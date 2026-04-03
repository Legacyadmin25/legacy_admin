from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.conf import settings

from audit.models import AuditLog
from audit.middleware import get_request_context

# List of models to exclude from automatic audit logging
EXCLUDED_MODELS = getattr(settings, 'AUDIT_EXCLUDED_MODELS', [
    # Don't log changes to the AuditLog itself to avoid recursion
    'audit.AuditLog',
    'audit.DataAccess',
    # Django session and admin log models
    'admin.LogEntry',
    'sessions.Session',
])

# List of sensitive models that should have all actions logged
SENSITIVE_MODELS = getattr(settings, 'AUDIT_SENSITIVE_MODELS', [
    # Models containing personally identifiable information
    'auth.User',
    'members.Member',
    'members.Policy',
    'members.Claim',
    'members.BankAccount',
])


@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    """Log user login events"""
    # Request context is already passed here by Django signals
    AuditLog.log_login(user, request)


@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    """Log user logout events"""
    # Request context is already passed here by Django signals
    AuditLog.log_logout(user, request)


@receiver(post_save)
def post_save_callback(sender, instance, created, **kwargs):
    """Log model instance creation and updates"""
    # Get the model name in app_label.model_name format
    model_name = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    # Skip excluded models
    if model_name in EXCLUDED_MODELS:
        return
    
    # Skip non-sensitive models that are not explicitly configured for auditing
    # unless they are in the sensitive models list
    if not getattr(sender, 'audit_log', False) and model_name not in SENSITIVE_MODELS:
        return
    
    # Get the current request context
    request = get_request_context()
    
    # For sensitive models or models with audit_log=True, log the change
    if created:
        # New instance created
        AuditLog.log_create(instance, request=request)
    else:
        # Existing instance updated
        AuditLog.log_update(instance, request=request)


@receiver(post_delete)
def post_delete_callback(sender, instance, **kwargs):
    """Log model instance deletions"""
    # Get the model name in app_label.model_name format
    model_name = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    # Skip excluded models
    if model_name in EXCLUDED_MODELS:
        return
    
    # Skip non-sensitive models that are not explicitly configured for auditing
    if not getattr(sender, 'audit_log', False) and model_name not in SENSITIVE_MODELS:
        return
    
    # Get the current request context
    request = get_request_context()
    
    # Log the deletion
    AuditLog.log_delete(instance, request=request)
