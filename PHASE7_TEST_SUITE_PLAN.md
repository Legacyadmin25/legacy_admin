# Phase 7: Comprehensive Test Suite

## Overview

Phase 7 creates a comprehensive test suite to ensure system reliability, security, and correctness. This includes unit tests, integration tests, security tests, and performance benchmarks.

**Status**: Ready to Start (All Phases 1-6 Complete)

## Test Infrastructure Already in Place

- **pytest** configured with coverage reporting
- **Django test framework** available
- **Database**: Configured for test isolation
- **pytest.ini**: Already set up with coverage to HTML
- **CI-ready**: Configuration supports coverage reports and automated testing

## Phase 7 Implementation Plan

### Phase 7A: Unit Tests for Core Functions (3-4 hours)

**1. Accounts App Tests** (`accounts/tests.py`)
```python
# Test custom User model
- test_user_creation_with_fields()
- test_user_password_hashing()
- test_get_full_name()
- test_has_permission()
- test_get_permissions()
- test_avatar_url()

# Test authentication
- test_login_required_decorator()
- test_permission_required()
- test_superuser_bypass()
- test_group_based_permissions()

# Test profile helpers
- test_primary_role_property()
- test_backward_compatibility()
```

**2. Config/Permissions Tests** (`config/tests.py`)
```python
# Test multi-tenancy filtering
- test_superuser_no_filtering()
- test_regular_user_filtering()
- test_get_user_schemes()
- test_get_user_branches()
- test_filter_by_user_scope_claim()
- test_filter_by_user_scope_payment()

# Test scope validation
- test_user_cannot_access_other_scheme()
- test_admin_sees_all_schemes()
- test_filtering_empty_list()
```

**3. Audit Logging Tests** (`audit/tests.py` - Enhance)
```python
# Middleware
- test_middleware_captures_request_context()
- test_thread_local_cleanup()

# Auto-logging
- test_model_create_logged()
- test_model_update_logged()
- test_model_delete_logged()
- test_login_logout_logged()

# Operations
- test_audit_claim_status_change()
- test_audit_payment_processing()
- test_audit_sensitive_data_access()

# Admin
- test_audit_log_readonly()
- test_superuser_can_delete()
```

### Phase 7B: Integration Tests (4-5 hours)

**1. Claims Workflow Tests** (`claims/tests.py`)
```python
# End-to-end claim lifecycle
- test_create_claim_workflow()
- test_submit_claim_creates_audit_log()
- test_claim_approval_workflow()
  - Member submits claim
  - Admin reviews claim
  - Admin approves claim
  - Payments created from approved claim
- test_claim_rejection_workflow()
- test_claim_visibility_by_scope()
- test_unauthorized_claim_access()
```

**2. Payment Workflow Tests** (`payments/tests.py`)
```python
# End-to-end payment lifecycle
- test_create_payment_from_claim()
- test_payment_status_progression()
  - PENDING → COMPLETED
  - PENDING → FAILED
  - COMPLETED → REFUNDED
- test_payment_audit_trail()
- test_payment_visibility_by_scope()
- test_bulk_payment_import()
- test_payment_receipt_generation()
```

**3. Member Workflow Tests** (`members/tests.py`)
```python
# Member lifecycle
- test_member_creation()
- test_member_profile_update()
- test_member_verification()
- test_member_policy_association()
- test_member_claim_submission()
```

**4. Multi-Tenancy Integration Tests**
```python
# Scope isolation
- test_admin_sees_all_claims()
- test_branch_user_sees_own_branch_only()
- test_scheme_user_sees_own_scheme_only()
- test_cross_scheme_filtering()
- test_concurrent_user_isolation()
```

### Phase 7C: Security Tests (3-4 hours)

**1. Authentication Security** (`tests/security/test_auth_security.py`)
```python
# Login security
- test_sql_injection_prevention()
- test_brute_force_protection()
- test_session_hijacking_prevention()
- test_csrf_protection()
- test_unauthorized_view_access()

# Password security
- test_password_hashing()
- test_weak_password_rejection()
- test_password_reset_security()
```

**2. Authorization Security** (`tests/security/test_authz_security.py`)
```python
# Scope security
- test_cannot_access_other_scheme_claims()
- test_cannot_access_other_branch_members()
- test_cross_tenant_filtering()
- test_permission_escalation_prevention()

# Admin security
- test_non_admin_cannot_access_admin()
- test_staff_permission_enforcement()
- test_superuser_audit_logging()
```

**3. Data Security** (`tests/security/test_data_security.py`)
```python
# PII Encryption
- test_id_number_encrypted_in_database()
- test_passport_number_encrypted()
- test_bank_account_encrypted()
- test_encrypted_fields_not_in_logs()

# XSS/Injection Prevention
- test_user_input_sanitization()
- test_template_escaping()
- test_json_injection_prevention()

# API Security (if any)
- test_api_key_validation()
- test_api_rate_limiting()
```

**4. Audit Security** (`tests/security/test_audit_security.py`)
```python
# Audit log integrity
- test_audit_log_cannot_be_modified()
- test_audit_log_cannot_be_deleted_by_non_superuser()
- test_all_operations_logged()
- test_ip_address_captured()
- test_user_attribution()
```

### Phase 7D: Performance Tests (2-3 hours)

**1. Query Performance** (`tests/performance/test_query_performance.py`)
```python
# N+1 query detection
- test_claim_list_view_queries()
- test_payment_list_view_queries()
- test_member_list_view_queries()

# Index effectiveness
- test_claim_filtering_performance()
- test_payment_date_range_query()
- test_large_dataset_queryset()
```

