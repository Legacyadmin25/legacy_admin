"""
Utility functions for the member application workflow.
These functions handle validation, step skipping logic, and cover calculations.
"""
from datetime import date
from typing import Dict, List, Tuple, Optional, Any
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from schemes.models import Plan
from .models import Member, Policy, Dependent, Beneficiary

def get_member_age_from_dob(dob):
    """
    Calculate member's age from date of birth.
    
    Args:
        dob: Date of birth
        
    Returns:
        int: The calculated age
    """
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def luhn_check(id_number):
    """
    Returns True if `id_number` passes the Luhn checksum.
    Works on any string of digits.
    
    Args:
        id_number: ID number to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not id_number or not isinstance(id_number, str) or not id_number.isdigit():
        return False
        
    digits = [int(d) for d in str(id_number)]
    checksum = 0
    double = False
    for i in range(len(digits)-1, -1, -1):
        digit = digits[i]
        if double:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
        double = not double
    return checksum % 10 == 0

def extract_dob_from_id(id_number):
    """
    Extract date of birth from South African ID number.
    
    Args:
        id_number: South African ID number (13 digits)
        
    Returns:
        date: Date of birth or None if invalid
    """
    if not id_number or not isinstance(id_number, str) or len(id_number) != 13 or not id_number.isdigit():
        return None
        
    try:
        year_prefix = '19' if int(id_number[0:2]) > 22 else '20'  # Assuming anyone born before 1922 is not alive
        year = int(year_prefix + id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        
        from datetime import date
        return date(year, month, day)
    except (ValueError, TypeError):
        return None

def extract_gender_from_id(id_number):
    """
    Extract gender from South African ID number.
    
    Args:
        id_number: South African ID number (13 digits)
        
    Returns:
        str: 'M' for male, 'F' for female, or None if invalid
    """
    if not id_number or not isinstance(id_number, str) or len(id_number) != 13 or not id_number.isdigit():
        return None
        
    try:
        # Digits 7-10 (0-indexed 6-9) determine gender
        # 0000-4999 = female, 5000-9999 = male
        gender_digits = int(id_number[6:10])
        return 'M' if gender_digits >= 5000 else 'F'
    except (ValueError, TypeError):
        return None

def get_filtered_plans(member: Member) -> List[Plan]:
    """
    Get plans that match the member's age criteria.
    
    Args:
        member: The member to filter plans for
        
    Returns:
        QuerySet: Filtered plans that match the member's age criteria
    """
    if not member or not member.date_of_birth:
        return Plan.objects.none()
    
    # Calculate member's age
    age = get_member_age_from_dob(member.date_of_birth)
    
    # Filter plans based on member's age and active status
    return Plan.objects.filter(
        main_age_from__lte=age,
        main_age_to__gte=age,
        is_active=True
    )

def get_allowed_counts(plan):
    """
    Get the allowed counts for different dependent types based on the plan.
    
    Args:
        plan: The policy plan
        
    Returns:
        dict: Dictionary with allowed counts for spouses, children, and extended members
    """
    if not plan:
        return {'spouses': 0, 'children': 0, 'extended': 0}
    
    return {
        'spouses': plan.spouses_allowed or 0,
        'children': plan.children_allowed or 0,
        'extended': plan.extended_allowed or 0
    }

def get_cover_amount_for_dependent(plan, age, relationship):
    """
    Calculate the cover amount for a dependent based on their age, relationship, and the plan tiers.
    
    Args:
        plan: The policy plan
        age: The dependent's age
        relationship: The relationship type ('spouse', 'child', 'extended')
        
    Returns:
        Decimal: The calculated cover amount
    """
    from decimal import Decimal
    
    if not plan:
        return Decimal('0.00')
    
    # Default cover amount if no tier matches
    default_cover = Decimal('0.00')
    
    # Get tiers for the specific relationship type
    tiers = plan.tiers.filter(member_type=relationship)
    
    # Find the appropriate tier based on age
    for tier in tiers:
        if tier.age_from <= age <= tier.age_to:
            return tier.cover
    
    # If no tier matches, return default cover
    return default_cover

def should_skip_step(policy, step_name):
    """
    Determines if a step should be skipped based on the policy's plan configuration.
    
    Args:
        policy: The policy object
        step_name: The name of the step to check ('spouse', 'children', 'extended')
        
    Returns:
        bool: True if the step should be skipped, False otherwise
    """
    if not policy or not policy.plan:
        return False
        
    plan = policy.plan
    
    if step_name == 'spouse':
        # Skip spouse step if no spouses allowed
        return plan.spouses_allowed == 0
    elif step_name == 'children':
        # Skip children step if no children allowed and no extended allowed
        return plan.children_allowed == 0 and plan.extended_allowed == 0
    elif step_name == 'extended':
        # Skip extended step if no extended allowed
        return plan.extended_allowed == 0
    
    # Default: don't skip
    return False

def validate_beneficiaries(beneficiaries):
    """
    Validates a collection of beneficiaries to ensure they meet the requirements:
    1. No more than 5 beneficiaries
    2. Total share percentage equals 100%
    
    Args:
        beneficiaries: QuerySet or list of Beneficiary objects
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not beneficiaries:
        return False, "At least one beneficiary is required."
    
    # Check maximum number of beneficiaries
    if len(beneficiaries) > 5:
        return False, "Maximum of 5 beneficiaries allowed."
    
    # Calculate total share percentage
    total_share = sum(b.share for b in beneficiaries)
    
    if total_share < 100:
        return False, f"Total beneficiary share is {total_share}%, but must equal 100%."
    elif total_share > 100:
        return False, f"Total beneficiary share is {total_share}%, but cannot exceed 100%."
    
    # All validations passed
    return True, ""

