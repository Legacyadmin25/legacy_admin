"""
Context processors for the accounts app.

This module provides context processors that add useful variables to the template context.
"""

from config.permissions import (
    can_view_all_members_report,
    can_view_amendments_report,
    can_view_payment_allocation_report,
    get_primary_group,
    get_user_permissions,
    has_permission,
    is_read_only_user,
    user_has_role,
)


def user_permissions(request):
    """
    Add the current user's permissions to the template context.
    
    This makes it easy to check permissions in templates without having to
    pass them from every view.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}
        
    user = request.user
    
    primary_role = get_primary_group(user)
    user_perms = get_user_permissions(user)
    is_admin = user.is_superuser or user_has_role(user, 'Administrator', 'Superuser')
    
    return {
        'user_permissions': user_perms,
        'user_primary_role': primary_role,
        'is_admin': is_admin,
        'is_read_only': is_read_only_user(user),
        'can_manage_users': has_permission(user, 'manage_users'),
        'can_manage_roles': is_admin,
        'can_view_reports': has_permission(user, 'view_reports'),
        'can_manage_settings': has_permission(user, 'manage_settings'),
        'can_view_all_members_report': can_view_all_members_report(user),
        'can_view_payment_admin_report': can_view_payment_allocation_report(user, 'admin'),
        'can_view_payment_scheme_report': can_view_payment_allocation_report(user, 'scheme'),
        'can_view_amendments_report': can_view_amendments_report(user),
    }
