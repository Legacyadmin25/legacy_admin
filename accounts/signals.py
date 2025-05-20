"""
Signal handlers for the accounts app.

This module contains signal handlers for user-related events,
such as user creation and profile updates.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile for each new user.
    
    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the user's profile when the user is saved.
    
    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved
        **kwargs: Additional keyword arguments
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(pre_save, sender=User)
def set_initial_user_permissions(sender, instance, **kwargs):
    """
    Set initial permissions for new users.
    
    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved
        **kwargs: Additional keyword arguments
    """
    if not instance.pk:
        # This is a new user, set default permissions
        instance.is_active = True  # Activate user by default
        
        # If no groups are assigned and this isn't a superuser, assign to Agent group
        if not instance.groups.exists() and not instance.is_superuser:
            from django.contrib.auth.models import Group
            try:
                agent_group = Group.objects.get(name='Agent')
                instance.save()  # Save first to get a PK
                instance.groups.add(agent_group)
            except Group.DoesNotExist:
                pass
