"""
Admin interface configuration for the accounts app.

This module configures the Django admin interface for the User, Profile, Role,
and UserRole models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group as AuthGroup

# Import models using helper functions to avoid circular imports
from .models import get_profile_model, get_role_models

# Get the custom User model
User = get_user_model()
Profile = get_profile_model()
Role, UserRole = get_role_models()


class ProfileInline(admin.StackedInline):
    """Inline admin for the Profile model."""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = [
        'phone', 'address', 'city', 'state', 'postal_code', 'country',
        'date_of_birth', 'profile_picture', 'bio', 'is_verified', 'is_active'
    ]


class UserRoleInline(admin.TabularInline):
    """Inline admin for the UserRole model."""
    model = UserRole
    extra = 1
    verbose_name = _('Role Assignment')
    verbose_name_plural = _('Role Assignments')
    raw_id_fields = ('user',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with profile and role inlines."""
    inlines = (ProfileInline, UserRoleInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email', 'date_of_birth')
        }),
        (_('Contact info'), {
            'fields': ('phone',)
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin interface for the Profile model."""
    list_display = ('user', 'full_name', 'email', 'phone', 'is_verified', 'is_active')
    list_filter = ('is_verified', 'is_active', 'country', 'state')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'phone')
    list_select_related = ('user',)
    
    def full_name(self, obj):
        """Return the user's full name."""
        return obj.user.get_full_name()
    full_name.short_description = 'Name'
    full_name.admin_order_field = 'user__first_name'
    
    def email(self, obj):
        """Return the user's email."""
        return obj.user.email
    email.short_description = 'Email'
    email.admin_order_field = 'user__email'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for the Role model."""
    list_display = ('name', 'description', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    filter_horizontal = ()
    
    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin interface for the UserRole model."""
    list_display = ('user', 'role', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'role', 'created_at')
    search_fields = ('user__username', 'user__email', 'role__name')
    list_select_related = ('user', 'role')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


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
