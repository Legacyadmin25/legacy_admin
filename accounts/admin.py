"""
Admin interface configuration for the accounts app.

This module configures the Django admin interface for the User model.
Role-based permissions are now handled through Django's built-in Group model.
Profile fields have been consolidated into the User model.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.utils.translation import gettext_lazy as _

# Import models
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with profile fields directly on User model."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'date_of_birth')
        }),
        (_('Address'), {
            'fields': ('address', 'city', 'state', 'postal_code', 'country'),
            'classes': ('collapse',)
        }),
        (_('Profile'), {
            'fields': ('profile_picture', 'bio', 'is_verified'),
            'classes': ('collapse',)
        }),
        (_('Branch & Scheme Assignments'), {
            'fields': ('branch', 'assigned_schemes'),
            'description': 'Assign users to branches (for BranchOwners) or schemes (for SchemeManagers) to enable data isolation.'
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'last_activity')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    
    filter_horizontal = ('assigned_schemes',)


# Unregister the default Group admin and register our custom one
admin.site.unregister(AuthGroup)

@admin.register(AuthGroup)
class GroupAdmin(admin.ModelAdmin):
    """Custom Group admin with improved display and filtering."""
    list_display = ('name', 'user_count')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    
    def user_count(self, obj):
        return obj.user_set.count()
    user_count.short_description = 'Users'
