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
    
    # Get user's primary role (using property on User model)
    primary_role = user.primary_role
    
    # Get user's permissions
    user_perms = user.get_permissions()
    
    # Common permission checks
    is_admin = user.is_superuser or user.is_staff or user.groups.filter(name__in=['Admin', 'Superuser']).exists()
    
    return {
        'user_permissions': user_perms,
        'user_primary_role': primary_role,
        'is_admin': is_admin,
        'can_manage_users': is_admin or 'manage_users' in [p.codename for p in user_perms],
        'can_manage_roles': is_admin or 'manage_roles' in [p.codename for p in user_perms],
        'can_view_reports': is_admin or 'view_reports' in [p.codename for p in user_perms],
        'can_manage_settings': is_admin or 'manage_settings' in [p.codename for p in user_perms],
    }
