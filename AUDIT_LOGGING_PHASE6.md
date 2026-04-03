# Phase 6: Complete Audit Logging Implementation

## Overview

This phase implements comprehensive audit logging across the entire application to provide a complete audit trail of all critical operations. This is essential for:

1. **Security**: Detect and investigate unauthorized access or malicious activity
2. **Compliance**: Meet POPIA (Protection of Personal Information Act) requirements
3. **Accountability**: Track who did what and when
4. **Debugging**: Understand system state changes and troubleshoot issues
5. **Analytics**: Analyze user behavior and operational patterns

## What's Been Implemented

### 1. Core Infrastructure ✅

**Models** (`audit/models.py`):
- `AuditLog`: Tracks all create, update, delete, login, logout, import, export operations
- `DataAccess`: Records access to sensitive personal data fields (POPIA compliance)

**Middleware** (`audit/middleware.py`):
- `AuditContextMiddleware`: Captures request context (user, IP, user agent) for all operations
- Thread-local storage makes request available to signals without passing it everywhere

**Signals** (`audit/signals.py`):
- Auto-logs model create/update/delete for sensitive models
- Logs user login/logout events
- Configurable via `AUDIT_EXCLUDED_MODELS` and `AUDIT_SENSITIVE_MODELS` in settings

### 2. Business Operations Utilities ✅

**Operations Module** (`audit/operations.py`):

```python
# Claim status changes (submitted → approved → paid)
audit_claim_status_change(claim, old_status, new_status, user, reason)

# Payment processing (created, processed, released, rejected)
audit_payment_processing(payment, action, amount, status, user, details)

# Policy changes (premium, coverage, status)
audit_policy_change(policy, field, old_value, new_value, user, reason)

# Member information changes
audit_member_change(member, field, old_value, new_value, user, reason)

# Sensitive data access (ID numbers, bank accounts) - POPIA
audit_sensitive_data_access(instance, fields_accessed, user, reason)

# Bulk operations (imports, exports, batch processing)
audit_bulk_operation(operation_type, object_list, count, user, details)

# Permission/role changes
audit_permission_change(user, permission, action, reason)

# Failed attempts (failed login, unauthorized access)
audit_failed_attempt(object_type, identifier, attempt_type, reason, user)

# Transactional operations with rollback safety
audit_with_transaction(auditable_function, *args, **kwargs)
```

### 3. Admin Interface ✅

**Audit Log Admin** (`audit/admin.py`):
- View all audit logs with user, timestamp, action, IP address
- Filter by action type, date range, user
- Search by username, object representation, IP address
- Clickable links to related objects
- JSON data displayed in formatted table
- Read-only (no modification or addition)
- Only superusers can delete

**Data Access Admin**:
- View all sensitive data access
- Filter by timestamp, user, content type
- Search by username, IP, reason
- POPIA compliance tracking

### 4. Management Commands ✅

**`python manage.py audit_logs`**:

```bash
# View all audit logs from last 7 days
python manage.py audit_logs

# Filter by user
python manage.py audit_logs --user admin

# Filter by action
python manage.py audit_logs --action login

# Filter by IP address
python manage.py audit_logs --ip 192.168.1.100

# Look back 30 days
python manage.py audit_logs --days 30

# View data access logs instead
python manage.py audit_logs --data-access

# Export as CSV
python manage.py audit_logs --csv > audit_export.csv

# Combine filters
python manage.py audit_logs --user admin --action update --days 3
```

## What to Integrate Next (To Complete Phase 6)

### 1. Claims Views - Add Audit Hooks

**Location**: `claims/views.py`

```python
from audit.operations import (
    audit_claim_status_change,
    audit_sensitive_data_access,
    audit_failed_attempt
)

# In claim approval/update views:
old_status = claim.status
claim.status = 'approved'
claim.save()
audit_claim_status_change(claim, old_status, 'approved', request.user, 'Claim approved by admin')

# In review operations that access sensitive data:
audit_sensitive_data_access(
    claim.member,
    fields_accessed=['id_number', 'phone', 'email'],
    user=request.user,
    reason='claim review'
)
```

### 2. Payment Views - Add Audit Hooks

**Location**: `payments/views.py`

```python
from audit.operations import (
    audit_payment_processing,
    audit_sensitive_data_access,
    audit_failed_attempt
)

# In payment processing:
audit_payment_processing(
    payment,
    action='released',
    amount=payment.amount,
    status='paid',
    user=request.user,
    details={'method': 'bank_transfer', 'reference': payment.reference_number}
)

# In payment retry after failure:
if not payment.processed:
    audit_failed_attempt(
        'payment',
        identifier=payment.id,
        attempt_type='processing_failed',
        reason='Bank connection timeout',
        user=request.user
    )
```

### 3. Member Views - Add Audit Hooks

**Location**: `members/views.py`

```python
from audit.operations import (
    audit_member_change,
    audit_sensitive_data_access
)

# Track member status changes:
old_name = member.first_name
member.first_name = new_name
member.save()
audit_member_change(
    member,
    field='first_name',
    old_value=old_name,
    new_value=new_name,
    user=request.user,
    reason='Member profile update'
)

# Track sensitive data updates:
if 'id_number' in request.POST:
    audit_member_change(
        member,
        field='id_number',
        old_value=member.id_number,  # Already encrypted
        new_value=request.POST['id_number'],  # Will be encrypted
        user=request.user,
        reason='ID number update'
    )
```

