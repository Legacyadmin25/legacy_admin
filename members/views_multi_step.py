from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Policy, Member, Dependent, Beneficiary, OtpVerification
from .forms import (
    PersonalDetailsForm, PolicyDetailsForm, SpouseInfoForm,
    DependentForm, BeneficiaryForm, PaymentOptionsForm,
    OTPConfirmForm, PolicySummaryForm
)
from .multi_step_utils import (
    get_or_create_policy, validate_policy_step, 
    clear_policy_session, mark_policy_complete
)
from schemes.models import Scheme, Plan
from .communications.sms_sender import send_otp_sms
from utils.easypay import generate_easypay_number
import json
from datetime import timedelta, datetime
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _get_public_enrollment_context(request):
    scheme_id = request.session.get('enrollment_scheme_id')
    agent_id = request.session.get('enrollment_agent_id')
    token = request.session.get('enrollment_token')
    return {
        'is_public_enrollment': bool(token and scheme_id),
        'scheme_id': scheme_id,
        'agent_id': agent_id,
    }


def _apply_public_link_context(policy, public_context):
    changed = False

    if public_context['scheme_id'] and policy.scheme_id != public_context['scheme_id']:
        policy.scheme_id = public_context['scheme_id']
        changed = True

    if public_context['agent_id'] and policy.underwritten_by_id != public_context['agent_id']:
        policy.underwritten_by_id = public_context['agent_id']
        changed = True

    return changed


def _mask_phone_number(phone_number):
    digits = ''.join(ch for ch in str(phone_number or '') if ch.isdigit())
    if len(digits) <= 4:
        return str(phone_number or '')
    return digits[-4:]


def _otp_has_expired(otp_verification):
    if not otp_verification.sent_at:
        return True
    return timezone.now() - otp_verification.sent_at > timedelta(minutes=15)


