"""
Context processors for the accounts app.

This module provides context processors that add useful variables to the template context.
"""

def user_permissions(request):
    """
    Add the current user's permissions to the template context.
    
    This makes it easy to check permissions in templates without having to
    pass them from every view.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}
        
    user = request.user
    
    # Get user's primary role
    if hasattr(user, 'profile'):
        primary_role = user.profile.primary_role
    elif user.is_superuser:
        primary_role = 'Superuser'
    elif user.is_staff:
        primary_role = 'Staff'
    else:
        primary_role = 'User'
    
    # Get user's permissions
    if hasattr(user, 'profile'):
        user_perms = user.profile.get_permissions()
    else:
        user_perms = set()
    
    # Common permission checks
    is_admin = user.is_superuser or user.is_staff or 'admin' in user_perms
    
    return {
        'user_permissions': user_perms,
        'user_primary_role': primary_role,
        'is_admin': is_admin,
        'can_manage_users': is_admin or 'manage_users' in user_perms,
        'can_manage_roles': is_admin or 'manage_roles' in user_perms,
        'can_view_reports': is_admin or 'view_reports' in user_perms,
        'can_manage_settings': is_admin or 'manage_settings' in user_perms,
    }
