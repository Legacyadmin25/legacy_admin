"""
Custom User Model for the accounts app.

This module defines a custom User model that extends the default Django User model
to support our role-based access control system.
"""
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.db.models import Q
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
    
    # Extended profile fields (previously in Profile model)
    address = models.TextField(
        _('address'),
        blank=True,
        help_text=_('User\'s street address.')
    )
    city = models.CharField(
        _('city'),
        max_length=100,
        blank=True,
        help_text=_('User\'s city.')
    )
    state = models.CharField(
        _('state'),
        max_length=100,
        blank=True,
        help_text=_('User\'s state/province.')
    )
    postal_code = models.CharField(
        _('postal code'),
        max_length=20,
        blank=True,
        help_text=_('User\'s postal code.')
    )
    country = models.CharField(
        _('country'),
        max_length=100,
        blank=True,
        help_text=_('User\'s country.')
    )
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profile_pics/',
        blank=True,
        null=True,
        help_text=_('User\'s profile picture.')
    )
    bio = models.TextField(
        _('bio'),
        blank=True,
        help_text=_('User\'s biography.')
    )
    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        help_text=_('Designates whether this user email has been verified.')
    )
    last_activity = models.DateTimeField(
        _('last activity'),
        auto_now=True,
        help_text=_('Date and time of the user\'s last activity.')
    )
    
    # Branch assignment (for data isolation)
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='assigned_users',
        help_text=_('The branch this user is assigned to (for branch-level access control).')
    )
    
    # Scheme assignments (for SchemeManagers)
    assigned_schemes = models.ManyToManyField(
        'schemes.Scheme',
        blank=True,
        related_name='scheme_managers',
        help_text=_('Schemes this user can manage (for SchemeManagers).')
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
    
    def has_permission(self, perm):
        """Check if user has a specific permission through groups."""
        if self.is_superuser:
            return True
        # Check direct permissions
        if self.user_permissions.filter(codename=perm).exists():
            return True
        # Check group permissions
        return self.groups.filter(permissions__codename=perm).exists()
    
    def get_permissions(self):
        """Get all permissions for this user through groups."""
        from django.contrib.auth.models import Permission
        if self.is_superuser:
            return Permission.objects.all()
        permissions = Permission.objects.filter(
            Q(user=self) | Q(group__user=self)
        ).distinct()
        return permissions
    
    def get_avatar_url(self):
        """Get the URL for the user's profile picture."""
        if self.profile_picture:
            return self.profile_picture.url
        return '/static/img/default-avatar.png'
    
    @property
    def profile(self):
        """
        Compatibility property to access user as profile.
        Returns self for backward compatibility with code expecting user.profile.
        """
        return self
