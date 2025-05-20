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
