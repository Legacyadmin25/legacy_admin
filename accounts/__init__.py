"""
Accounts Application

This package contains the accounts app which handles user authentication,
authorization, and profile management for the Legacy Admin system.
"""

# This is intentionally left empty to avoid circular imports
# All model imports should be done inside the app's models/__init__.py

# Set default app config for Django
default_app_config = 'accounts.apps.AccountsConfig'

# Don't expose any models at the package level to prevent circular imports
__all__ = []