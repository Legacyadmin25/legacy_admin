"""
Template tags for role-based template rendering.

This module provides template tags to check user roles and permissions
in templates without cluttering the view logic.
"""
from django import template
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe

register = template.Library()
User = get_user_model()

@register.filter
def has_role(user, role_name):
    """Check if a user has a specific role."""
    if not user or not user.is_authenticated:
        return False
        
    # Superusers have all roles
    if user.is_superuser:
        return True
        
    # Check if user has the specified role
    return user.groups.filter(name=role_name).exists()

@register.filter
def has_any_role(user, role_names):
    """Check if a user has any of the specified roles."""
    if not user or not user.is_authenticated:
        return False
        
    # Superusers have all roles
    if user.is_superuser:
        return True
        
    # Split the comma-separated role names
    roles = [r.strip() for r in role_names.split(',')]
    return user.groups.filter(name__in=roles).exists()

@register.filter
def has_permission(user, permission_code):
    """Check if a user has a specific permission."""
    if not user or not user.is_authenticated:
        return False
        
    # Superusers have all permissions
    if user.is_superuser:
        return True
        
    # Check if user has the permission through their profile
    if hasattr(user, 'profile'):
        return user.profile.has_permission(permission_code)
        
    return False

@register.simple_tag(takes_context=True)
def if_has_permission(context, permission_code, true_text='', false_text=''):
    """
    Return true_text if user has the permission, otherwise false_text.
    
    Usage:
        {% if_has_permission 'manage_users' 'Show this' 'Show that' %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return false_text
        
    user = request.user
    
    # Check permission
    if has_permission(user, permission_code):
        return true_text
    return false_text

@register.simple_tag(takes_context=True)
def role_based_content(context, roles, content):
    """
    Render content only if the user has one of the specified roles.
    
    Usage:
        {% role_based_content 'Administrator,BranchOwner' %}
            This content is only visible to Administrators and Branch Owners.
        {% end_role_based_content %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return ''
        
    user = request.user
    
    # Superusers see all content
    if user.is_superuser:
        return content
        
    # Check if user has any of the specified roles
    if has_any_role(user, roles):
        return content
        
    return ''

@register.inclusion_tag('accounts/includes/role_badge.html')
def role_badge(user):
    """
    Render a badge showing the user's primary role.
    
    Usage:
        {% load role_tags %}
        {% role_badge request.user %}
    """
    if not user or not user.is_authenticated:
        return {'role_name': 'Guest', 'role_class': 'secondary'}
        
    # Get the primary role
    if hasattr(user, 'profile'):
        role_name = user.profile.primary_role or 'User'
    elif user.is_superuser:
        role_name = 'Superuser'
    elif user.is_staff:
        role_name = 'Staff'
    else:
        role_name = 'User'
    
    # Map roles to CSS classes
    role_classes = {
        'Superuser': 'danger',
        'Administrator': 'primary',
        'BranchOwner': 'info',
        'SchemeManager': 'success',
        'Finance Officer': 'warning',
        'Claims Officer': 'warning',
        'Agent': 'secondary',
        'Compliance Auditor': 'dark',
    }
    
    return {
        'role_name': role_name,
        'role_class': role_classes.get(role_name, 'secondary')
    }
