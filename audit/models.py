import json
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class AuditLog(models.Model):
    """
    Audit log for tracking all changes to critical data in the system.
    """
    # Action types
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_EXPORT = 'export'
    ACTION_IMPORT = 'import'
    ACTION_VIEW = 'view'
    
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_EXPORT, 'Export'),
        (ACTION_IMPORT, 'Import'),
        (ACTION_VIEW, 'View'),
    ]
    
    # Fields
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150, blank=True)  # Stored separately in case user is deleted
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Target object (what was changed)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(max_length=255, blank=True)  # String representation of the object
    
    # Change details
    data = models.JSONField(null=True, blank=True)  # JSON representation of the changes
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        if self.content_object:
            return f"{self.timestamp} - {self.get_action_display()} {self.object_repr} by {self.username or 'system'}"
        return f"{self.timestamp} - {self.get_action_display()} by {self.username or 'system'}"
    
    @classmethod
    def log_create(cls, instance, user=None, request=None):
        """Log the creation of an object"""
        return cls._log(instance, cls.ACTION_CREATE, user, request)
    
    @classmethod
    def log_update(cls, instance, user=None, request=None, changes=None):
        """Log the update of an object"""
        return cls._log(instance, cls.ACTION_UPDATE, user, request, changes)
    
    @classmethod
    def log_delete(cls, instance, user=None, request=None):
        """Log the deletion of an object"""
        return cls._log(instance, cls.ACTION_DELETE, user, request)
    
    @classmethod
    def log_login(cls, user, request=None):
        """Log a user login"""
        return cls._log(None, cls.ACTION_LOGIN, user, request)
    
    @classmethod
    def log_logout(cls, user, request=None):
        """Log a user logout"""
        return cls._log(None, cls.ACTION_LOGOUT, user, request)
    
    @classmethod
    def log_export(cls, content_type, user=None, request=None, details=None):
        """Log a data export"""
        return cls._log(None, cls.ACTION_EXPORT, user, request, data={
            'content_type': content_type,
            'details': details
        })
    
    @classmethod
    def log_import(cls, content_type, user=None, request=None, details=None):
        """Log a data import"""
        return cls._log(None, cls.ACTION_IMPORT, user, request, data={
            'content_type': content_type,
            'details': details
        })
    
    @classmethod
    def log_view(cls, instance, user=None, request=None):
        """Log a sensitive data view"""
        return cls._log(instance, cls.ACTION_VIEW, user, request)
    
    @classmethod
    def _log(cls, instance, action, user=None, request=None, changes=None):
        """Internal method to create a log entry"""
        # Prepare data for the log entry
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Get content type and object ID if instance is provided
        content_type = None
        object_id = None
        object_repr = ''
        
        if instance:
            content_type = ContentType.objects.get_for_model(instance)
            object_id = str(instance.pk)
            object_repr = str(instance)
        
        # Get username
        username = user.username if user else 'system'
        
        # Create the log entry
        log_entry = cls.objects.create(
            user=user,
            username=username,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            content_type=content_type,
            object_id=object_id,
            object_repr=object_repr,
            data=changes
        )
        
        return log_entry
    
    @staticmethod
    def _get_client_ip(request):
        """Get the client's real IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the list (client's real IP)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DataAccess(models.Model):
    """
    Records sensitive data access for POPIA compliance.
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # What data was accessed
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=50)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Access details
    fields_accessed = models.JSONField(default=list)
    access_reason = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Data Access Log'
        verbose_name_plural = 'Data Access Logs'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.username} accessed {self.content_type}"
    
    @classmethod
    def log_access(cls, instance, fields, user=None, request=None, reason=None):
        """Log access to sensitive data"""
        # Get content type
        content_type = ContentType.objects.get_for_model(instance)
        
        # Get IP address
        ip_address = None
        if request:
            ip_address = cls._get_client_ip(request)
        
        # Get username
        username = user.username if user else 'system'
        
        # Create the log entry
        log_entry = cls.objects.create(
            user=user,
            username=username,
            ip_address=ip_address,
            content_type=content_type,
            object_id=str(instance.pk),
            fields_accessed=fields,
            access_reason=reason or ''
        )
        
        return log_entry
    
    @staticmethod
    def _get_client_ip(request):
        """Get the client's real IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the list (client's real IP)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
