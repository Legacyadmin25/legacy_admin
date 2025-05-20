from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from .models import Policy, Member

# Session key for storing the current policy ID
SESSION_KEY = 'policy_id'

def get_or_create_policy(request, member_id=None):
    """
    Get the current policy from session or create a new one.
    If member_id is provided, associate the policy with that member.
    """
    policy = None
    policy_id = request.session.get(SESSION_KEY)
    
    if policy_id:
        try:
            policy = Policy.objects.get(pk=policy_id, is_complete=False)
            # If member_id is provided and doesn't match, create a new policy
            if member_id and policy.member_id != member_id:
                policy = None
        except Policy.DoesNotExist:
            policy = None
    
    if not policy and member_id:
        member = get_object_or_404(Member, pk=member_id)
        # Create policy with minimal required fields
        policy = Policy(
            member=member,
            start_date=timezone.now().date(),
            cover_amount=0,
            premium_amount=0
        )
        policy.save()
        request.session[SESSION_KEY] = policy.pk
    
    return policy

def validate_policy_step(view_func):
    """
    Decorator to validate policy exists and is in the correct step.
    Redirects to the first step if validation fails.
    """
    def wrapper(request, pk=None, *args, **kwargs):
        policy_id = pk or request.session.get(SESSION_KEY)
        
        if not policy_id:
            messages.error(request, 'No active policy found. Please start a new application.')
            return redirect('members:step1_personal')
        
        try:
            policy = Policy.objects.get(pk=policy_id)
        except Policy.DoesNotExist:
            messages.error(request, 'Policy not found. Please start a new application.')
            if SESSION_KEY in request.session:
                del request.session[SESSION_KEY]
            return redirect('members:step1_personal')
        
        # If policy is complete, redirect to confirmation
        if policy.is_complete:
            return redirect('members:step9_policy_confirmation', policy_id=policy.pk)
            
        return view_func(request, policy, *args, **kwargs)
    
    return wrapper

def clear_policy_session(request):
    """Clear the policy from the session."""
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]

def mark_policy_complete(policy):
    """Mark a policy as complete."""
    policy.is_complete = True
    policy.save()
