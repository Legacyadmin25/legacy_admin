"""
Profile model for the accounts app.

This module defines the Profile model that extends the custom User model
with additional user profile information and role-based functionality.
"""
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    """
    Profile model that extends the custom User model.
    
    This model stores additional user information and provides methods
    for role-based access control.
    """
    # User reference
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Profile fields
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional fields
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    # Role-related fields
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}'s Profile"
    
    @property
    def full_name(self):
        """Get the user's full name."""
        return self.user.get_full_name()
    
    @property
    def email(self):
        """Get the user's email."""
        return self.user.email
    
    @property
    def primary_role(self):
        """Get the user's primary role."""
        if self.user.is_superuser:
            return 'Superuser'
        if self.user.is_staff:
            return 'Staff'
        if self.user.groups.exists():
            return self.user.groups.first().name
        return 'User'
    
    def has_role(self, role_name):
        """Check if the user has the specified role."""
        return self.user.groups.filter(name=role_name).exists()
    
    def has_any_role(self, *role_names):
        """Check if the user has any of the specified roles."""
        return self.user.groups.filter(name__in=role_names).exists()
    
    def has_all_roles(self, *role_names):
        """Check if the user has all of the specified roles."""
        return all(self.has_role(role_name) for role_name in role_names)
    
    def has_permission(self, permission):
        """
        Check if user has a specific permission.
        
        Args:
            permission (str): The permission code to check
            
        Returns:
            bool: True if the user has the permission, False otherwise
        """
        from config.permissions import has_permission
        return has_permission(self.user, permission)
    
    def get_permissions(self):
        """
        Get all permissions for this user.
        
        Returns:
            set: A set of permission strings the user has
        """
        from config.permissions import get_user_permissions
        return get_user_permissions(self.user)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to create a profile for each new user.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal to save the profile when the user is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