def _send_policy_otp(policy, otp_verification):
    """Generate a new OTP, send via SMS, and fall back to email if SMS fails.
    Returns (success: bool, sms_log, otp_code: str).
    """
    otp_code = otp_verification.generate_new_code()
    sms_log = send_otp_sms(policy.member.phone_number, otp_code)

    if sms_log.status.upper() in ('SENT', 'TEST'):
        return True, sms_log, otp_code

    # SMS failed — try email fallback
    member = policy.member
    if member.email:
        try:
            send_mail(
                subject='Legacy Core Verification Code',
                message=(
                    f'Your verification code is: {otp_code}\n'
                    f'This code is valid for 15 minutes.\n'
                    f'Do not share this code.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[member.email],
                fail_silently=False,
            )
            sms_log.detail = f'SMS failed; OTP sent via email to {member.email}'
            sms_log.save(update_fields=['detail'])
            return True, sms_log, otp_code
        except Exception as email_err:
            sms_log.detail = f'{sms_log.detail}; email fallback failed: {email_err}'
            sms_log.save(update_fields=['detail'])

    return False, sms_log, otp_code

# ─── Step 1: Personal Details ─────────────────────────────────────────────────

def step1_personal(request):
    """Step 1: Collect personal details and create a new member."""
    policy = get_or_create_policy(request)
    public_context = _get_public_enrollment_context(request)
    member = policy.member if policy else None
    
    if request.method == 'POST':
        form = PersonalDetailsForm(request.POST, instance=member)
        if form.is_valid():
            member = form.save(commit=False)
            member.save()  # Save the member first
            
            # Create or update policy with the member
            if not policy or not policy.member:
                policy = get_or_create_policy(request, member.id)
            elif policy.member != member:
                policy.member = member

            if policy and _apply_public_link_context(policy, public_context):
                policy.save()
            elif policy and policy.member_id == member.id and policy.pk:
                policy.save()
            
            # Store the policy ID in the session
            request.session['policy_id'] = policy.id
            
            return redirect('members:step2_policy_details', pk=policy.pk)
    else:
        # Initialize form with member data if available
        initial_data = {}
        if member:
            initial_data = {
                'title': member.title,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'id_number': member.id_number,
                'passport_number': member.passport_number,
                'gender': member.gender,
                'date_of_birth': member.date_of_birth,
                'phone_number': member.phone_number,
                'whatsapp_number': member.whatsapp_number,
                'email': member.email,
                'marital_status': member.marital_status,
                'physical_address_line_1': member.physical_address_line_1,
                'physical_address_line_2': member.physical_address_line_2,
                'physical_address_city': member.physical_address_city,
                'physical_address_postal_code': member.physical_address_postal_code,
                'nationality': member.nationality,
                'country_of_birth': member.country_of_birth,
                'country_of_residence': member.country_of_residence,
            }
        form = PersonalDetailsForm(initial=initial_data, instance=member)
    
    return render(request, 'members/step1_personal_address.html', {
        'form': form,
        'step': 1,
        'steps': range(1, 10),  # Total number of steps
    })

# ─── Step 2: Policy Details ──────────────────────────────────────────────────

@validate_policy_step
def step2_policy_details(request, policy):
    """Step 2: Select policy details and plan."""
    public_context = _get_public_enrollment_context(request)
    if _apply_public_link_context(policy, public_context):
        policy.save()

    # Get member's age for plan filtering
    today = timezone.now().date()
    age = today.year - policy.member.date_of_birth.year - (
        (today.month, today.day) < 
        (policy.member.date_of_birth.month, policy.member.date_of_birth.day)
    )
    
    # Get available schemes and plans based on user permissions
    age_filtered_plans = Plan.objects.filter(
        is_active=True,
        main_age_from__lte=age,
        main_age_to__gte=age,
    )

    if public_context['is_public_enrollment']:
        schemes_qs = Scheme.objects.filter(pk=public_context['scheme_id'], active=True)
        plans_qs = age_filtered_plans.filter(scheme_id=public_context['scheme_id'])
    elif request.user.is_superuser:
        schemes_qs = Scheme.objects.filter(active=True)
        plans_qs = age_filtered_plans
        if policy.scheme_id:
            plans_qs = plans_qs.filter(scheme_id=policy.scheme_id)

        # Prevent superuser onboarding from being blocked by age configuration gaps.
        if not plans_qs.exists():
            plans_qs = Plan.objects.filter(is_active=True)
    else:
        branch_user = getattr(request.user, 'branchuser', None)
        agent_scheme = getattr(branch_user, 'scheme', None) if branch_user else None
        schemes_qs = Scheme.objects.filter(branch=branch_user.branch, active=True) if branch_user and branch_user.branch else Scheme.objects.none()
        agent_scheme = agent_scheme or (schemes_qs.first() if schemes_qs.exists() else None)
        plans_qs = age_filtered_plans.filter(scheme=agent_scheme) if agent_scheme else Plan.objects.none()
    
    if request.method == 'POST':
        # Handle back button
        if 'back' in request.POST:
            return redirect('members:step1_personal')
            
        form = PolicyDetailsForm(
            request.POST, 
            instance=policy,
            user=request.user
        )
        form.fields['scheme'].queryset = schemes_qs
        form.fields['plan'].queryset = plans_qs
        
        if form.is_valid():
            policy = form.save(commit=False)

            if policy.plan_id:
                selected_plan = policy.plan
                policy.scheme = selected_plan.scheme
                policy.premium_amount = selected_plan.main_premium if selected_plan.main_premium is not None else selected_plan.premium
                policy.cover_amount = selected_plan.main_cover if selected_plan.main_cover is not None else 0

            _apply_public_link_context(policy, public_context)
            
            # Set policy dates if start_date is provided
            if policy.start_date:
                start = policy.start_date
                first_next_month = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
                cover_month = first_next_month.month + 6
                cover_year = first_next_month.year
                if cover_month > 12:
                    cover_month -= 12
                    cover_year += 1
                policy.inception_date = first_next_month
                policy.cover_date = first_next_month.replace(year=cover_year, month=cover_month)
            
            policy.save()
            return redirect('members:step3_spouse_info', pk=policy.pk)
    else:
        # Initialize form with existing policy data
        initial_data = {}
        if policy:
            initial_data = {
                'scheme': policy.scheme,
                'plan': policy.plan,
                'start_date': policy.start_date,
                'inception_date': policy.inception_date,
                'cover_date': policy.cover_date,
                'underwritten_by': policy.underwritten_by,
                'premium_amount': policy.premium_amount,
                'cover_amount': policy.cover_amount,
            }
        form = PolicyDetailsForm(initial=initial_data, instance=policy, user=request.user)
        form.fields['scheme'].queryset = schemes_qs
        form.fields['plan'].queryset = plans_qs
    
    plans_qs = plans_qs.select_related('scheme').prefetch_related('plan_tiers')

    # Prepare plans data with all required fields used by the template.
    plans_data = []
    for plan in plans_qs:
        tiers = [
            {
                'member_type': tier.get_user_type_display(),
                'age_from': tier.age_from,
                'age_to': tier.age_to,
                'premium': float(tier.premium_amount),
                'cover': float(tier.cover_amount),
            }
            for tier in plan.plan_tiers.all()
        ]

        in_member_scheme = True if not policy.scheme_id else (plan.scheme_id == policy.scheme_id)

        plans_data.append({
            'id': plan.id,
            'name': plan.name,
            'description': plan.description or '',
            'premium': float(plan.main_premium) if plan.main_premium is not None else float(plan.premium),
            'cover_amount': float(plan.main_cover) if plan.main_cover is not None else 0.0,
            'spouses_allowed': plan.spouses_allowed,
            'children_allowed': plan.children_allowed,
            'extended_allowed': plan.extended_allowed,
            'policy_type': plan.policy_type,
            'waiting_period': plan.waiting_period,
            'in_member_scheme': in_member_scheme,
            'is_popular': getattr(plan, 'is_popular', False),
            'tiers': json.dumps(tiers),
        })

    # Keep backward-compatible alias expected by some scripts/snippets.
    available_plans = plans_data
    
    # Prepare plans data for JavaScript
    plans_json = json.dumps([
        {
            'id': p.id,
            'name': p.name,
            'description': p.description or '',
            'premium_amount': float(p.main_premium) if p.main_premium is not None else 0.0,
            'cover_amount': float(p.main_cover) if p.main_cover is not None else 0.0,
            'underwriter': getattr(p, 'underwriter', ''),
        }
        for p in plans_qs
    ])
    
    return render(request, 'members/step2_policy_details.html', {
        'form': form,
        'policy': policy,
        'step': 2,
        'steps': range(1, 10),  # Update this based on your total steps
        'member_age': age,
        'plans_data': plans_data,
        'plans_json': plans_json,
        'available_plans': available_plans,
    })

# ─── Step 3: Spouse Information ─────────────────────────────────────────────

@validate_policy_step
def step3_spouse_info(request, policy):
    """Step 3: Collect spouse information."""
    if request.method == 'POST':
        form = SpouseInfoForm(request.POST, instance=policy.member)
        if form.is_valid():
            form.save()
            return redirect('members:step4_children_info', pk=policy.pk)
    else:
        form = SpouseInfoForm(instance=policy.member)
    
    return render(request, 'members/step3_spouse_info.html', {
        'form': form,
        'policy': policy,
        'member': policy.member,  # Add member to context
        'step': 3,
        'steps': range(1, 10),
    })

# ─── Step 4: Children Information ───────────────────────────────────────────

@validate_policy_step
def step4_children_info(request, policy):
    """Step 4: Collect children information."""
    children_allowed = policy.plan.children_allowed if policy.plan and policy.plan.children_allowed else 0
    extended_allowed = policy.plan.extended_allowed if policy.plan and policy.plan.extended_allowed else 0
    children = policy.dependents.filter(relationship='Child').order_by('first_name', 'last_name')
    extended_members = policy.dependents.filter(relationship='Extended Family').order_by('first_name', 'last_name')
    form = DependentForm()
    
    if request.method == 'POST':
        if 'next_step' in request.POST:
            return redirect('members:step5_beneficiaries', pk=policy.pk)

        remove_dependent_id = request.POST.get('remove_dependent')
        if remove_dependent_id:
            dependent = get_object_or_404(Dependent, pk=remove_dependent_id, policy=policy)
            dependent.delete()
            messages.success(request, 'Dependent removed successfully.')
            return redirect('members:step4_children_info', pk=policy.pk)

        relationship_map = {
            'add_child': ('Child', children.count(), children_allowed),
            'add_extended': ('Extended Family', extended_members.count(), extended_allowed),
        }
        action = next((name for name in relationship_map if name in request.POST), None)

        if action:
            relationship_name, current_count, allowed_count = relationship_map[action]
            if allowed_count <= current_count:
                messages.error(request, f'This plan allows a maximum of {allowed_count} {relationship_name.lower()} dependents.')
            else:
                post_data = request.POST.copy()
                post_data['relationship'] = relationship_name
                form = DependentForm(post_data)
                if form.is_valid():
                    dependent = form.save(commit=False)
                    dependent.policy = policy
                    dependent.relationship = relationship_name
                    dependent.save()
                    messages.success(request, f'{relationship_name} added successfully.')
                    return redirect('members:step4_children_info', pk=policy.pk)
    
    return render(request, 'members/step4_children_info.html', {
        'form': form,
        'policy': policy,
        'children': children,
        'extended_members': extended_members,
        'children_count': children.count(),
        'extended_count': extended_members.count(),
        'children_allowed': children_allowed,
        'extended_allowed': extended_allowed,
        'step': 4,
        'steps': range(1, 10),
    })

# ─── Step 5: Beneficiaries ──────────────────────────────────────────────────

@validate_policy_step
def step5_beneficiaries(request, policy):
    """Step 5: Add beneficiaries to the policy."""
    beneficiaries = policy.beneficiaries.all()
    
    if request.method == 'POST':
        form = BeneficiaryForm(request.POST, policy=policy)
        if form.is_valid():
            beneficiary = form.save(commit=False)
            beneficiary.policy = policy
            beneficiary.save()
            messages.success(request, 'Beneficiary added successfully.')
            return redirect('members:step5_beneficiaries', pk=policy.pk)
    else:
        form = BeneficiaryForm(policy=policy)
    
    return render(request, 'members/step5_beneficiaries.html', {
        'form': form,
        'policy': policy,
        'beneficiaries': beneficiaries,
        'step': 5,
        'steps': range(1, 10),
    })

# ─── Step 6: Payment Options ────────────────────────────────────────────────

@validate_policy_step
def step6_payment_options(request, policy):
    """Step 6: Select payment options."""
    if request.method == 'POST':
        form = PaymentOptionsForm(request.POST, instance=policy)
        if form.is_valid():
            policy = form.save(commit=False)
            
            # Generate EasyPay number if not set
            if not policy.easypay_number:
                policy.easypay_number = generate_easypay_number(str(policy.pk))
            
            policy.save()
            return redirect('members:step7_otp_verification', pk=policy.pk)
    else:
        form = PaymentOptionsForm(instance=policy)
    
    return render(request, 'members/step6_payment_options.html', {
        'form': form,
        'policy': policy,
        'step': 6,
        'steps': range(1, 10),
    })

# ─── Step 7: OTP Verification ───────────────────────────────────────────────

@validate_policy_step
def step7_otp_verification(request, policy):
    """Step 7: Verify OTP for policy confirmation."""
    # Create or get OTP verification record
    otp_verification, created = OtpVerification.objects.get_or_create(
        policy=policy,
        defaults={'code_hash': 'dummy'}  # Will be set by generate_new_code
    )
    
    otp_sent = True
    otp_delivery_error = ''
    debug_otp = None

    if request.method == 'POST':
        form = OTPConfirmForm(request.POST)
        if form.is_valid():
            if otp_verification.check_code(form.cleaned_data['otp_code']):
                policy.otp_confirmed = True
                policy.save()
                return redirect('members:step8_policy_summary', pk=policy.pk)
            messages.error(request, 'Invalid or expired OTP code. Please try again.')
    else:
        form = OTPConfirmForm()

        # Generate and send new OTP if not already sent or expired
        if created or _otp_has_expired(otp_verification):
            otp_sent, sms_log, otp_code_plain = _send_policy_otp(policy, otp_verification)
            if otp_sent:
                messages.success(request, 'A verification code has been sent.')
            else:
                otp_delivery_error = sms_log.detail or 'We could not send the verification code right now.'
                messages.error(request, otp_delivery_error)
                if settings.DEBUG:
                    debug_otp = otp_code_plain

    return render(request, 'members/step7_otp_verification.html', {
        'form': form,
        'policy': policy,
        'member': policy.member,
        'step': 7,
        'steps': range(1, 10),
        'otp_sent': otp_sent,
        'otp_delivery_error': otp_delivery_error,
        'masked_phone_number': _mask_phone_number(policy.member.phone_number),
        'debug_otp': debug_otp,
    })


@validate_policy_step
def resend_policy_otp(request, policy):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)

    otp_verification, _ = OtpVerification.objects.get_or_create(
        policy=policy,
        defaults={'code_hash': 'dummy'}
    )
    otp_sent, sms_log, _otp_plain = _send_policy_otp(policy, otp_verification)

    status_code = 200 if otp_sent else 400
    return JsonResponse({
        'success': otp_sent,
        'error': '' if otp_sent else (sms_log.detail or 'Unable to send OTP.'),
    }, status=status_code)

