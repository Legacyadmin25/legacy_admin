"""
Custom User Model for the accounts app.

This module defines a custom User model that extends the default Django User model
to support our role-based access control system.
"""
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model that extends the default Django User model.
    
    This model adds support for role-based access control and additional
    user-related functionality.
    """
    # Add any additional fields here
    phone = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        help_text=_('User\'s phone number (optional).')
    )
    date_of_birth = models.DateField(
        _('date of birth'),
        null=True,
        blank=True,
        help_text=_('User\'s date of birth (optional).')
    )
    
    # Add related_name to avoid clashes with auth.User
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_groups",
        related_query_name="user",
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_permissions",
        related_query_name="user",
    )
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        db_table = 'auth_user'  # Use the same table name as the default User model
        swappable = 'AUTH_USER_MODEL'
    
    def __str__(self):
        """Return the string representation of the user."""
        return self.get_full_name() or self.username
    
    @property
    def is_admin(self):
        """Check if the user is an admin."""
        return self.is_superuser or self.is_staff or self.groups.filter(name__in=['Admin', 'Superuser']).exists()
    
    @property
    def primary_role(self):
        """Get the user's primary role."""
        if self.is_superuser:
            return 'Superuser'
        if self.is_staff:
            return 'Staff'
        if self.groups.exists():
            return self.groups.first().name
        return 'User'
