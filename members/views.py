import json
from weasyprint import HTML
from django.shortcuts import render, redirect, get_object_or_404, Http404
from django.urls import reverse
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.utils.html import escape
from .models import Member, Policy, Dependent, Beneficiary, OtpVerification
from .forms import (
    PersonalDetailsForm,
    PolicyDetailsForm,
    DependentForm,
    BeneficiaryForm,
    PaymentOptionsForm,
    OTPConfirmForm,
    PersonalDetailsEditForm,
    AddressEditForm,
    PolicyEditForm,
    PaymentOptionsEditForm,
    CommunicationForm,
    NotesForm,
)
from members.communications.sms_sender import send_bulk_sms
from utils.luhn import validate_id_number, luhn_check
from utils.easypay import generate_easypay_number
from schemes.models import Scheme
from schemes.models import Plan

# Define the step range for the application process
STEP_RANGE = range(1, 10)  # Steps 1-9


@login_required
def find_policy(request):
    q = request.GET.get('q', '').strip()  # Get search query from GET parameters

    # Only filter if there's a search query; otherwise, return an empty list
    if q:
        members_qs = Member.objects.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(id_number__icontains=q)
        )
    else:
        members_qs = []  # If no query, return empty list

    # Ensure we get the related policy (first one) for the member
    policies = Policy.objects.filter(member__in=members_qs)  # Adjusted to filter based on member

    # Group check logic moved to the view to avoid recursion in the template
    is_superuser = request.user.is_superuser
    is_branch_owner = request.user.groups.filter(name="Branch Owner").exists()
    is_scheme_admin = request.user.groups.filter(name="Scheme Admin").exists()

    # Pass the policies and group check results to the template
    return render(request, 'members/find_policy/base_profile.html', {
        'members': members_qs,  # Pass the filtered members to the template
        'q': q,  # Pass the search query to display it in the search box
        'selected_tab': 'search',  # To maintain the active tab (if needed)
        'policies': policies,  # Pass the policies object to the template
        'is_superuser': is_superuser,  # Pass if the user is superuser
        'is_branch_owner': is_branch_owner,  # Pass if the user is a Branch Owner
        'is_scheme_admin': is_scheme_admin,  # Pass if the user is a Scheme Admin
    })


# ─── Wizard Step 1: Personal ───────────────────────────────────────────────────

def create_personal(request):
    initial_data = {}
    member = None
    
    if request.GET.get('scheme'):
        scheme_id = request.GET.get('scheme')
        initial_data['scheme'] = scheme_id

    if request.session.get('is_diy_signup') and request.session.get('diy_agent_id') and request.session.get('diy_scheme_id'):
        initial_data['via_diy'] = True
        agent_id = request.session.get('diy_agent_id')
        scheme_id = request.session.get('diy_scheme_id')
        if agent_id:
            initial_data['agent'] = agent_id
        if scheme_id:
            initial_data['scheme'] = scheme_id

    if request.method == 'POST':
        form = PersonalDetailsForm(request.POST)
        if form.is_valid():
            # Save member with calculated age
            member = form.save()
            
            # Get eligible plans for this member based on age
            from members.utils import get_filtered_plans
            eligible_plans = get_filtered_plans(member)
            
            # Store eligible plan IDs in session for Step 2
            request.session['eligible_plan_ids'] = [plan.id for plan in eligible_plans]
            
            # Create a new policy instance for this member
            policy, created = Policy.objects.get_or_create(member=member)
            
            # Redirect to Step 2
            return redirect('members:step2_policy_details', member_id=member.id)
        else:
            # Log validation errors for debugging
            print("\n=== Step 1 Form Validation Failed ===")
            print("Form errors:", form.errors)
            print("Form data:", form.cleaned_data)
            print("Non-field errors:", form.non_field_errors())
            print("=== End of Validation Errors ===\n")
    else:
        form = PersonalDetailsForm(initial=initial_data)

    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    # Calculate min/max dates for date of birth field
    from datetime import date, timedelta
    today = date.today()
    min_date = date(today.year - 100, today.month, today.day).isoformat()  # 100 years ago
    max_date = today.isoformat()  # Today

    return render(request, 'members/step1_personal_address.html', {
        'form': form,
        'step': 1,
        'steps': STEP_RANGE,
        'base_template': base_template,
        'member': member,  # Pass member to template, will be None on first load
        'min_date': min_date,
        'max_date': max_date,
        'today': today.isoformat(),
    })



