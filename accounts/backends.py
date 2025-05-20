"""
Custom authentication backends for the accounts app.

This module provides custom authentication backends for handling
role-based access control.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class RoleBasedModelBackend(ModelBackend):
    """
    Custom authentication backend that handles role-based access control.
    
    This backend extends the default ModelBackend to provide additional
    functionality for role-based permissions and authentication.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user with the given username/email and password.
        
        Args:
            request: The current request object
            username: The username or email of the user
            password: The password of the user
            **kwargs: Additional keyword arguments
            
        Returns:
            User: The authenticated user if successful, None otherwise
        """
        if username is None or password is None:
            return None
            
        try:
            # Try to find user by username or email
            user = User.objects.get(
                Q(username__iexact=username) | 
                Q(email__iexact=username)
            )
            
            # Check if the password is valid
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            # Run the default password hasher once to prevent timing attacks
            User().set_password(password)
            
        return None
    
    def has_perm(self, user_obj, perm, obj=None):
        """
        Check if the user has the specified permission.
        
        Args:
            user_obj: The user object
            perm: The permission to check (format: 'app_label.codename')
            obj: The object to check the permission against (optional)
            
        Returns:
            bool: True if the user has the permission, False otherwise
        """
        # Superusers have all permissions
        if user_obj.is_superuser:
            return True
            
        # Check if the user has the permission through their groups
        if hasattr(user_obj, 'profile'):
            return user_obj.profile.has_permission(perm)
            
        return False
    
    def has_module_perms(self, user_obj, app_label):
        """
        Check if the user has any permissions for the given app.
        
        Args:
            user_obj: The user object
            app_label: The app label to check
            
        Returns:
            bool: True if the user has any permissions for the app, False otherwise
        """
        # Superusers have all permissions
        if user_obj.is_superuser:
            return True
            
        # Check if the user has any permissions for the app
        if hasattr(user_obj, 'profile'):
            permissions = user_obj.profile.get_permissions()
            return any(perm.startswith(f'{app_label}.') for perm in permissions)
            
        return False
