import json
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import Member, Policy
from settings_app.models import UserRole

@login_required
def search_suggestions(request):
    """
    API endpoint for providing search suggestions as the user types.
    Supports searching by name, ID number, phone number, and policy number.
    Also handles exact matches for policy numbers and redirects.
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Get user role for filtering
    user = request.user
    try:
        user_role = user.role.role_type
        user_branch = user.role.branch
        user_scheme = user.role.scheme
    except (UserRole.DoesNotExist, AttributeError):
        user_role = None
        user_branch = None
        user_scheme = None
    
    # Base queryset with role-based filtering
    policies_qs = Policy.objects.select_related('member', 'scheme', 'plan')
    
    # Apply role-based filtering
    if user_role == 'scheme_manager' and user_scheme:
        policies_qs = policies_qs.filter(scheme=user_scheme)
    elif user_role == 'branch_owner' and user_branch:
        policies_qs = policies_qs.filter(scheme__branch=user_branch)
    elif user_role not in ['internal_admin', 'compliance_auditor']:
        # For regular users or agents, only show their own policies
        if hasattr(user, 'agent'):
            policies_qs = policies_qs.filter(agent=user.agent)
        else:
            policies_qs = policies_qs.none()
    
    # Check for exact policy number match first
    exact_match = None
    exact_policy = policies_qs.filter(
        Q(policy_number=query) | 
        Q(uw_membership_number=query)
    ).first()
    
    if exact_policy:
        exact_match = {
            'id': exact_policy.id,
            'redirect_url': reverse('members:policy_detail', kwargs={'policy_id': exact_policy.id})
        }
    
    # Search for suggestions
    policies = policies_qs.filter(
        Q(member__first_name__icontains=query) |
        Q(member__last_name__icontains=query) |
        Q(member__id_number__icontains=query) |
        Q(member__phone_number__icontains=query) |
        Q(policy_number__icontains=query) |
        Q(uw_membership_number__icontains=query)
    ).distinct()[:10]  # Limit to 10 suggestions
    
    suggestions = []
    
    for policy in policies:
        member = policy.member
        suggestion = {
            'id': policy.id,
            'text': f"{member.first_name} {member.last_name}",
            'type': 'Policy',
            'extra': f"#{policy.policy_number or policy.uw_membership_number or 'N/A'}",
            'redirect_url': reverse('members:policy_detail', kwargs={'policy_id': policy.id})
        }
        suggestions.append(suggestion)
    
    return JsonResponse({
        'suggestions': suggestions,
        'exact_match': exact_match is not None,
        'redirect_url': exact_match['redirect_url'] if exact_match else None
    })
