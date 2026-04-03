"""
Models package for the accounts app.

This package contains all the models for the accounts application.
"""
from django.apps import apps
from django.conf import settings

# Import models directly
from .user import User
# Profile model has been consolidated into User model
# Role and UserRole have been removed - using Django Groups instead

# This is needed for Django to recognize the models
__all__ = ['User']

def get_user_model():
    """Helper function to get the User model when needed."""
    return User

def get_profile_model():
    """Helper function to get the Profile model when needed."""
    return Profile
