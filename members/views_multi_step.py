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
    ChildrenInfoForm, BeneficiaryForm, PaymentOptionsForm, 
    OTPConfirmForm, PolicySummaryForm
)
from .multi_step_utils import (
    get_or_create_policy, validate_policy_step, 
    clear_policy_session, mark_policy_complete
)
from schemes.models import Scheme, Plan
from utils.easypay import generate_easypay_number
import json
from datetime import timedelta, datetime
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# ─── Step 1: Personal Details ─────────────────────────────────────────────────

def step1_personal(request):
    """Step 1: Collect personal details and create a new member."""
    policy = get_or_create_policy(request)
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
    # Get member's age for plan filtering
    today = timezone.now().date()
    age = today.year - policy.member.date_of_birth.year - (
        (today.month, today.day) < 
        (policy.member.date_of_birth.month, policy.member.date_of_birth.day)
    )
    
    # Get available schemes and plans based on user permissions
    if request.user.is_superuser:
        schemes_qs = Scheme.objects.all()
        plans_qs = Plan.objects.filter(
            main_age_from__lte=age,
            main_age_to__gte=age
        )
    else:
        branch_user = getattr(request.user, 'branchuser', None)
        agent_scheme = getattr(branch_user, 'scheme', None) if branch_user else None
        schemes_qs = Scheme.objects.filter(branch=branch_user.branch) if branch_user and branch_user.branch else Scheme.objects.none()
        agent_scheme = agent_scheme or (schemes_qs.first() if schemes_qs.exists() else None)
        plans_qs = Plan.objects.filter(
            main_age_from__lte=age,
            main_age_to__gte=age,
            scheme=agent_scheme
        )
    
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
    
    # Prepare plans data with all required fields
    available_plans = []
    for plan in plans_qs:
        available_plans.append({
            'id': plan.id,
            'name': plan.name,
            'description': plan.description or '',
            'premium_amount': float(plan.main_premium) if plan.main_premium is not None else 0.0,
            'cover_amount': float(plan.main_cover) if plan.main_cover is not None else 0.0,
            'main_premium': float(plan.main_premium) if plan.main_premium is not None else 0.0,  # Keep for backward compatibility
            'main_cover': float(plan.main_cover) if plan.main_cover is not None else 0.0,  # Keep for backward compatibility
            'is_popular': getattr(plan, 'is_popular', False),
            'benefits': list(getattr(plan, 'benefits', []).values('id', 'description') if hasattr(plan, 'benefits') and plan.benefits.exists() else []),
            'underwriter': getattr(plan, 'underwriter', ''),
        })
    
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
    children = policy.member.children.all()
    
    if request.method == 'POST':
        form = ChildrenInfoForm(request.POST, instance=policy.member)
        if form.is_valid():
            form.save()
            return redirect('members:step5_beneficiaries', pk=policy.pk)
    else:
        form = ChildrenInfoForm(instance=policy.member)
    
    return render(request, 'members/step4_children_info.html', {
        'form': form,
        'policy': policy,
        'children': children,
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
    
    if request.method == 'POST':
        form = OTPConfirmForm(request.POST, instance=otp_verification)
        if form.is_valid():
            otp_verification = form.save(commit=False)
            if otp_verification.verify_otp(form.cleaned_data['otp_code']):
                policy.otp_confirmed = True
                policy.save()
                return redirect('members:step8_policy_summary', pk=policy.pk)
            else:
                messages.error(request, 'Invalid OTP code. Please try again.')
    else:
        form = OTPConfirmForm()
        
        # Generate and send new OTP if not already sent or expired
        if created or not otp_verification.is_valid():
            otp_code = otp_verification.generate_new_code()
            # In a real app, you would send this via SMS or email
            messages.info(request, f'Your OTP is: {otp_code}')
    
    return render(request, 'members/step7_otp_verification.html', {
        'form': form,
        'policy': policy,
        'step': 7,
        'steps': range(1, 10),
        'otp_sent': True,
    })

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