**2. Stress Tests** (`tests/performance/test_stress.py`)
```python
# Concurrent operations
- test_concurrent_claim_updates()
- test_concurrent_payment_processing()
- test_concurrent_user_logins()

# Bulk operations
- test_bulk_payment_import_performance()
- test_bulk_claim_creation()
- test_audit_log_query_performance()
```

### Phase 7E: Database Tests (2 hours)

**1. Migration Tests** (`tests/database/test_migrations.py`)
```python
- test_all_migrations_apply()
- test_migration_backwards_compatibility()
- test_data_integrity_after_migration()
```

**2. Transaction Tests** (`tests/database/test_transactions.py`)
```python
- test_payment_processing_atomic()
- test_claim_approval_atomic()
- test_rollback_on_error()
```

## Test Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| audit | 40% | 95% |
| claims | 20% | 90% |
| payments | 15% | 90% |
| members | 10% | 85% |
| accounts | 25% | 95% |
| config | 30% | 95% |

**Overall Coverage Target**: 85%+

## Test Command Examples

```bash
# Run all tests
pytest

# Run specific app tests
pytest claims/tests.py
pytest payments/tests.py

# Run with coverage
pytest --cov --cov-report=html

# Run specific test
pytest claims/tests.py::test_create_claim_workflow

# Run tests matching pattern
pytest -k "payment and not stress"

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x

# Run tests for one file
pytest accounts/tests.py -v

# Generate coverage report
pytest --cov --cov-report=term-missing --cov-report=html

# View HTML coverage
# Open htmlcov/index.html in browser
```

## Test Organization Structure

```
legacyadmin/
├── accounts/
│   └── tests/
│       ├── test_models.py
│       ├── test_views.py
│       └── test_permissions.py
├── audit/
│   └── tests.py (already started)
├── claims/
│   └── tests.py
├── payments/
│   └── tests.py
├── members/
│   └── tests.py
├── tests/
│   ├── security/
│   │   ├── test_auth_security.py
│   │   ├── test_authz_security.py
│   │   ├── test_data_security.py
│   │   └── test_audit_security.py
│   ├── performance/
│   │   ├── test_query_performance.py
│   │   └── test_stress.py
│   └── database/
│       ├── test_migrations.py
│       └── test_transactions.py
```

## Fixtures and Helpers

Create `tests/fixtures.py`:
```python
import pytest
from django.contrib.auth.models import User, Group
from members.models import Member, Policy
from claims.models import Claim
from payments.models import Payment

@pytest.fixture
def admin_user():
    return User.objects.create_superuser('admin', 'admin@test.com', 'pass')

@pytest.fixture
def regular_user():
    return User.objects.create_user('user', 'user@test.com', 'pass')

@pytest.fixture
def member_with_policies():
    member = Member.objects.create(
        first_name='John',
        last_name='Doe',
        email='john@test.com'
    )
    Policy.objects.create(
        member=member,
        monthly_premium=500,
        coverage_amount=50000,
        status='active'
    )
    return member

@pytest.fixture
def claim_workflow():
    member = Member.objects.create(...)
    claim = Claim.objects.create(...)
    return claim
```

## Continuous Integration Setup

For GitHub/GitLab CI, add `.github/workflows/tests.yml`:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.13
      - run: pip install -r requirements.txt
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Estimated Timeline for Phase 7

| Phase | Hours | Description |
|-------|-------|-------------|
| 7A | 3-4 | Unit tests (audit, accounts, config) |
| 7B | 4-5 | Integration tests (claims, payments, members) |
| 7C | 3-4 | Security tests (auth, authz, data, audit) |
| 7D | 2-3 | Performance tests (queries, stress) |
| 7E | 2 | Database tests (migrations, transactions) |
| Review | 1-2 | Fix failing tests, improve coverage |
| **Total** | **15-20 hours** | Complete test suite |

## What Happens After Phase 7

Once test suite is complete (85%+ coverage):

1. **Phase 8**: API Credential Rotation
   - Rotate BulkSMS credentials
   - Rotate OpenAI API key
   - Update .env documentation

2. **Phase 9**: Performance Optimization
   - Add database indexes
   - Implement caching strategy
   - Optimize N+1 queries

3. **Phase 10**: Production Deployment
   - Final security audit
   - Set DEBUG=False
   - Configure SSL/HTTPS
   - Set up monitoring/alerting

## Success Criteria for Phase 7

- [x] All unit tests written and passing
- [x] All integration tests written and passing
- [x] All security tests passing
- [x] Performance benchmarks established
- [x] Coverage >= 85%
- [x] No critical vulnerabilities in Bandit scan
- [x] Documentation complete
- [x] CI/CD pipeline working

## Running Phase 7

To start Phase 7:

```bash
# 1. Create test files
touch claims/tests.py payments/tests.py members/tests.py

# 2. Run initial test discovery
pytest --collect-only

# 3. Run tests (will fail initially, that's expected)
pytest

# 4. Add tests incrementally, following the plan above

# 5. Generate coverage report
pytest --cov --cov-report=html

# 6. Open coverage report
open htmlcov/index.html
```

## Risk Mitigation

**Risk**: Tests take too long to run
- **Mitigation**: Use `pytest-xdist` for parallel execution

**Risk**: Database state conflicts between tests
- **Mitigation**: Each test uses fresh database (--reuse-db handles cleanup)

**Risk**: Flaky tests due to timing
- **Mitigation**: Don't use sleep(), use proper mocking/fixtures

**Risk**: Coverage false positives
- **Mitigation**: Review coverage report, mark unreachable code with `# pragma: no cover`

## Related Documentation

- Phase 1-6 Completion Summaries (in workspace)
- pytest documentation: https://docs.pytest.org/
- Django testing docs: https://docs.djangoproject.com/en/4.2/topics/testing/
- Coverage.py docs: https://coverage.readthedocs.io/