# ─── Wizard Step 2: Policy Details ─────────────────────────────────────────────
@login_required
def create_policy_details(request, member_id):
    # Get member and existing policy if any
    member = get_object_or_404(Member, pk=member_id)
    policy = Policy.objects.filter(member=member).first()
    
    # Get user's branch and scheme context
    branch_user = getattr(request.user, 'branchuser', None)
    agent_scheme = getattr(branch_user, 'scheme', None) if branch_user else None

    # Calculate member's age using utility function
    from members.utils import get_member_age_from_dob
    age = get_member_age_from_dob(member.date_of_birth)

    # Get schemes based on user permissions
    if request.user.is_superuser:
        schemes_qs = Scheme.objects.all()
    else:
        # If user has a branch or scheme, filter by it
        schemes_qs = Scheme.objects.filter(branch=branch_user.branch) if branch_user and branch_user.branch else Scheme.objects.none()
        agent_scheme = agent_scheme or (schemes_qs.first() if schemes_qs.exists() else None)
    
    # Get filtered plans based on member's age
    from members.utils import get_filtered_plans
    filtered_plans = get_filtered_plans(member)
    
    # Further filter plans by scheme if needed
    if not request.user.is_superuser and agent_scheme:
        plans_qs = filtered_plans.filter(scheme=agent_scheme)
        # Keep track of all eligible plans for UI display
        all_eligible_plans = filtered_plans
    else:
        plans_qs = filtered_plans
        all_eligible_plans = filtered_plans
        
    # Log the filtered plans for debugging
    print(f"Found {plans_qs.count()} eligible plans for member age {age}")
    for plan in plans_qs:
        print(f"Plan: {plan.name}, Age Range: {plan.main_age_from}-{plan.main_age_to}")
        
    # If no plans are available for this age, include a message
    if not plans_qs.exists():
        messages.warning(request, f"No plans available for member age {age}. Please contact support.")
        # Still continue to show the form with empty plans

    if request.method == 'POST':
        form = PolicyDetailsForm(request.POST, instance=policy or Policy(member=member))
        form.fields['scheme'].queryset = schemes_qs
        form.fields['plan'].queryset = plans_qs

        if form.is_valid():
            policy = form.save(commit=False)
            policy.member = member

            # Set plan details on the policy
            selected_plan = form.cleaned_data['plan']
            policy.premium_amount = selected_plan.premium
            policy.cover_amount = selected_plan.main_cover

            # Calculate inception and cover dates
            if policy.start_date:
                start = policy.start_date
                # Inception = first of next month
                first_next_month = (start.replace(day=1) + timezone.timedelta(days=32)).replace(day=1)
                # Cover = Inception + waiting period (default 6 months)
                waiting_period = selected_plan.waiting_period
                cover_month = first_next_month.month + waiting_period
                cover_year = first_next_month.year
                if cover_month > 12:
                    cover_month = cover_month % 12 or 12  # Handle December
                    cover_year += (cover_month - 1) // 12
                cover_date = first_next_month.replace(year=cover_year, month=cover_month)
                policy.inception_date = first_next_month
                policy.cover_date = cover_date

            # Save policy to get a PK if new
            policy.save()

            # Generate and assign the correct UW membership number if not set
            if not policy.uw_membership_number:
                prefix = (policy.scheme.name[:3].upper().replace(' ', '') if policy.scheme and policy.scheme.name else "POL")
                unique_number = f"{policy.pk:06d}"
                policy.uw_membership_number = f"{prefix}-{unique_number}"
            
            # Generate Easypay number if not set
            if not policy.easypay_number:
                policy.easypay_number = generate_easypay_number(str(policy.pk))
            
            policy.save()

            # Check if we should skip steps based on plan configuration
            from members.utils import should_skip_step
            if should_skip_step(policy, 'spouse'):
                if should_skip_step(policy, 'children'):
                    return redirect('members:step5_beneficiaries', member_id=member.id)
                else:
                    return redirect('members:step4_children_info', member_id=member.id)
            else:
                return redirect('members:step3_spouse_info', member_id=member.id)
    else:
        # Initialize form with existing policy or create new one
        if policy:
            form = PolicyDetailsForm(instance=policy)
        else:
            # For superusers, auto-select the first available scheme if not set
            if request.user.is_superuser:
                default_scheme = schemes_qs.first() if schemes_qs.exists() else None
                initial_policy = Policy(member=member, scheme=default_scheme)
            else:
                initial_policy = Policy(member=member, scheme=agent_scheme)
            form = PolicyDetailsForm(instance=initial_policy)
        
        form.fields['scheme'].queryset = schemes_qs
        form.fields['plan'].queryset = plans_qs

    # Prepare plan data for template with detailed information
    plans_data = []
    for p in plans_qs:
        # Get tier information for the plan
        tiers_data = []
        for tier in p.tiers.all():
            tiers_data.append({
                'id': tier.id,
                'member_type': tier.member_type,
                'age_from': tier.age_from,
                'age_to': tier.age_to,
                'cover': float(tier.cover),
                'premium': float(tier.premium)
            })
        
        # Check if this plan is in the member's scheme
        in_member_scheme = True
        if agent_scheme and p.scheme != agent_scheme:
            in_member_scheme = False
        
        # Add plan data
        plans_data.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'premium': float(p.premium),
            'cover_amount': float(p.main_cover),
            'policy_type': p.policy_type,
            'spouses_allowed': p.spouses_allowed,
            'children_allowed': p.children_allowed,
            'extended_allowed': p.extended_allowed,
            'waiting_period': p.waiting_period,
            'is_active': p.is_active,
            'is_popular': getattr(p, 'is_popular', False),
            'in_member_scheme': in_member_scheme,
            'tiers': tiers_data
        })
    
    # Convert to JSON for JavaScript use
    plans_json = json.dumps(plans_data)
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    return render(request, 'members/step2_policy_details.html', {
        'form': form,
        'member': member,
        'step': 2,
        'steps': STEP_RANGE,
        'plans': plans_qs,
        'all_eligible_plans': all_eligible_plans,
        'member_age': age,
        'plans_json': plans_json,
        'plans_data': plans_data,  # Pass both JSON and Python objects
        'base_template': base_template,
        'agent_scheme': agent_scheme,
        'has_plans': plans_qs.exists(),
    })

    selected_scheme_id = form.initial.get('scheme') or getattr(form.instance, 'scheme_id', '')
    # Get the scheme name for the selected scheme
    if selected_scheme_id:
        try:
            selected_scheme_name = Scheme.objects.get(pk=selected_scheme_id).name
        except Scheme.DoesNotExist:
            selected_scheme_name = ''
    else:
        selected_scheme_name = ''
    # Prepare available plans with all needed data
    available_plans = []
    for p in plans_qs:
        # Serialize member tiers for JavaScript
        tiers_data = []
        for tier in p.tiers.all():
            tiers_data.append({
                'user_type': tier.user_type,
                'age_from': tier.age_from,
                'age_to': tier.age_to,
                'cover': float(tier.cover),
                'premium': float(tier.premium)
            })
            
        plan_data = {
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'premium_amount': p.main_premium,
            'cover_amount': p.main_cover,
            'is_popular': getattr(p, 'is_popular', False),
            'spouses_allowed': p.spouses_allowed,
            'children_allowed': p.children_allowed,
            'extended_allowed': p.extended_allowed,
            'tiers': p.tiers.all(),
            'tiers_json': json.dumps(tiers_data)
        }
        available_plans.append(plan_data)
    
    return render(request, 'members/step2_policy_details.html', {
        'form': form,
        'member': member,
        'step': 2,
        'steps': STEP_RANGE,
        'plans_json': plans_json,
        'available_plans': available_plans,
        'base_template': base_template,
        'selected_scheme_id': selected_scheme_id,
        'selected_scheme_name': selected_scheme_name,
    })


