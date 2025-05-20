"""
Models package for the accounts app.

This package contains all the models for the accounts application.
"""
from django.apps import apps
from django.conf import settings

# Import models directly
from .user import User
from .profile import Profile
from .role import Role, UserRole

# This is needed for Django to recognize the models
__all__ = ['User', 'Profile', 'Role', 'UserRole']

def get_user_model():
    """Helper function to get the User model when needed."""
    return User

def get_profile_model():
    """Helper function to get the Profile model when needed."""
    return Profile

def get_role_models():
    """Helper function to get the Role and UserRole models when needed."""
    return Role, UserRole
