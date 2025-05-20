"""
Role and UserRole models for the accounts app.

This module defines the Role and UserRole models that are used for
role-based access control in the application.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Role(models.Model):
    """
    Role model for defining user roles and permissions.
    
    This model extends Django's built-in Group model to provide
    additional role-based functionality.
    """
    name = models.CharField(
        _('name'),
        max_length=150,
        unique=True,
        help_text=_('The name of the role.')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('A description of the role and its permissions.')
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this role is active.')
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        help_text=_('The date and time when the role was created.')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('The date and time when the role was last updated.')
    )

    class Meta:
        verbose_name = _('role')
        verbose_name_plural = _('roles')
        ordering = ['name']

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    Model for assigning roles to users.
    
    This model creates a many-to-many relationship between users and roles,
    allowing users to have multiple roles with different scopes.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('user'),
        help_text=_('The user who is assigned the role.')
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('role'),
        help_text=_('The role being assigned to the user.')
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this role assignment is active.')
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        help_text=_('The date and time when the role was assigned.')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('The date and time when the role assignment was last updated.')
    )

    class Meta:
        verbose_name = _('user role')
        verbose_name_plural = _('user roles')
        unique_together = ('user', 'role')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"
