"""
Central Role Permissions Registry

This module defines the permissions associated with each role in the system.
It serves as a single source of truth for role-based access control throughout the application.
"""

ROLE_PERMISSIONS = {
    "Internal Admin": ["all"],
    "Superuser": ["admin", "view_all", "settings"],
    "Administrator": ["dashboard_access", "view_reports", "manage_users"],
    "BranchOwner": ["dashboard_access", "view_branch", "payments", "reminders"],
    "SchemeManager": ["dashboard_access", "view_scheme", "payments", "claims", "reports"],
    "Finance Officer": ["dashboard_access", "payments", "receipts", "exports"],
    "Claims Officer": ["dashboard_access", "claims", "claims_approve", "documents"],
    "Agent": ["dashboard_access", "policy_create", "client_referral", "view_own"],
    "Compliance Auditor": ["dashboard_access", "read_only"]
}

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
    user_groups = [group.name for group in user.groups.all()]
    
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
    user_groups = [group.name for group in user.groups.all()]
    
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
        
    # Define group hierarchy (highest priority first)
    group_hierarchy = [
        "Internal Admin",
        "Administrator",
        "BranchOwner",
        "SchemeManager",
        "Finance Officer",
        "Claims Officer",
        "Agent",
        "Compliance Auditor"
    ]
    
    # Get user's groups
    user_groups = [group.name for group in user.groups.all()]
    
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
    from schemes.models import Scheme
    from settings_app.models import UserRole
    
    # Superusers and internal admins see all schemes
    if user.is_superuser or user.groups.filter(name__in=['Superuser', 'Internal Admin']).exists():
        return Scheme.objects.all()
    
    # Check if user has a scoped UserRole
    try:
        user_role = user.role
        if user_role.scheme:
            return Scheme.objects.filter(id=user_role.scheme.id)
        if user_role.branch:
            # If assigned to branch, show all schemes in that branch
            return Scheme.objects.filter(branch=user_role.branch)
    except (AttributeError, UserRole.DoesNotExist):
        pass
    
    # Default: user can't see any schemes
    return Scheme.objects.none()


def get_user_branches(user):
    """
    Get all branches the user has access to based on their role.
    
    Args:
        user: The user to get accessible branches for
        
    Returns:
        QuerySet: Branch objects the user can access
    """
    from branches.models import Branch
    from settings_app.models import UserRole
    
    # Superusers and internal admins see all branches
    if user.is_superuser or user.groups.filter(name__in=['Superuser', 'Internal Admin']).exists():
        return Branch.objects.all()
    
    # Check if user has a scoped UserRole
    try:
        user_role = user.role
        if user_role.branch:
            return Branch.objects.filter(id=user_role.branch.id)
    except (AttributeError, UserRole.DoesNotExist):
        pass
    
    # Default: user can't see any branches
    return Branch.objects.none()


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
    if user.is_superuser or user.groups.filter(name__in=['Superuser', 'Internal Admin']).exists():
        return queryset
    
    # Get user's accessible schemes and branches
    accessible_schemes = get_user_schemes(user)
    accessible_branches = get_user_branches(user)
    
    # Filter based on model type
    model_name = model_class.__name__
    
    if model_name in ['Member', 'Policy', 'Dependent', 'Beneficiary']:
        # These models connect through Policy -> Scheme
        return queryset.filter(policy__scheme__in=accessible_schemes)
    elif model_name == 'Payment':
        # Payments connect through Policy -> Scheme
        return queryset.filter(policy__scheme__in=accessible_schemes)
    elif model_name == 'Claim':
        # Claims connect through Policy -> Scheme
        return queryset.filter(policy__scheme__in=accessible_schemes)
    elif model_name in ['Scheme', 'Plan']:
        # These connect directly through branch
        return queryset.filter(branch__in=accessible_branches)
    elif model_name in ['Agent', 'Underwriter']:
        # These are typically branch-scoped
        if accessible_branches.exists():
            return queryset.filter(branch__in=accessible_branches)
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
    if user.groups.filter(name__in=['Internal Admin', 'Superuser', 'Administrator']).exists():
        return True
    
    # BranchOwners can only view their assigned branch
    if user.groups.filter(name='BranchOwner').exists():
        return user.branch_id == branch.id if user.branch else False
    
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
    if user.groups.filter(name__in=['Internal Admin', 'Superuser', 'Administrator']).exists():
        return True
    
    # SchemeManagers can only view their assigned schemes
    if user.groups.filter(name='SchemeManager').exists():
        return user.assigned_schemes.filter(id=scheme.id).exists()
    
    # BranchOwners can view schemes in their branch
    if user.groups.filter(name='BranchOwner').exists():
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
    if user.groups.filter(name__in=['Internal Admin', 'Superuser', 'Administrator']).exists():
        return Branch.objects.all()
    
    # BranchOwners see only their assigned branch
    if user.groups.filter(name='BranchOwner').exists():
        if user.branch:
            return Branch.objects.filter(id=user.branch.id)
        return Branch.objects.none()
    
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
    if user.groups.filter(name__in=['Internal Admin', 'Superuser', 'Administrator']).exists():
        return Scheme.objects.all()
    
    # SchemeManagers see only their assigned schemes
    if user.groups.filter(name='SchemeManager').exists():
        return user.assigned_schemes.all()
    
    # BranchOwners see all schemes in their branch
    if user.groups.filter(name='BranchOwner').exists():
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
    if user.groups.filter(name__in=['Internal Admin', 'Superuser', 'Administrator']).exists():
        return queryset
    
    # Get user's accessible schemes
    accessible_schemes = get_user_accessible_schemes(user)
    accessible_branches = get_user_accessible_branches(user)
    
    # Filter based on model type
    if model_name in ['Member', 'Policy', 'Claim', 'Payment']:
        # These models connect through Policy -> Scheme -> Branch
        if user.groups.filter(name='SchemeManager').exists():
            # SchemeManagers: filter by their assigned schemes
            return queryset.filter(policy__plan__scheme__in=accessible_schemes)
        elif user.groups.filter(name='BranchOwner').exists():
            # BranchOwners: filter by their branch's schemes
            return queryset.filter(policy__plan__scheme__branch=user.branch)
    elif model_name in ['Scheme', 'Plan']:
        # Schemes and Plans filter by branch/assignment
        if user.groups.filter(name='SchemeManager').exists():
            return queryset.filter(scheme__in=accessible_schemes)
        elif user.groups.filter(name='BranchOwner').exists():
            return queryset.filter(scheme__branch=user.branch)
    elif model_name in ['Branch']:
        # Branches filter by direct assignment
        return queryset.filter(id__in=accessible_branches.values_list('id', flat=True))
    
    # Default: restrict to accessible data
    return queryset.none()