def get_allowed_counts(plan):
    """
    Gets the allowed counts for dependents based on the plan.
    
    Args:
        plan: The plan object
        
    Returns:
        dict: A dictionary containing the allowed counts
    """
    if not plan:
        return {
            'spouses_allowed': 0,
            'children_allowed': 0,
            'extended_allowed': 0
        }
    
    return {
        'spouses_allowed': plan.spouses_allowed,
        'children_allowed': plan.children_allowed,
        'extended_allowed': plan.extended_allowed
    }

def get_cover_amount_for_dependent(plan, age, member_type):
    """
    Calculates the cover amount based on age and member type.
    
    Args:
        plan: The plan object
        age: The age of the dependent
        member_type: The type of member (e.g., 'spouse', 'child', 'extended')
        
    Returns:
        float: The cover amount
    """
    if not plan:
        return 0.0
    
    tiers = plan.tiers.all()
    for tier in tiers:
        if tier.member_type == member_type and tier.age_from <= age <= tier.age_to:
            return tier.cover
    return 0

# Preserve existing useful functions

def get_policy_dependent_counts(policy):
    """
    Gets the current counts for dependents based on the policy.
    
    Args:
        policy: The policy object
        
    Returns:
        dict: A dictionary containing the current counts
    """
    if not policy:
        return {
            'spouse_count': 0,
            'children_count': 0,
            'extended_count': 0
        }
    
    # Count current dependents
    spouse_count = policy.dependents.filter(relationship='Spouse').count()
    children_count = policy.dependents.filter(relationship='Child').count()
    extended_count = policy.dependents.filter(relationship='Extended Family').count()
    
    return {
        'spouse_count': spouse_count,
        'children_count': children_count,
        'extended_count': extended_count
    }

def validate_beneficiaries(beneficiaries):
    """
    Validates that beneficiaries meet the required criteria:
    - Maximum 5 beneficiaries
    - Total share must be 100%
    
    Args:
        beneficiaries: List of beneficiary objects
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(beneficiaries) > 5:
        return False, "Maximum of 5 beneficiaries allowed."
    
    total_share = sum(b.share for b in beneficiaries)
    if total_share != 100:
        return False, f"Total beneficiary share must be 100%. Current total: {total_share}%"
    
    return True, ""

def get_filtered_plans(member):
    """
    Gets plans that match the member's age criteria.
    
    Args:
        member: The member object
        
    Returns:
        list: List of eligible plans
    """
    if not member or not member.date_of_birth:
        return []
    
    age = get_member_age_from_dob(member.date_of_birth)
    
    # Filter plans based on member's age
    return Plan.objects.filter(
        main_age_from__lte=age,
        main_age_to__gte=age,
        is_active=True
    )

def safe_redirect_to_step(member_id, current_step):
    """
    Safely redirects to the appropriate step based on plan configuration.
    Handles cases where steps should be skipped.
    
    Args:
        member_id: The member ID
        current_step: The current step number
        
    Returns:
        redirect: A redirect to the appropriate step, or None if no redirect needed
    """
    try:
        member = Member.objects.get(pk=member_id)
        policy = Policy.objects.filter(member=member).first()
        
        if not policy or not policy.plan:
            return None
            
        next_step = current_step + 1
        
        # Map step numbers to step names
        step_names = {
            3: 'spouse',
            4: 'children'
        }
        
        # Check if we need to skip steps
        while next_step <= 9 and next_step in step_names and should_skip_step(policy, step_names[next_step]):
            next_step += 1
            
        if next_step > 9:
            return redirect('members:policy_confirmation', member_id=member_id)
            
        # Map step numbers to URL names
        step_urls = {
            1: 'members:create_personal',
            2: 'members:step2_policy_details',
            3: 'members:step3_spouse_info',
            4: 'members:step4_children_info',
            5: 'members:step5_beneficiaries',
            6: 'members:step6_payment_options',
            7: 'members:step7_otp_verification',
            8: 'members:step8_policy_summary',
            9: 'members:policy_confirmation'
        }
        
        return redirect(step_urls.get(next_step), member_id=member_id)
    except (Member.DoesNotExist, KeyError):
        return None

def prepare_step_context(request, member_id, step):
    """
    Prepares common context data for step templates.
    
    Args:
        request: The request object
        member_id: The member ID
        step: The current step number
        
    Returns:
        dict: The context dictionary
    """
    from django.db.models import Sum
    
    member = Member.objects.get(pk=member_id)
    policy = Policy.objects.filter(member=member).first()
    
    context = {
        'member': member,
        'policy': policy,
        'step': step,
        'steps': range(1, 8),  # 7 visible steps in progress bar
        'base_template': "base_diy.html" if request.session.get('is_diy_signup') else "base.html",
    }
    
    if policy and policy.plan:
        # Add dependent counts
        plan_counts = get_allowed_counts(policy.plan)
        policy_counts = get_policy_dependent_counts(policy)
        
        context.update({
            'spouses_allowed': plan_counts['spouses_allowed'],
            'children_allowed': plan_counts['children_allowed'],
            'extended_allowed': plan_counts['extended_allowed'],
            'spouse_count': policy_counts['spouse_count'],
            'children_count': policy_counts['children_count'],
            'extended_count': policy_counts['extended_count'],
        })
        
        # Add beneficiary info
        beneficiaries = policy.beneficiaries.all()
        context['beneficiaries'] = beneficiaries
        context['beneficiary_count'] = beneficiaries.count()
        context['beneficiary_share_total'] = beneficiaries.aggregate(total=Sum('share'))['total'] or 0
        
    return context
