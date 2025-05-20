# Role-Based Permissions Checklist

This document provides a comprehensive overview of which roles can perform specific actions within the Legacy Guard system. It serves as a reference for QA testing, user training, and compliance auditing.

## Permission Matrix

| Feature | Superuser | Admin | BranchOwner | SchemeManager | Finance Officer | Claims Officer | Agent | Compliance Auditor |
|---------|:---------:|:-----:|:-----------:|:-------------:|:---------------:|:--------------:|:-----:|:-----------------:|
| Create Policy | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Approve Claims | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Import Payments | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| View Reports | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Access AI Insights | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Access All Members | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Manage Users | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Send Reminders | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Export Data | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| View Audit Logs | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| System Settings | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Process Payments | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Generate Receipts | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| View Own Policies | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Client Referrals | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |

## Role Descriptions

### Superuser
- Has unrestricted access to all system features
- Can manage all users, roles, and permissions
- Can access system configuration and settings

### Administrator
- Can manage users and their permissions
- Has access to all operational features
- Can view and generate all reports

### BranchOwner
- Can manage schemes within their branch
- Can view all policies within their branch
- Can process payments and approve claims for their branch

### SchemeManager
- Can manage agents within their scheme
- Can view all policies within their scheme
- Can process payments and approve claims for their scheme

### Finance Officer
- Specializes in payment processing and financial operations
- Can import payments and generate receipts
- Can view financial reports and export data

### Claims Officer
- Specializes in claims processing
- Can approve or reject claims
- Can view claim-related documents

### Agent
- Can create new policies
- Can refer clients
- Can only view their own policies

### Compliance Auditor
- Has read-only access to most system data
- Can view audit logs and reports
- Cannot modify any data or approve actions

## Permission Enforcement

Permissions are enforced at multiple levels:

1. **UI Level**: Interface elements are conditionally rendered based on user roles
2. **View Level**: Django view mixins validate permissions before processing requests
3. **API Level**: API endpoints validate permissions before allowing access
4. **Model Level**: Django model permissions restrict database operations

## Testing Guidelines

When testing role-based access:

1. Log in as each role type
2. Attempt to access each feature in the matrix
3. Verify that access is granted or denied according to the matrix
4. Check that UI elements are appropriately shown or hidden
5. Verify that direct URL access is properly restricted

## Compliance Notes

This permission structure complies with:

- Separation of duties requirements
- Financial services regulatory requirements
- Data protection principles (need-to-know basis)
- Audit trail requirements for all sensitive operations
