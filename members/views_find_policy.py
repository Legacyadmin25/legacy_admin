from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from settings_app.models import Branch, Agent, UserRole
from schemes.models import Scheme, Plan
from members.models import Policy, Member

@login_required
def find_policy(request):
    # Get search parameters
    q = request.GET.get('q', '').strip()  # Main search query
    
    # Advanced filters
    status = request.GET.get('status', '')
    branch_id = request.GET.get('branch', '')
    scheme_id = request.GET.get('scheme', '')
    agent_id = request.GET.get('agent', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    cover_min = request.GET.get('cover_min', '')
    cover_max = request.GET.get('cover_max', '')
    age_min = request.GET.get('age_min', '')
    age_max = request.GET.get('age_max', '')
    payment_method = request.GET.get('payment_method', '')
    
    # Check if we have an exact policy number match for auto-redirect
    if q and len(q.strip()) >= 5:  # Only check for longer queries that might be policy numbers
        exact_policy = Policy.objects.filter(
            Q(policy_number=q) | 
            Q(uw_membership_number=q)
        ).first()
        
        if exact_policy:
            return redirect(reverse('members:policy_detail', kwargs={'policy_id': exact_policy.id}))
    
    # Start with base queryset with all related objects for performance
    policies = Policy.objects.select_related(
        'member', 'plan', 'scheme'
    ).prefetch_related(
        'member__dependents', 'member__beneficiaries'
    )
    
    # Get user role for filtering
    try:
        user_role = request.user.role.role_type
        user_branch = request.user.role.branch
        user_scheme = request.user.role.scheme
    except (UserRole.DoesNotExist, AttributeError):
        user_role = None
        user_branch = None
        user_scheme = None
    
    # Apply role-based filtering
    if user_role == 'scheme_manager' and user_scheme:
        policies = policies.filter(scheme=user_scheme)
    elif user_role == 'branch_owner' and user_branch:
        policies = policies.filter(scheme__branch=user_branch)
    elif user_role not in ['internal_admin', 'compliance_auditor']:
        # For regular users or agents, only show their own policies
        if hasattr(request.user, 'agent'):
            policies = policies.filter(agent=request.user.agent)
        else:
            policies = policies.none()
    
    # Apply search filter if query exists
    if q:
        policies = policies.filter(
            Q(member__first_name__icontains=q) |
            Q(member__last_name__icontains=q) |
            Q(member__id_number__icontains=q) |
            Q(member__phone_number__icontains=q) |
            Q(policy_number__icontains=q) |
            Q(uw_membership_number__icontains=q)
        )
    
    # Apply advanced filters if provided
    if status:
        if status == 'active':
            policies = policies.filter(is_active=True)
        elif status == 'lapsed':
            policies = policies.filter(is_active=False)
        elif status == 'trial':
            policies = policies.filter(is_trial=True)
    
    # Apply branch filter if selected and user has permission
    if branch_id and branch_id.isdigit() and user_role in ['internal_admin', 'compliance_auditor']:
        policies = policies.filter(scheme__branch_id=branch_id)
    
    # Apply scheme filter if selected and user has permission
    if scheme_id and scheme_id.isdigit():
        # Check if user has permission to view this scheme
        if user_role in ['internal_admin', 'compliance_auditor'] or \
           (user_role == 'branch_owner' and user_branch and \
            Scheme.objects.filter(id=scheme_id, branch=user_branch).exists()) or \
           (user_role == 'scheme_manager' and user_scheme and user_scheme.id == int(scheme_id)):
            policies = policies.filter(scheme_id=scheme_id)
    
    # Apply agent filter if selected
    if agent_id and agent_id.isdigit():
        policies = policies.filter(agent_id=agent_id)
    
    # Apply date range filters
    if date_from:
        try:
            policies = policies.filter(start_date__gte=date_from)
        except ValueError:
            pass  # Invalid date format, ignore
    
    if date_to:
        try:
            policies = policies.filter(start_date__lte=date_to)
        except ValueError:
            pass  # Invalid date format, ignore
    
    # Apply cover amount filters
    if cover_min and cover_min.isdigit():
        policies = policies.filter(cover_amount__gte=cover_min)
    
    if cover_max and cover_max.isdigit():
        policies = policies.filter(cover_amount__lte=cover_max)
    
    # Apply payment method filter
    if payment_method:
        policies = policies.filter(payment_method=payment_method)
    
    # Order by most recent start date first
    policies = policies.order_by('-start_date')
    
    # Pagination - 25 results per page
    paginator = Paginator(policies, 25)
    page = request.GET.get('page')
    
    try:
        paginated_policies = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        paginated_policies = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        paginated_policies = paginator.page(paginator.num_pages)
    
    # Get available branches, schemes, and agents for filters based on user role
    if user_role in ['internal_admin', 'compliance_auditor']:
        branches = Branch.objects.all().order_by('name')
        schemes = Scheme.objects.all().order_by('name')
        agents = Agent.objects.all().order_by('full_name')
    elif user_role == 'branch_owner' and user_branch:
        branches = [user_branch]  # Only show their own branch
        schemes = Scheme.objects.filter(branch=user_branch).order_by('name')
        agents = Agent.objects.filter(scheme__branch=user_branch).order_by('full_name')
    elif user_role == 'scheme_manager' and user_scheme:
        branches = [user_scheme.branch] if user_scheme.branch else []
        schemes = [user_scheme]  # Only show their own scheme
        agents = Agent.objects.filter(scheme=user_scheme).order_by('full_name')
    else:
        branches = []
        schemes = []
        agents = []
    
    # Get available payment methods for the filter
    payment_methods = [
        ('DEBIT_ORDER', 'Debit Order'),
        ('EFT', 'EFT'),
        ('EASYPAY', 'Easypay')
    ]
    
    # Prepare context data for the template
    context = {
        'policies': paginated_policies,
        'branches': branches,
        'schemes': schemes,
        'agents': agents,
        'payment_methods': payment_methods,
        'q': q,
        'status': status,
        'selected_branch': branch_id,
        'selected_scheme': scheme_id,
        'selected_agent': agent_id,
        'date_from': date_from,
        'date_to': date_to,
        'cover_min': cover_min,
        'cover_max': cover_max,
        'age_min': age_min,
        'age_max': age_max,
        'selected_payment_method': payment_method,
        'selected_tab': 'search',
        'user_role': user_role,
        'total_results': paginator.count,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': paginated_policies,
    }
    
    return render(request, 'members/find_policy/tabs/member_search.html', context)
