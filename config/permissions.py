"""
Central Role Permissions Registry

This module defines the permissions associated with each role in the system.
It serves as a single source of truth for role-based access control throughout the application.
"""

CANONICAL_ROLE_HIERARCHY = [
    "Superuser",
    "Administrator",
    "Compliance Auditor",
    "Finance Officer",
    "Claims Officer",
    "Branch Owner",
    "Scheme Manager",
    "Internal Admin",
    "Agent",
]

ROLE_ALIASES = {
    "Super Users": "Superuser",
    "Superuser": "Superuser",
    "Admin": "Administrator",
    "Administrator": "Administrator",
    "BranchOwner": "Branch Owner",
    "Branch Owner": "Branch Owner",
    "SchemeManager": "Scheme Manager",
    "Scheme Manager": "Scheme Manager",
    "Scheme Admin": "Scheme Manager",
    "Claims": "Claims Officer",
    "Claims Officer": "Claims Officer",
    "Finance": "Finance Officer",
    "Finance Team": "Finance Officer",
    "Finance Officer": "Finance Officer",
    "Data Capturer": "Internal Admin",
    "Internal Admin": "Internal Admin",
    "Compliance Auditor": "Compliance Auditor",
    "Agent": "Agent",
}

ROLE_PERMISSIONS = {
    "Superuser": ["all"],
    "Administrator": [
        "dashboard_access", "view_all", "manage_users", "manage_settings", "manage_agents",
        "manage_schemes", "manage_branches", "manage_policies", "manage_payments",
        "view_reports", "manage_claims", "manage_documents", "generate_agent_signup_links"
    ],
    "Branch Owner": [
        "dashboard_access", "view_branch", "manage_branch", "manage_agents", "manage_schemes",
        "manage_policies", "manage_payments", "view_reports", "generate_agent_signup_links"
    ],
    "Scheme Manager": [
        "dashboard_access", "view_scheme", "manage_agents", "manage_policies", "manage_payments",
        "view_reports", "manage_claims", "manage_documents", "generate_agent_signup_links"
    ],
    "Internal Admin": [
        "dashboard_access", "view_scheme", "manage_policies", "manage_payments", "manage_documents"
    ],
    "Finance Officer": [
        "dashboard_access", "view_all", "manage_payments", "view_reports", "receipts", "exports"
    ],
    "Claims Officer": [
        "dashboard_access", "view_all", "manage_claims", "manage_documents"
    ],
    "Compliance Auditor": [
        "dashboard_access", "view_all", "view_reports", "read_only"
    ],
    "Agent": [
        "view_own", "own_diy_link"
    ],
}


def normalize_role_name(role_name):
    return ROLE_ALIASES.get(role_name, role_name)


def get_canonical_group_names(user):
    if user.is_superuser:
        return ["Superuser"]
    return [normalize_role_name(group.name) for group in user.groups.all()]


def user_has_role(user, *role_names):
    canonical_targets = {normalize_role_name(role_name) for role_name in role_names}
    if "Superuser" in canonical_targets and user.is_superuser:
        return True
    return any(group_name in canonical_targets for group_name in get_canonical_group_names(user))


def is_read_only_user(user):
    return user_has_role(user, "Compliance Auditor")


def can_manage_agents(user):
    return user.is_superuser or user_has_role(user, "Administrator", "Branch Owner", "Scheme Manager")


def can_manage_agent_signup_links(user, agent=None):
    if user.is_superuser or user_has_role(user, "Administrator"):
        return True
    if user_has_role(user, "Agent"):
        return bool(getattr(user, 'agent', None)) and (agent is None or getattr(user, 'agent', None) == agent)
    if agent is None:
        return user_has_role(user, "Branch Owner", "Scheme Manager")
    if user_has_role(user, "Branch Owner"):
        return bool(user.branch_id) and bool(agent.scheme_id) and agent.scheme.branch_id == user.branch_id
    if user_has_role(user, "Scheme Manager"):
        return user.assigned_schemes.filter(id=agent.scheme_id).exists()
    return False

# Permission helpers
def has_permission(user, permission):
    """
    Check if a user has a specific permission based on their role.
    
    Args:
        user: The user to check permissions for
        permission: The permission to check
        
    Returns:
        bool: True if the user has the permission, False otherwise
    """
    # Superusers have all permissions
    if user.is_superuser:
        return True
        
    # Get user's groups
    user_groups = get_canonical_group_names(user)
    
    # Check if user has the permission through any of their groups
    for group_name in user_groups:
        if group_name in ROLE_PERMISSIONS:
            if "all" in ROLE_PERMISSIONS[group_name] or permission in ROLE_PERMISSIONS[group_name]:
                return True
                
    return False

