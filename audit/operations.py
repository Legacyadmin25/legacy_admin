"""
Business logic audit helpers for logging important application operations.
Provides utilities for logging domain-specific events (claims, payments, policies).
"""
from django.db import transaction
from django.utils import timezone
from audit.models import AuditLog, DataAccess
from audit.middleware import get_request_context


def audit_claim_status_change(claim, old_status, new_status, user=None, reason=None):
    """
    Log a changes in claim status (submitted, approved, rejected, paid).
    
    Args:
        claim: Claim instance
        old_status: Previous status
        new_status: New status
        user: User making the change (optional)
        reason: Reason for the change (optional)
    """
    request = get_request_context()
    changes = {
        'field': 'status',
        'old_value': old_status,
        'new_value': new_status,
        'reason': reason,
        'timestamp': timezone.now().isoformat()
    }
    return AuditLog.log_update(claim, user=user, request=request, changes=changes)


def audit_payment_processing(payment, action, amount, status, user=None, details=None):
    """
    Log payment processing operations (created, processed, released, rejected).
    
    Args:
        payment: Payment instance
        action: Type of action ('created', 'processed', 'released', 'rejected')
        amount: Payment amount
        status: Payment status after operation
        user: User performing the action
        details: Additional details (reference number, method, etc.)
    """
    request = get_request_context()
    changes = {
        'action': action,
        'amount': str(amount),
        'status': status,
        'details': details,
        'timestamp': timezone.now().isoformat()
    }
    return AuditLog.log_update(payment, user=user, request=request, changes=changes)


def audit_policy_change(policy, field, old_value, new_value, user=None, reason=None):
    """
    Log changes to policy details (premium, coverage, status, etc.).
    
    Args:
        policy: Policy instance
        field: Field name that changed
        old_value: Previous value
        new_value: New value
        user: User making the change
        reason: Reason for the change
    """
    request = get_request_context()
    changes = {
        'field': field,
        'old_value': str(old_value),
        'new_value': str(new_value),
        'reason': reason,
        'timestamp': timezone.now().isoformat()
    }
    return AuditLog.log_update(policy, user=user, request=request, changes=changes)


def audit_member_change(member, field, old_value, new_value, user=None, reason=None):
    """
    Log changes to member information (personal details, verification, etc.).
    
    Args:
        member: Member instance
        field: Field name that changed
        old_value: Previous value
        new_value: New value
        user: User making the change
        reason: Reason for the change
    """
    request = get_request_context()
    changes = {
        'field': field,
        'old_value': str(old_value),
        'new_value': str(new_value),
        'reason': reason,
        'timestamp': timezone.now().isoformat()
    }
    return AuditLog.log_update(member, user=user, request=request, changes=changes)


def audit_sensitive_data_access(instance, fields_accessed, user=None, reason=None):
    """
    Log access to sensitive personal data (ID numbers, bank accounts, contact info).
    Required for POPIA compliance.
    
    Args:
        instance: Model instance containing sensitive data
        fields_accessed: List of field names accessed (e.g., ['id_number', 'bank_account'])
        user: User accessing the data
        reason: Reason for accessing the data (e.g., 'claim review', 'verification')
    """
    request = get_request_context()
    return DataAccess.log_access(instance, fields_accessed, user=user, request=request, reason=reason)


def audit_bulk_operation(operation_type, object_list, count, user=None, details=None):
    """
    Log bulk operations (batch processing, imports, exports).
    
    Args:
        operation_type: Type of operation ('import', 'export', 'batch_process')
        object_list: List of affected objects or content type name
        count: Number of objects affected
        user: User performing the operation
        details: Additional details about the operation
    """
    request = get_request_context()
    data = {
        'operation_type': operation_type,
        'count': count,
        'object_list': object_list,
        'details': details,
        'timestamp': timezone.now().isoformat()
    }
    
    if operation_type == 'import':
        return AuditLog.log_import(object_list, user=user, request=request, details=data)
    elif operation_type == 'export':
        return AuditLog.log_export(object_list, user=user, request=request, details=data)
    else:
        # Generic log for other batch operations
        return AuditLog.objects.create(
            user=user,
            username=user.username if user else 'system',
            action='update',
            ip_address=AuditLog._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            data=data
        )


def audit_permission_change(user, permission, action, reason=None):
    """
    Log permission/role changes for compliance and security audit trail.
    
    Args:
        user: User whose permissions changed
        permission: Permission/Role object or name
        action: 'grant' or 'revoke'
        reason: Reason for the change
    """
    request = get_request_context()
    changes = {
        'action': action,
        'permission': str(permission),
        'reason': reason,
        'timestamp': timezone.now().isoformat()
    }
    return AuditLog.log_update(user, request=request, changes=changes)


def audit_failed_attempt(object_type, identifier, attempt_type, reason=None, user=None):
    """
    Log failed attempts (failed login, unauthorized access, failed verification).
    
    Args:
        object_type: Type of object ('login', 'payment', 'verification', etc.)
        identifier: What was being accessed (username, policy_id, etc.)
        attempt_type: Type of failed attempt
        reason: Reason for failure
        user: User attempting the action (optional)
    """
    request = get_request_context()
    data = {
        'object_type': object_type,
        'identifier': identifier,
        'attempt_type': attempt_type,
        'reason': reason,
        'timestamp': timezone.now().isoformat()
    }
    
    return AuditLog.objects.create(
        user=user,
        username=user.username if user else identifier,
        action='view',  # Using 'view' for unauthorized attempts
        ip_address=AuditLog._get_client_ip(request) if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        data=data
    )


@transaction.atomic
def audit_with_transaction(auditable_function, *args, **kwargs):
    """
    Execute a function within an atomic transaction and log all changes.
    Ensures that if anything fails, the entire operation and audit log are rolled back.
    
    Args:
        auditable_function: The function to execute with automatic auditing
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        The function's return value
    """
    try:
        result = auditable_function(*args, **kwargs)
        return result
    except Exception as e:
        # Log the failed operation
        request = get_request_context()
        AuditLog.objects.create(
            user=kwargs.get('user'),
            username=kwargs.get('user').username if kwargs.get('user') else 'system',
            action='update',
            ip_address=AuditLog._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            data={'error': str(e), 'function': auditable_function.__name__}
        )
        raise
