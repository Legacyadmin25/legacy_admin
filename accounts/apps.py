"""
App configuration for the accounts app.

This module contains the AppConfig class for the accounts app,
which configures the application and its settings.
"""
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_initial_roles(sender, **kwargs):
    """Create initial user roles and permissions."""
    # Import here to avoid AppRegistryNotReady error
    from django.contrib.auth.models import Group
    
    # Create groups if they don't exist
    groups = [
        'Internal Admin',
        'Superuser',
        'Administrator',
        'BranchOwner',
        'SchemeManager',
        'Finance Officer',
        'Claims Officer',
        'Agent',
        'Compliance Auditor',
    ]
    
    for group_name in groups:
        Group.objects.get_or_create(name=group_name)


class AccountsConfig(AppConfig):
    """Configuration for the accounts app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'User Accounts'
    
    def ready(self):
        """Run when the app is ready."""
        # Import signals to register them
        from . import signals  # noqa: F401
        
        # Connect the create_initial_roles function to the post_migrate signal
        post_migrate.connect(create_initial_roles, sender=self)
        
        # Import models here to ensure they're registered
        from .models import User, Profile, Role, UserRole  # noqa: F401