def get_user_permissions(user):
    """
    Get all permissions for a user based on their role.
    
    Args:
        user: The user to get permissions for
        
    Returns:
        list: List of permissions the user has
    """
    # Superusers have all permissions
    if user.is_superuser:
        return ["all"]
        
    # Get user's groups
    user_groups = get_canonical_group_names(user)
    
    # Collect all permissions from user's groups
    permissions = []
    for group_name in user_groups:
        if group_name in ROLE_PERMISSIONS:
            if "all" in ROLE_PERMISSIONS[group_name]:
                return ["all"]
            permissions.extend(ROLE_PERMISSIONS[group_name])
                
    return list(set(permissions))  # Remove duplicates

def get_primary_group(user):
    """
    Get the primary group for a user based on role hierarchy.
    
    Args:
        user: The user to get the primary group for
        
    Returns:
        str: The name of the primary group, or None if no group is found
    """
    if user.is_superuser:
        return "Superuser"
        
    group_hierarchy = CANONICAL_ROLE_HIERARCHY
    user_groups = get_canonical_group_names(user)
    
    # Find the highest priority group
    for group_name in group_hierarchy:
        if group_name in user_groups:
            return group_name
            
    return None


# Multi-tenancy helpers
def get_user_schemes(user):
    """
    Get all schemes the user has access to based on their role.
    
    Args:
        user: The user to get accessible schemes for
        
    Returns:
        QuerySet: Scheme objects the user can access
    """
    return get_user_accessible_schemes(user)


def get_user_branches(user):
    """
    Get all branches the user has access to based on their role.
    
    Args:
        user: The user to get accessible branches for
        
    Returns:
        QuerySet: Branch objects the user can access
    """
    return get_user_accessible_branches(user)


def filter_by_user_scope(queryset, user, model_class):
    """
    Filter a queryset by user's accessible scope (schemes/branches).
    
    Args:
        queryset: The initial queryset to filter
        user: The user to filter by
        model_class: The model class being filtered (Member, Policy, Payment, Claim, etc.)
        
    Returns:
        QuerySet: Filtered queryset based on user scope
    """
    # Superusers and internal admins see all data
    if user.is_superuser or user_has_role(user, 'Administrator', 'Compliance Auditor', 'Finance Officer', 'Claims Officer'):
        return queryset
    
    # Get user's accessible schemes and branches
    accessible_schemes = get_user_schemes(user)
    accessible_branches = get_user_branches(user)
    
    # Filter based on model type
    model_name = model_class.__name__
    
    if model_name in ['Member', 'Policy', 'Dependent', 'Beneficiary']:
        # These models connect through Policy -> Scheme
        if model_name == 'Policy':
            return queryset.filter(scheme__in=accessible_schemes)
        if model_name == 'Member':
            return queryset.filter(policies__scheme__in=accessible_schemes).distinct()
        return queryset.filter(policy__scheme__in=accessible_schemes)
    elif model_name == 'Payment':
        # Payments connect through Policy -> Scheme
        return queryset.filter(policy__scheme__in=accessible_schemes)
    elif model_name == 'Claim':
        # Claims connect through Policy -> Scheme
        return queryset.filter(policy__scheme__in=accessible_schemes)
    elif model_name == 'Scheme':
        return queryset.filter(id__in=accessible_schemes.values_list('id', flat=True))
    elif model_name == 'Plan':
        # These connect directly through branch
        return queryset.filter(scheme__in=accessible_schemes)
    elif model_name == 'Agent':
        return queryset.filter(scheme__in=accessible_schemes)
    elif model_name == 'Underwriter':
        if accessible_branches.exists():
            return queryset.filter(schemes__branch__in=accessible_branches).distinct()
        return queryset.none()
    
    # Default: no restriction (admin access)
    return queryset


# ============================================================================
# NEW DATA ISOLATION HELPERS (Using User.branch and User.assigned_schemes)
# ============================================================================

def can_view_branch(user, branch):
    """
    Check if user can view/access a specific branch.
    
    Args:
        user: The user to check
        branch: The Branch object to check access for
        
    Returns:
        bool: True if user can access the branch
    """
    # Superusers and admins can view all branches
    if user.is_superuser:
        return True
    if user_has_role(user, 'Administrator', 'Compliance Auditor', 'Finance Officer', 'Claims Officer'):
        return True
    
    # BranchOwners can only view their assigned branch
    if user_has_role(user, 'Branch Owner'):
        return user.branch_id == branch.id if user.branch else False

    if user_has_role(user, 'Scheme Manager', 'Internal Admin'):
        return user.assigned_schemes.filter(branch_id=branch.id).exists()
    
    # All other roles start with no access
    return False


def can_view_scheme(user, scheme):
    """
    Check if user can view/access a specific scheme.
    
    Args:
        user: The user to check
        scheme: The Scheme object to check access for
        
    Returns:
        bool: True if user can access the scheme
    """
    # Superusers and admins can view all schemes
    if user.is_superuser:
        return True
    if user_has_role(user, 'Administrator', 'Compliance Auditor', 'Finance Officer', 'Claims Officer'):
        return True
    
    # SchemeManagers can only view their assigned schemes
    if user_has_role(user, 'Scheme Manager', 'Internal Admin'):
        return user.assigned_schemes.filter(id=scheme.id).exists()
    
    # BranchOwners can view schemes in their branch
    if user_has_role(user, 'Branch Owner'):
        return scheme.branch_id == user.branch_id if user.branch else False
    
    # All other roles start with no access
    return False