### 4. Policy Views - Add Audit Hooks

**Location**: `schemes/views.py`

```python
from audit.operations import audit_policy_change

# Track policy changes:
old_premium = policy.premium_amount
policy.premium_amount = new_premium
policy.save()
audit_policy_change(
    policy,
    field='premium_amount',
    old_value=old_premium,
    new_value=new_premium,
    user=request.user,
    reason='Premium adjustment'
)
```

## Configuration Reference

Add to `legacyadmin/settings.py`:

```python
# Audit Logging Configuration
AUDIT_EXCLUDED_MODELS = [
    'audit.AuditLog',           # Don't log audit logs (avoid recursion)
    'audit.DataAccess',         # Don't log data access logs
    'admin.LogEntry',           # Don't log Django admin actions
    'sessions.Session',         # Don't log session changes
]

AUDIT_SENSITIVE_MODELS = [
    'auth.User',                # Track all user changes
    'members.Member',           # Track member info changes
    'members.Policy',           # Track policy changes
    'claims.Claim',             # Track claim status changes
    'payments.Payment',         # Track payment processing
]
```

## Testing Audit Logging

### 1. Manual Testing in Django Shell

```python
from django.contrib.auth.models import User
from audit.models import AuditLog
from audit.operations import audit_claim_status_change

# Create a test user
user = User.objects.get(username='testuser')

# Simulate a claim status change
from claims.models import Claim
claim = Claim.objects.first()
audit_claim_status_change(claim, 'submitted', 'approved', user, 'Test')

# Check that it was logged
logs = AuditLog.objects.filter(user=user).order_by('-timestamp')
print(logs[0])
print(logs[0].data)
```

### 2. View in Admin Interface

1. Go to `/admin/audit/auditlog/`
2. Filter by your test user
3. Verify entries are created with correct timestamps and data

### 3. Command Line Testing

```bash
# View logs for your test user
python manage.py audit_logs --user testuser

# View last 24 hours
python manage.py audit_logs --days 1

# Export for analysis
python manage.py audit_logs --days 7 --csv > audit_report.csv
```

## Security Best Practices

### 1. Retention Policy

Audit logs should be kept for at least:
- 1 year for compliance purposes
- 2-3 years for investigation purposes

```python
# Add to settings.py
AUDIT_LOG_RETENTION_DAYS = 365  # 1 year

# Cleanup script (run monthly):
# python manage.py cleanup_audit_logs
```

### 2. Access Control

- Only administrators can view audit logs
- Only superusers can delete audit logs
- Audit logs are read-only (cannot be modified)
- Track who is viewing audit logs (add audit log to audit log access!)

```python
# In audit admin views
class AuditLogAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False  # Nobody can add
    
    def has_change_permission(self, request, obj=None):
        return False  # Nobody can modify
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete
```

### 3. Immutability

- Audit logs should be immutable and append-only
- Consider moving old logs to read-only archive storage
- Never allow modification of existing logs

### 4. Sensitive Data in Logs

- PII fields are captured as field names, not values
- Encrypted fields (id_number, etc.) are logged as encrypted values
- Bank accounts not logged in transactions, only transaction amounts
- Consider hashing sensitive identifiers in log data

## Integration Checklist

- [ ] Middleware added to settings.py ✅
- [ ] AuditLog and DataAccess models created ✅
- [ ] Signals configured in apps.py ✅
- [ ] Admin interfaces configured (read-only) ✅
- [ ] Management command for log queries ✅
- [ ] Business logic operations utilities created ✅
- [ ] **TODO**: Add audit_claim_status_change() calls to claims/views.py
- [ ] **TODO**: Add audit_payment_processing() calls to payments/views.py
- [ ] **TODO**: Add audit_member_change() calls to members/views.py
- [ ] **TODO**: Add audit_sensitive_data_access() to sensitive operations
- [ ] **TODO**: Create retention policy and cleanup script
- [ ] **TODO**: Document audit log format for compliance
- [ ] **TODO**: Test audit logging end-to-end
- [ ] **TODO**: Set up log archival for long-term storage

## Verifying Audit Logging Works

```bash
# 1. Check middleware is loaded
python manage.py shell
>>> from audit.middleware import get_request_context
>>> print(get_request_context())  # Will be None in shell

# 2. Check auto-logging is working
python manage.py runserver

# 3. In browser:
#    - Log in (check audit log shows login)
#    - Create/update a sensitive model (check audit log shows changes)
#    - View audit logs in admin at /admin/audit/auditlog/

# 4. Test management command
python manage.py audit_logs --limit 5

# 5. Test data access logging
python manage.py audit_logs --data-access
```

## Next Steps

After Phase 6 is complete:

1. **Phase 7**: Create comprehensive test suite
   - Unit tests for multi-tenancy
   - Integration tests for payment workflow
   - Security regression tests

2. **Phase 8**: Performance optimization
   - Add database indexes on frequently queried audit log fields
   - Archive old audit logs to separate table
   - Implement log rotation and cleanup

3. **Phase 9**: Finalize for production
   - Rotate API credentials (BulkSMS, OpenAI)
   - Set up monitoring and alerting
   - Document runbook for operations team
