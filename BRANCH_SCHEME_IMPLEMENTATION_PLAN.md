# Branch & Scheme Access Control Implementation Plan

## Current Status

✅ **What's Working:**
- Schemes ARE properly linked to Branches (ForeignKey relationship)
- Branch reverse relationship working (branch.schemes.all())
- Role-based permission system defined (8 roles)
- View-level permission checks in place

❌ **What's Missing:**
- User model has NO branch field
- BranchOwners cannot be assigned to specific branches
- No way to assign SchemeManagers to specific schemes
- All users with a role can see all data (no isolation)

## Implementation Required

### Phase 1: Database Schema Updates

#### 1.1 Add User-Branch Relationship
```python
# In accounts/models/user.py - add to User model:
branch = models.ForeignKey(
    'branches.Branch',
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name='assigned_users',
    help_text='The branch this user is assigned to (for BranchOwners)'
)
```

#### 1.2 Add User-Scheme Relationships  
```python
# In accounts/models/user.py - add to User model:
assigned_schemes = models.ManyToManyField(
    'schemes.Scheme',
    blank=True,
    related_name='assigned_users',
    help_text='Schemes this user can manage (for SchemeManagers)'
)
```

#### 1.3 Migration
- Create migration: `python manage.py makemigrations accounts`
- Apply migration: `python manage.py migrate`

### Phase 2: Update Views with Data Filtering

#### 2.1 BranchOwner Views
Update `branches/views.py` to filter by user.branch:
```python
if user.groups.filter(name='BranchOwner').exists():
    if user.branch:
        branches = Branch.objects.filter(id=user.branch.id)
    else:
        # BranchOwner with no assigned branch - show nothing
        branches = Branch.objects.none()
```

#### 2.2 Scheme Views
Update views showing schemes to filter by assigned_schemes:
```python
if user.groups.filter(name='SchemeManager').exists():
    schemes = Scheme.objects.filter(assigned_users=user)
elif user.groups.filter(name='BranchOwner').exists():
    schemes = Scheme.objects.filter(branch=user.branch)
```

#### 2.3 Member/Policy Views
Update to respect user branch/scheme:
```python
if user.groups.filter(name='BranchOwner').exists():
    members = Member.objects.filter(policies__plan__scheme__branch=user.branch)
elif user.groups.filter(name='SchemeManager').exists():
    members = Member.objects.filter(policies__plan__scheme__assigned_users=user)
```

### Phase 3: Update Admin Interface

#### 3.1 User Admin
Update `accounts/admin.py` with new fields:
```python
fieldsets = (
    # ... existing fieldsets ...
    (_('Branch & Scheme Assignment'), {
        'fields': ('branch', 'assigned_schemes'),
    }),
)
filter_horizontal = ('assigned_schemes',)
```

#### 3.2 Branch Admin
Show assigned users inline:
```python
class UserInline(admin.TabularInline):
    model = User
    fields = ('username', 'email', 'is_staff')
    extra = 0
```

### Phase 4: Update Existing Data

#### 4.1 User Assignment Rules
- Find all BranchOwners → assign to TFi Brokers branch
- Find all SchemeManagers → assign to their scheme
- Superusers: leave blank (access everything)
- Admins: leave blank (access everything)

### Phase 5: Update Forms

#### 5.1 User Creation Form
Add branch and assigned_schemes fields:
```python
class UserCreationForm(forms.ModelForm):
    class Meta:
        fields = ['username', 'email', '...', 'branch', 'assigned_schemes']
```

### Phase 6: Update Permission Checks (Optional Enhancement)

Create helper functions in `config/permissions.py`:
```python
def can_view_branch(user, branch):
    """Check if user can view a specific branch."""
    if user.is_superuser:
        return True
    if user.groups.filter(name__in=['Internal Admin', 'Administrator']).exists():
        return True
    if user.groups.filter(name='BranchOwner').exists():
        return user.branch_id == branch.id
    return False

def can_view_scheme(user, scheme):
    """Check if user can view a specific scheme."""
    if user.is_superuser:
        return True
    if user.groups.filter(name__in=['Internal Admin', 'Administrator']).exists():
        return True
    if user.groups.filter(name='SchemeManager').exists():
        return user.assigned_schemes.filter(id=scheme.id).exists()
    if user.groups.filter(name='BranchOwner').exists():
        return scheme.branch_id == user.branch_id
    return False
```

## Implementation Checklist

- [ ] **Task 1**: Update User model with branch FK and assigned_schemes ManyToMany
- [ ] **Task 2**: Create and apply migrations
- [ ] **Task 3**: Update branches/views.py to filter by user.branch
- [ ] **Task 4**: Update schemes views to filter by assigned_schemes or branch
- [ ] **Task 5**: Update member/policy views with data filtering
- [ ] **Task 6**: Update admin.py for UserAdmin fieldsets
- [ ] **Task 7**: Create admin inline for showing assigned users
- [ ] **Task 8**: Assign existing users to branches/schemes
- [ ] **Task 9**: Update user creation form
- [ ] **Task 10**: Add helper functions to config/permissions.py
- [ ] **Task 11**: Update templates to show filtered data
- [ ] **Task 12**: Create new test to verify data isolation
- [ ] **Task 13**: Test each role with their assigned branch/scheme

## Impact Assessment

**High Priority**: Critical for production compliance and data isolation
**Effort**: Medium (2-4 hours)
**Risk**: Low (schema additive, no breaking changes)
**Database**: Safe (backward compatible - nullable fields)
**Testing**: Automated test + manual per-role testing required

## Files to Modify/Create

1. `accounts/models/user.py` - Add fields
2. `accounts/migrations/XXXX_*.py` - New migration
3. `branches/views.py` - Filter by user.branch
4. `schemes/views.py` - Filter by assigned_schemes
5. `members/views.py` - Filter by branch/scheme  
6. `accounts/admin.py` - New admin fieldsets
7. `accounts/forms.py` - Update UserCreationForm
8. `config/permissions.py` - Helper functions
9. `test_data_isolation.py` - New test file

## Timeline

**Step 1** (5 min): Update User model + migration
**Step 2** (20 min): Update all views with filtering
**Step 3** (10 min): Update admin interface
**Step 4** (10 min): Update forms
**Step 5** (5 min): Add helper functions
**Step 6** (20 min): Manual testing per role
**Step 7** (10 min): Create automated test