# ─── Wizard Step 3: Spouse Information ────────────────────────────────────────

@login_required
def create_spouse_info(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    policy = get_object_or_404(Policy, member=member)
    plan = policy.plan
    
    # Import utility functions
    from members.utils import should_skip_step, get_allowed_counts, get_member_age_from_dob, get_cover_amount_for_dependent, luhn_check
    
    # Check if we should skip this step based on plan configuration
    if should_skip_step(policy, 'spouse'):
        return redirect('members:step4_children_info', member_id=member.id)
    
    # Get allowed counts from the plan
    allowed_counts = get_allowed_counts(plan)
    spouses_allowed = allowed_counts['spouses']
    
    # Count existing spouse dependents
    spouse_count = policy.dependents.filter(relationship='spouse').count()
    spouse_exists = spouse_count > 0
    
    # Check if already at max spouses
    at_max_spouses = spouse_count >= spouses_allowed
    
    # Get existing spouse if any
    spouse = None
    if spouse_exists:
        spouse = policy.dependents.filter(relationship='spouse').first()
    
    if request.method == 'POST':
        # Check if going back
        if 'back' in request.POST:
            return redirect('members:create_policy_details', member_id=member.id)
            
        form = DependentForm(request.POST, instance=spouse, prefix='spouse')
        
        if form.is_valid():
            dependent = form.save(commit=False)
            dependent.policy = policy
            dependent.relationship = 'spouse'
            
            # Extract DOB and gender from ID if South African
            if not dependent.is_foreign and dependent.id_number:
                # Validate ID using Luhn algorithm
                if luhn_check(dependent.id_number):
                    # Extract DOB and gender from ID
                    from members.utils import extract_dob_from_id, extract_gender_from_id
                    dob = extract_dob_from_id(dependent.id_number)
                    gender = extract_gender_from_id(dependent.id_number)
                    
                    if dob:
                        dependent.date_of_birth = dob
                    if gender:
                        dependent.gender = gender
            
            # Calculate age from DOB
            if dependent.date_of_birth:
                age = get_member_age_from_dob(dependent.date_of_birth)
                
                # Calculate cover amount based on age and relationship
                cover_amount = get_cover_amount_for_dependent(plan, age, 'spouse')
                dependent.cover_amount = cover_amount
            
            dependent.save()
            
            # Redirect to next step
            return redirect('members:step4_children_info', member_id=member.id)
    else:
        initial = {'relationship': 'spouse'}
        if spouse_exists:
            form = DependentForm(instance=spouse, prefix='spouse')
        else:
            form = DependentForm(initial=initial, prefix='spouse')
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    return render(request, 'members/step3_spouse_info.html', {
        'member': member,
        'policy': policy,
        'plan': plan,
        'form': form,
        'spouse_exists': spouse_exists,
        'spouse_count': spouse_count,
        'spouses_allowed': spouses_allowed,
        'at_max_spouses': at_max_spouses,
        'step': 3,
        'steps': STEP_RANGE,
        'base_template': base_template,
    })


# ─── Wizard Step 4: Children Information ──────────────────────────────────────

@login_required
def create_children_info(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member
    plan = policy.plan
    
    # Import utility functions
    from members.utils import should_skip_step, get_allowed_counts, get_member_age_from_dob, get_cover_amount_for_dependent, luhn_check, extract_dob_from_id, extract_gender_from_id
    
    # Check if we should skip this step based on plan configuration
    if should_skip_step(policy, 'children'):
        return redirect('members:step5_beneficiaries', pk=policy.pk)
    
    # Get allowed counts from the plan
    allowed_counts = get_allowed_counts(plan)
    children_allowed = allowed_counts['children']
    extended_allowed = allowed_counts['extended']
    
    # Count existing dependents by type
    children_count = policy.dependents.filter(relationship='child').count()
    extended_count = policy.dependents.filter(relationship='extended').count()
    
    # Check if already at max for each type
    at_max_children = children_count >= children_allowed
    at_max_extended = extended_count >= extended_allowed
    
    # Get existing dependents
    children = policy.dependents.filter(relationship='child').order_by('date_of_birth')
    extended_members = policy.dependents.filter(relationship='extended').order_by('date_of_birth')
    
    # Initialize form
    form = None
    
    if request.method == 'POST':
        # Check if going back
        if 'back' in request.POST:
            return redirect('members:step3_spouse_info', pk=policy.pk)
            
        # Handle adding a child or extended family member
        if ('add_child' in request.POST or 'add_extended' in request.POST) and 'relationship' in request.POST:
            relationship = request.POST.get('relationship')
            
            # Check if we're at the maximum allowed for this relationship type
            if (relationship == 'child' and at_max_children) or (relationship == 'extended' and at_max_extended):
                messages.error(request, f'You have reached the maximum number of {relationship}s allowed for this plan.')
                return redirect('members:step4_children_info', pk=policy.pk)
            
            form = DependentForm(request.POST)
            if form.is_valid():
                dependent = form.save(commit=False)
                dependent.policy = policy
                dependent.relationship = relationship
                
                # Extract DOB and gender from ID if South African
                if dependent.id_number and luhn_check(dependent.id_number):
                    dob = extract_dob_from_id(dependent.id_number)
                    gender = extract_gender_from_id(dependent.id_number)
                    
                    if dob:
                        dependent.date_of_birth = dob
                    if gender:
                        dependent.gender = gender
                
                # Calculate age from DOB
                if dependent.date_of_birth:
                    age = get_member_age_from_dob(dependent.date_of_birth)
                    
                    # Calculate cover amount based on age and relationship
                    cover_amount = get_cover_amount_for_dependent(plan, age, relationship)
                    dependent.cover_amount = cover_amount
                
                dependent.save()
                messages.success(request, f'{relationship.title()} added successfully.')
                return redirect('members:step4_children_info', pk=policy.pk)
        
        # Handle removing a dependent
        elif 'remove_dependent' in request.POST:
            dependent_id = request.POST.get('remove_dependent')
            if dependent_id:
                try:
                    dependent = get_object_or_404(Dependent, id=dependent_id, policy=policy)
                    relationship = dependent.relationship
                    dependent.delete()
                    messages.success(request, f'{relationship.title()} removed successfully.')
                except Exception as e:
                    messages.error(request, f'Error removing dependent: {str(e)}')
                return redirect('members:step4_children_info', pk=policy.pk)
        
        # Handle proceeding to next step
        elif 'next_step' in request.POST:
            return redirect('members:step5_beneficiaries', pk=policy.pk)
    
    # Initialize form if not already set
    if form is None:
        form = DependentForm()
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    return render(request, 'members/step4_children_info.html', {
        'member': member,
        'policy': policy,
        'plan': plan,
        'children': children,
        'extended_members': extended_members,
        'form': form,
        'children_count': children_count,
        'extended_count': extended_count,
        'children_allowed': children_allowed,
        'extended_allowed': extended_allowed,
        'at_max_children': at_max_children,
        'at_max_extended': at_max_extended,
        'step': 4,
        'steps': STEP_RANGE,
        'base_template': base_template,
    })


# ─── Wizard Step 5: Beneficiaries ────────────────────────────────────────────

def create_beneficiaries(request, pk):
    """
    Step 5: Beneficiaries
    Allow users to add beneficiaries (up to 5 max), ensure their combined share equals 100%,
    and validate ID numbers or passport info properly.
    """
    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member
    
    # Import utility functions
    from members.utils import validate_beneficiaries, luhn_check, extract_dob_from_id, extract_gender_from_id
    
    # Get existing beneficiaries and calculate total share
    beneficiaries = policy.beneficiaries.all()
    total_share = sum(b.share for b in beneficiaries)
    beneficiary_count = beneficiaries.count()
    at_max_beneficiaries = beneficiary_count >= 5
    
    if request.method == 'POST':
        # Handle adding a beneficiary
        if 'add_beneficiary' in request.POST and not at_max_beneficiaries:
            form = BeneficiaryForm(request.POST)
            if form.is_valid():
                beneficiary = form.save(commit=False)
                beneficiary.policy = policy
                
                # Extract DOB and gender from ID if South African
                if beneficiary.id_number and luhn_check(beneficiary.id_number):
                    dob = extract_dob_from_id(beneficiary.id_number)
                    gender = extract_gender_from_id(beneficiary.id_number)
                    
                    if dob:
                        beneficiary.date_of_birth = dob
                    if gender:
                        beneficiary.gender = gender
                
                beneficiary.save()
                messages.success(request, 'Beneficiary added successfully.')
                return redirect('members:step5_beneficiaries', pk=policy.pk)
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        
        # Handle removing a beneficiary
        elif 'remove_beneficiary' in request.POST:
            beneficiary_id = request.POST.get('remove_beneficiary')
            if beneficiary_id:
                try:
                    beneficiary = get_object_or_404(Beneficiary, id=beneficiary_id, policy=policy)
                    beneficiary.delete()
                    messages.success(request, 'Beneficiary removed successfully.')
                except Exception as e:
                    messages.error(request, f'Error removing beneficiary: {str(e)}')
                return redirect('members:step5_beneficiaries', pk=policy.pk)
        
        # Handle proceeding to next step
        elif 'next_step' in request.POST:
            # Validate beneficiaries before proceeding
            is_valid, error_message = validate_beneficiaries(beneficiaries)
            if is_valid:
                return redirect('members:step6_payment_options', pk=policy.pk)
            else:
                messages.error(request, error_message)
    else:
        form = BeneficiaryForm()
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    return render(request, 'members/step5_beneficiaries.html', {
        'member': member,
        'policy': policy,
        'beneficiaries': beneficiaries,
        'form': form,
        'total_share': total_share,
        'beneficiary_count': beneficiary_count,
        'at_max_beneficiaries': at_max_beneficiaries,
        'step': 5,
        'steps': STEP_RANGE,
        'base_template': base_template,
    })
@login_required
def create_dependents(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    # Get the most recent policy for this member (order by id in descending order)
    policy = Policy.objects.filter(member=member).order_by('-id').first()
    if not policy:
        raise Http404("No policy found for this member")

    dependents = policy.dependents.all()
    beneficiaries = policy.beneficiaries.all()
    editing_dependent = None
    editing_beneficiary = None
    dep_form = DependentForm(prefix='dep')
    ben_form = BeneficiaryForm(prefix='ben')
    form_errors = []

    if request.method == 'POST':
        # Handle navigation buttons
        if 'back' in request.POST:
            return redirect('members:step2_policy_details', member_id=member.id)
        if 'next' in request.POST:
            total_share = sum(b.share for b in beneficiaries)
            if total_share != 100:
                form_errors.append('Total beneficiary share must be exactly 100% before proceeding.')
            else:
                return redirect('members:step4_payment_options', member_id=member.id)

        # Handle dependent form submission
        if 'save_dependent' in request.POST:
            edit_id = request.POST.get('edit_dep_id')
            if edit_id:
                editing_dependent = get_object_or_404(Dependent, pk=edit_id, policy=policy)
                dep_form = DependentForm(request.POST, instance=editing_dependent, prefix='dep')
            else:
                dep_form = DependentForm(request.POST, prefix='dep')
            ben_form = BeneficiaryForm(prefix='ben')  # Unbound

            dep_data = dep_form.data if dep_form.is_bound else {}
            any_filled = any(dep_data.get(f'dep-{f}') for f in ['id_number','first_name','last_name','date_of_birth']) and dep_data.get('dep-relationship') not in [None, '', 'Select...']
            if any_filled:
                if dep_form.is_valid():
                    max_dependents = getattr(policy.plan, 'max_dependents', 7)
                    if dependents.count() >= max_dependents:
                        dep_form.add_error(None, f'Maximum number of dependents ({max_dependents}) reached for this plan.')
                        form_errors.append(f'Maximum number of dependents ({max_dependents}) reached for this plan.')
                    else:
                        d = dep_form.save(commit=False)
                        d.policy = policy
                        d.member = member
                        d.save()
                        return redirect('members:step3_dependents', member_id=member.id)
                else:
                    form_errors.extend([f"Dependent: {err}" for err in dep_form.errors.values()])
            elif not any_filled:
                dep_form = DependentForm(prefix='dep')
            dependents = policy.dependents.all()
            beneficiaries = policy.beneficiaries.all()

        # Handle beneficiary form submission
        elif 'save_beneficiary' in request.POST:
            edit_id = request.POST.get('edit_ben_id')
            if edit_id:
                editing_beneficiary = get_object_or_404(Beneficiary, pk=edit_id, policy=policy)
                ben_form = BeneficiaryForm(request.POST, instance=editing_beneficiary, prefix='ben')
            else:
                ben_form = BeneficiaryForm(request.POST, prefix='ben')
            dep_form = DependentForm(prefix='dep')  # Unbound

            if ben_form.is_valid():
                b = ben_form.save(commit=False)
                b.policy = policy
                b.save()
                beneficiaries = policy.beneficiaries.all()
                dependents = policy.dependents.all()
                return redirect('members:step3_dependents', member_id=member.id)
            else:
                form_errors.extend([f"Beneficiary: {err}" for err in ben_form.errors.values()])

    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    return render(request, 'members/step3_dependents_beneficiaries.html', {
        'dep_form': dep_form,
        'ben_form': ben_form,
        'dependents': dependents,
        'beneficiaries': beneficiaries,
        'editing_dependent': editing_dependent,
        'editing_beneficiary': editing_beneficiary,
        'form_errors': form_errors,
        'policy': policy,
        'member': member,
        'step': 3,
        'steps': STEP_RANGE,
        'base_template': base_template,
    })


# ─── Wizard Step 6: Payment Options ────────────────────────────────────────────
@login_required
def create_payment_options(request, pk):
    """
    Step 6: Payment Options
    Allow users to select a payment method (EasyPay, Debit Order, or EFT) and generate
    Easypay number, barcode, and QR code for payment.
    """
    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member
    
    # Import utility functions
    from members.utils.easypay import generate_easypay_number, generate_qr_code_image, generate_barcode_image
    from members.utils.links import payment_link
    from django.conf import settings
    import os
    
    # Generate Easypay number, barcode, and QR code if not already generated
    if not policy.easypay_number:
        # Generate Easypay number
        policy.easypay_number = generate_easypay_number(policy.pk)
        
        # Generate barcode and QR code images
        if hasattr(policy.plan, 'main_premium'):
            payment_amount = policy.plan.main_premium
        else:
            payment_amount = policy.premium_amount
            
        # Generate and save barcode image
        barcode_image = generate_barcode_image(policy.easypay_number)
        policy.barcode.save(barcode_image.name, barcode_image)
        
        # Generate and save QR code image
        qr_image = generate_qr_code_image(policy.easypay_number)
        policy.qr_code.save(qr_image.name, qr_image)
        
        # Save the policy with the new Easypay number and images
        policy.save()
    
    if request.method == 'POST':
        form = PaymentOptionsForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            return redirect('members:step7_otp_verification', pk=policy.pk)
    else:
        form = PaymentOptionsForm(instance=policy)
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    return render(request, 'members/step6_payment_options.html', {
        'form': form,
        'policy': policy,
        'barcode_url': policy.barcode.url if policy.barcode else None,
        'qr_url': policy.qr_code.url if policy.qr_code else None,
        'step': 6,
        'steps': range(1, 10),
        'base_template': base_template,
    })


# ─── Wizard Step 7: OTP Verification ──────────────────────────────────────────
@login_required
def step7_otp_verification(request, pk):
    """
    Step 7: OTP Verification
    Send a 6-digit OTP to the member's phone number and verify it before proceeding.
    """
    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member
    
    # Import utility functions
    from members.utils.sms_sender import send_otp
    from members.utils.otp import generate_otp, hash_otp, verify_otp
    from django.utils import timezone
    
    # Check if OTP verification already exists, create if not
    otp_verification, created = OtpVerification.objects.get_or_create(
        policy=policy,
        defaults={
            'code_hash': '',
            'sent_at': timezone.now(),
            'attempts': 0,
            'resent_count': 0
        }
    )
    
    # If this is a new OTP verification or a resend request, generate and send OTP
    if created or request.GET.get('resend') == '1':
        # Generate a new 6-digit OTP
        otp_code = generate_otp()
        
        # Hash and store the OTP
        otp_verification.code_hash = hash_otp(otp_code)
        otp_verification.sent_at = timezone.now()
        otp_verification.attempts = 0
        otp_verification.resent_count += 1
        otp_verification.save()
        
        # Send the OTP via SMS
        phone_number = member.phone_number
        send_result = send_otp(phone_number, otp_code)
        
        if not send_result.get('success', False):
            messages.error(request, "Failed to send OTP. Please try again or contact support.")
    
    # Handle OTP verification
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '')
        
        # Verify the entered OTP
        is_valid = verify_otp(
            entered_otp=entered_otp,
            stored_hash=otp_verification.code_hash,
            sent_at=otp_verification.sent_at,
            expiry_minutes=10
        )
        
        # Increment attempt counter
        otp_verification.attempts += 1
        otp_verification.save()
        
        if is_valid:
            # Mark policy as OTP confirmed
            policy.otp_confirmed = True
            policy.save()
            
            # Send confirmation SMS
            from members.utils.sms_sender import send_policy_confirmation
            send_policy_confirmation(member.phone_number, policy.easypay_number)
            
            # Redirect to next step
            messages.success(request, "Phone number verified successfully!")
            return redirect('members:step8_policy_summary', pk=policy.pk)
        else:
            # Check if too many attempts
            if otp_verification.attempts >= 3:
                messages.error(request, "Too many incorrect attempts. Please request a new code.")
            else:
                messages.error(request, "Invalid verification code. Please try again.")
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    # Mask the phone number for display
    masked_phone = ""
    if member.phone_number:
        # Keep first 3 and last 2 digits visible, mask the rest
        phone = member.phone_number.replace("+", "").replace(" ", "")
        if len(phone) > 5:
            masked_phone = f"{phone[:3]}{'*' * (len(phone) - 5)}{phone[-2:]}"
        else:
            masked_phone = phone
    
    return render(request, 'members/step7_otp_verification.html', {
        'policy': policy,
        'member': member,
        'masked_phone': masked_phone,
        'attempts': otp_verification.attempts,
        'max_attempts': 3,
        'resent_count': otp_verification.resent_count,
        'step': 7,
        'steps': range(1, 10),
        'base_template': base_template,
    })

# Legacy OTP verification function (kept for backward compatibility)
@login_required
def otp_verification(request, member_id):
    # Redirect to the new URL pattern with pk instead of member_id
    member = get_object_or_404(Member, pk=member_id)
    policy = get_object_or_404(Policy, member=member)
    return redirect('members:step7_otp_verification', pk=policy.pk)


# ─── OTP Resend Function ────────────────────────────────────────────────────────
@login_required
def resend_otp(request, policy_id=None, pk=None):
    """
    Resend OTP to the member's phone number.
    This function handles both the legacy URL pattern with policy_id and the new pattern with pk.
    """
    # Handle both URL patterns
    policy_pk = pk if pk is not None else policy_id
    policy = get_object_or_404(Policy, pk=policy_pk)
    
    # Import utility functions
    from members.utils.sms_sender import send_otp
    from members.utils.otp import generate_otp, hash_otp
    from django.utils import timezone
    
    # Get or create OTP verification
    otp_verification, created = OtpVerification.objects.get_or_create(
        policy=policy,
        defaults={
            'code_hash': '',
            'sent_at': timezone.now(),
            'attempts': 0,
            'resent_count': 0
        }
    )
    
    # Generate a new 6-digit OTP
    otp_code = generate_otp()
    
    # Hash and store the OTP
    otp_verification.code_hash = hash_otp(otp_code)
    otp_verification.sent_at = timezone.now()
    otp_verification.attempts = 0
    otp_verification.resent_count += 1
    otp_verification.save()
    
    # Send the OTP via SMS
    phone_number = policy.member.phone_number
    send_result = send_otp(phone_number, otp_code)
    
    # Return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'success': send_result.get('success', False),
            'message': 'OTP resent successfully' if send_result.get('success', False) else 'Failed to send OTP'
        })
    
    # If not AJAX, redirect back with message
    if send_result.get('success', False):
        messages.success(request, "Verification code has been resent successfully!")
    else:
        messages.error(request, "Failed to send verification code. Please try again or contact support.")
    # Redirect back to the OTP verification page
    return redirect('members:step7_otp_verification', pk=policy.pk)