def get_user_accessible_branches(user):
    """
    Get QuerySet of branches accessible by the user (using direct assignment).
    
    Args:
        user: The user to get accessible branches for
        
    Returns:
        QuerySet: Branch objects the user can access
    """
    from branches.models import Branch
    
    # Superusers and admins see all branches
    if user.is_superuser:
        return Branch.objects.all()
    if user_has_role(user, 'Administrator', 'Compliance Auditor', 'Finance Officer', 'Claims Officer'):
        return Branch.objects.all()
    
    # BranchOwners see only their assigned branch
    if user_has_role(user, 'Branch Owner'):
        if user.branch:
            return Branch.objects.filter(id=user.branch.id)
        return Branch.objects.none()

    if user_has_role(user, 'Scheme Manager', 'Internal Admin'):
        return Branch.objects.filter(schemes__in=user.assigned_schemes.all()).distinct()
    
    # Other roles have no direct branch access
    return Branch.objects.none()


def get_user_accessible_schemes(user):
    """
    Get QuerySet of schemes accessible by the user (using direct assignment).
    
    Args:
        user: The user to get accessible schemes for
        
    Returns:
        QuerySet: Scheme objects the user can access
    """
    from schemes.models import Scheme
    
    # Superusers and admins see all schemes
    if user.is_superuser:
        return Scheme.objects.all()
    if user_has_role(user, 'Administrator', 'Compliance Auditor', 'Finance Officer', 'Claims Officer'):
        return Scheme.objects.all()
    
    # SchemeManagers see only their assigned schemes
    if user_has_role(user, 'Scheme Manager', 'Internal Admin'):
        return user.assigned_schemes.all()
    
    # BranchOwners see all schemes in their branch
    if user_has_role(user, 'Branch Owner'):
        if user.branch:
            return Scheme.objects.filter(branch=user.branch)
        return Scheme.objects.none()
    
    # Other roles have no direct scheme access
    return Scheme.objects.none()


def filter_queryset_by_user_scope(queryset, user, model_name):
    """
    Filter a queryset by user's scope (branch/scheme assignments).
    
    Args:
        queryset: The queryset to filter
        user: The user to filter by
        model_name: The name of the model ('Member', 'Policy', 'Scheme', 'Branch', etc.)
        
    Returns:
        QuerySet: Filtered queryset
    """
    # Superusers and admins see all data
    if user.is_superuser:
        return queryset
    if user_has_role(user, 'Administrator', 'Compliance Auditor', 'Finance Officer', 'Claims Officer'):
        return queryset
    
    # Get user's accessible schemes
    accessible_schemes = get_user_accessible_schemes(user)
    accessible_branches = get_user_accessible_branches(user)
    
    # Filter based on model type
    if model_name in ['Member', 'Policy', 'Claim', 'Payment']:
        # These models connect through Policy -> Scheme -> Branch
        if user_has_role(user, 'Scheme Manager', 'Internal Admin'):
            # SchemeManagers: filter by their assigned schemes
            if model_name == 'Policy':
                return queryset.filter(scheme__in=accessible_schemes)
            if model_name == 'Member':
                return queryset.filter(policies__scheme__in=accessible_schemes).distinct()
            return queryset.filter(policy__scheme__in=accessible_schemes)
        elif user_has_role(user, 'Branch Owner'):
            # BranchOwners: filter by their branch's schemes
            if model_name == 'Policy':
                return queryset.filter(scheme__branch=user.branch)
            if model_name == 'Member':
                return queryset.filter(policies__scheme__branch=user.branch).distinct()
            return queryset.filter(policy__scheme__branch=user.branch)
    elif model_name in ['Scheme', 'Plan']:
        # Schemes and Plans filter by branch/assignment
        if model_name == 'Scheme':
            if user_has_role(user, 'Scheme Manager', 'Internal Admin'):
                return queryset.filter(id__in=accessible_schemes.values_list('id', flat=True))
            elif user_has_role(user, 'Branch Owner'):
                return queryset.filter(branch=user.branch)
        else:
            if user_has_role(user, 'Scheme Manager', 'Internal Admin'):
                return queryset.filter(scheme__in=accessible_schemes)
            elif user_has_role(user, 'Branch Owner'):
                return queryset.filter(scheme__branch=user.branch)
    elif model_name in ['Branch']:
        # Branches filter by direct assignment
        return queryset.filter(id__in=accessible_branches.values_list('id', flat=True))
    
    # Default: restrict to accessible data
    return queryset.none()