# ─── Step 8: Policy Summary ────────────────────────────────────────────────

@validate_policy_step
def step8_policy_summary(request, policy):
    """Step 8: Show policy summary before final confirmation."""
    beneficiaries = policy.beneficiaries.all()
    dependents = policy.dependents.all()
    
    if request.method == 'POST':
        form = PolicySummaryForm(request.POST, instance=policy)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.is_complete = True
            policy.save()
            
            # Send confirmation email
            send_policy_confirmation_email(policy)
            
            # Clear the session
            if 'policy_id' in request.session:
                del request.session['policy_id']
                
            return redirect('members:step9_policy_confirmation', pk=policy.pk)
    else:
        form = PolicySummaryForm(instance=policy)
    
    return render(request, 'members/step8_policy_summary.html', {
        'form': form,
        'policy': policy,
        'beneficiaries': beneficiaries,
        'dependents': dependents,
        'step': 8,
        'steps': range(1, 10),
    })

# ─── Step 9: Policy Confirmation ───────────────────────────────────────────

def step9_policy_confirmation(request, pk):
    """Step 9: Show policy confirmation."""
    policy = get_object_or_404(Policy, pk=pk)
    
    return render(request, 'members/step9_policy_confirmation.html', {
        'policy': policy,
        'step': 9,
        'steps': range(1, 10),
    })

# ─── Helper Functions ──────────────────────────────────────────────────────

def send_policy_confirmation_email(policy):
    """Send policy confirmation email to the member."""
    subject = f'Your Policy #{policy.policy_number} Confirmation'
    html_message = render_to_string('emails/policy_confirmation.html', {
        'policy': policy,
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[policy.member.email],
        html_message=html_message,
        fail_silently=False,
    )

# ─── Incomplete Applications List ──────────────────────────────────────────

class IncompleteApplicationsList(ListView):
    """View for listing incomplete policy applications."""
    model = Policy
    template_name = 'members/incomplete_applications.html'
    context_object_name = 'policies'
    
    def get_queryset(self):
        """Return only incomplete policies, ordered by most recently updated."""
        return Policy.objects.filter(
            is_complete=False,
            member__isnull=False
        ).select_related('member').order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Incomplete Applications'
        return context