# ─── Wizard Step 8: Policy Summary ───────────────────────────────────────

@login_required
def step8_policy_summary(request, pk):
    """
    Step 8: Policy Summary
    Show a summary of all policy details for review before final confirmation.
    """
    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member
    
    # Check if OTP has been confirmed
    if not policy.otp_confirmed:
        messages.warning(request, "You must verify your phone number before proceeding.")
        return redirect('members:step7_otp_verification', pk=policy.pk)
    
    # Get all dependents for this policy
    dependents = Dependent.objects.filter(policy=policy).order_by('relationship_type', 'first_name')
    
    # Get all beneficiaries for this policy
    beneficiaries = Beneficiary.objects.filter(policy=policy).order_by('percentage', 'first_name')
    
    # Calculate total premium
    total_premium = policy.plan.premium if policy.plan else 0
    for dependent in dependents:
        total_premium += dependent.premium or 0
    
    # Calculate total cover amount
    total_cover = policy.plan.cover_amount if policy.plan else 0
    for dependent in dependents:
        total_cover += dependent.cover_amount or 0
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    # Handle form submission (proceed to next step)
    if request.method == 'POST':
        # Mark policy as complete
        policy.is_complete = True
        policy.save()
        
        # Redirect to final confirmation page
        return redirect('members:step9_policy_confirmation', pk=policy.pk)
    
    return render(request, 'members/step8_policy_summary.html', {
        'policy': policy,
        'member': member,
        'dependents': dependents,
        'beneficiaries': beneficiaries,
        'total_premium': total_premium,
        'total_cover': total_cover,
        'step': 8,
        'steps': range(1, 10),
        'base_template': base_template,
    })


# Legacy policy summary function (kept for backward compatibility)
def policy_summary(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    policy = get_object_or_404(Policy, member=member)
    return redirect('members:step8_policy_summary', pk=policy.pk)


# ─── Policy Document Download ───────────────────────────────────────

@login_required
def download_policy_document(request, pk):
    """
    Download the policy document PDF.
    If the document doesn't exist, generate it first.
    """
    policy = get_object_or_404(Policy, pk=pk)
    
    # Check if user has permission to access this policy
    if request.user.is_staff or policy.member.user == request.user:
        # Generate document if it doesn't exist
        if not policy.document:
            from members.utils.pdf_generator import generate_and_save_policy_document
            success = generate_and_save_policy_document(policy)
            if not success:
                messages.error(request, "Failed to generate policy document. Please try again later.")
                return redirect('members:step9_policy_confirmation', pk=policy.pk)
        
        # Serve the document
        from django.http import FileResponse
        response = FileResponse(policy.document, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="LegacyPolicy_{policy.policy_number}.pdf"'
        return response
    else:
        messages.error(request, "You don't have permission to access this document.")
        return redirect('members:dashboard')


# ─── Wizard Step 9: Policy Confirmation ─────────────────────────────────

@login_required
def step9_policy_confirmation(request, pk):
    """
    Step 9: Policy Confirmation
    Final confirmation page showing that the policy has been successfully created.
    """
    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member
    
    # Check if policy is complete
    if not policy.is_complete:
        messages.warning(request, "You must complete all previous steps before accessing the confirmation page.")
        return redirect('members:step8_policy_summary', pk=policy.pk)
    
    # Generate PDF document if it doesn't exist yet
    if not policy.document:
        from members.utils.pdf_generator import generate_and_save_policy_document
        success = generate_and_save_policy_document(policy)
        if success:
            messages.success(request, "Policy document has been generated successfully.")
        else:
            messages.warning(request, "There was an issue generating the policy document. Please try again later.")
    
    # Send email with policy document if not already sent
    if policy.document and member.email and not policy.email_sent_at:
        from members.utils.email_sender import send_policy_document_email
        if send_policy_document_email(policy):
            messages.success(request, f"Policy document has been emailed to {member.email}.")
        else:
            messages.warning(request, "There was an issue sending the policy document via email. Please try again later.")
    
    # Generate WhatsApp share link if document exists
    whatsapp_url = None
    if policy.document:
        from urllib.parse import quote
        share_text = f"Hi there, here is my Legacy policy document: {request.build_absolute_uri(policy.document.url)}"
        whatsapp_url = f"https://wa.me/?text={quote(share_text)}"
    
    # Determine which base template to use
    base_template = "base_diy.html" if request.session.get('is_diy_signup') else "base.html"
    
    return render(request, 'members/step9_policy_confirmation.html', {
        'policy': policy,
        'member': member,
        'whatsapp_url': whatsapp_url,
        'step': 9,
        'steps': range(1, 10),
        'base_template': base_template,
    })
@login_required
def policy_certificate(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    policy = get_object_or_404(Policy, member=member)
    return render(request, 'members/step6_policy_completion.html', {
        'member': member,
        'policy': policy,
        'step': 6,
        'steps': STEP_RANGE,
    })


# ─── Wizard Step 7: Done ──────────────────────────────────────────────────────
# members/views_diy.py or members/views.py (wherever your DIY logic is handled)
from django.shortcuts import render, get_object_or_404
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from members.models import Member, Policy
from django.conf import settings

def create_done(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    policy = get_object_or_404(Policy, member=member)

    # ─── Generate PDF ─────────────────────────────────────────────────────
    html = render_to_string('members/policy_pdf_template.html', {
        'member': member,
        'policy': policy
    })
    pdf_file = HTML(string=html).write_pdf()

    # ─── Email with PDF ───────────────────────────────────────────────────
    if member.email:
        email = EmailMessage(
            subject="Your Trinity Funeral Policy Document",
            body=render_to_string('members/email/policy_confirmation.txt', {
                'member': member,
                'policy': policy
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[member.email],
        )
        email.attach(f"{policy.membership_number}.pdf", pdf_file, 'application/pdf')
        email.send()

    return render(request, 'members/step7_create_done.html', {
        'member': member,
        'policy': policy,
        'step': 7,
        'steps': range(1, 8),
    })




# ─── Find Policy ──────────────────────────────────────────────────────────────from django.shortcuts import render
@login_required
def find_policy(request):
    q = request.GET.get('q', '').strip()  # Get search query from GET parameters

    # Only filter if there's a search query; otherwise, return an empty list
    if q:
        members_qs = Member.objects.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(id_number__icontains=q)
        )
    else:
        members_qs = []  # If no query, return empty list

    # Ensure we get the related policy (first one) for the member
    policies = Policy.objects.filter(member__in=members_qs)  # Adjusted to filter based on member

    # Group check logic moved to the view to avoid recursion in the template
    is_superuser = request.user.is_superuser
    is_branch_owner = request.user.groups.filter(name="Branch Owner").exists()
    is_scheme_admin = request.user.groups.filter(name="Scheme Admin").exists()

    # Pass the policies and group check results to the template
    return render(request, 'members/find_policy/base_profile.html', {
        'members': members_qs,  # Pass the filtered members to the template
        'q': q,  # Pass the search query to display it in the search box
        'selected_tab': 'search',  # To maintain the active tab (if needed)
        'policies': policies,  # Pass the policies object to the template
        'is_superuser': is_superuser,  # Pass if the user is superuser
        'is_branch_owner': is_branch_owner,  # Pass if the user is a Branch Owner
        'is_scheme_admin': is_scheme_admin,  # Pass if the user is a Scheme Admin
    })


# ─── Policy Detail / Inline-Edit Tabs ──────────────────────────────────────────
@login_required
def policy_detail(request, policy_id):
    policy = get_object_or_404(Policy, pk=policy_id)
    member = policy.member
    selected_tab = request.GET.get('selected_tab', 'personal')

    if request.method == 'POST':
        tab = request.POST.get('tab')
        if tab == 'personal':
            f = PersonalDetailsEditForm(request.POST, instance=member)
            if f.is_valid():
                f.save()
        elif tab == 'policy':
            f = PolicyEditForm(request.POST, instance=policy)
            if f.is_valid():
                f.save()
        elif tab in ('dependents', 'beneficiaries'):
            return redirect('members:step3_dependents', member_id=member.id)
        elif tab == 'payment':
            f = PaymentOptionsEditForm(request.POST, instance=policy)
            if f.is_valid():
                f.save()
        elif tab == 'notes':
            f = NotesForm(request.POST)
            if f.is_valid():
                pass  # TODO: save note
        elif tab == 'communication':
            f = CommunicationForm(request.POST, request.FILES)
            if f.is_valid():
                pass  # TODO: dispatch communication

        return redirect(f"{reverse('members:policy_detail', args=[policy_id])}?selected_tab={tab}")

    ctx = {
        'policy': policy,
        'member': member,
        'selected_tab': selected_tab,
        'personal_form': PersonalDetailsEditForm(instance=member),
        'address_form': AddressEditForm(instance=member),
        'policy_form': PolicyEditForm(instance=policy),
        'payments_form': PaymentOptionsEditForm(instance=policy),
        'dependents': policy.dependents.all(),
        'beneficiaries': policy.beneficiaries.all(),
        'notes': [],
    }
    return render(request, 'members/find_policy/base_profile.html', ctx)


# ─── Delete Tabs ──────────────────────────────────────────────────────────────
@login_required
def delete_dependent(request, policy_id, dep_id):
    policy = get_object_or_404(Policy, pk=policy_id)
    dep = get_object_or_404(Dependent, pk=dep_id, policy=policy)
    member_id = policy.member_id
    if request.method == 'POST':
        dep.delete()
        return redirect('members:step3_dependents', member_id=member_id)
    return render(request, 'members/find_policy/edit_policy/confirm_delete_dependent.html', {
        'dependent': dep,
        'policy': policy,
    })


@login_required
def delete_beneficiary(request, policy_id, ben_id):
    policy = get_object_or_404(Policy, pk=policy_id)
    ben = get_object_or_404(Beneficiary, pk=ben_id, policy=policy)
    member_id = policy.member_id
    if request.method == 'POST':
        ben.delete()
        return redirect('members:step3_dependents', member_id=member_id)
    return render(request, 'members/find_policy/edit_policy/confirm_delete_beneficiary.html', {
        'beneficiary': ben,
        'policy': policy,
    })


# ─── AJAX Helpers ────────────────────────────────────────────────────────────
@login_required
def resend_otp(request, policy_id):
    policy = get_object_or_404(Policy, pk=policy_id)
    otp, _ = OtpVerification.objects.get_or_create(policy=policy)
    otp.generate_new_code()
    send_bulk_sms(policy.member.phone_number, f"Your OTP is {otp.plain_code}")
    return JsonResponse({'status': 'ok'})


@login_required
def resend_certificate_email(request, policy_id):
    return JsonResponse({'status': 'ok'})

def policy_edit(request, id):
    policy = get_object_or_404(Policy, id=id)
    # Logic to handle policy editing
    return render(request, 'members/policy_edit.html', {'policy': policy})

def download_policy_certificate(request, policy_id):
    # Get the policy object by ID or return 404 if not found
    policy = get_object_or_404(Policy, pk=policy_id)

    # Generate or fetch the certificate (This is a simple example; replace with actual certificate generation logic)
    certificate_content = f"Certificate for policy: {policy.membership_number}"

    # Create the response with a PDF content type
    response = HttpResponse(certificate_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="policy_{policy.membership_number}_certificate.pdf"'

    return response
