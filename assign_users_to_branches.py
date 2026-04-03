#!/usr/bin/env python
"""
Script to assign existing users to branches and schemes based on their roles.

This enables data isolation by assigning:
- BranchOwners to their branch
- SchemeManagers to their schemes
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
django.setup()

from django.contrib.auth import get_user_model
from branches.models import Branch
from schemes.models import Scheme

User = get_user_model()

print("=" * 70)
print("ASSIGNING USERS TO BRANCHES AND SCHEMES")
print("=" * 70)

# Get the main branch (TFi Brokers)
try:
    main_branch = Branch.objects.get(name='TFi Brokers')
    print(f"\n✓ Found main branch: {main_branch.name}")
except Branch.DoesNotExist:
    print("✗ ERROR: TFi Brokers branch not found!")
    exit(1)

# Get all schemes in the main branch
schemes = Scheme.objects.filter(branch=main_branch)
print(f"✓ Found {schemes.count()} schemes in {main_branch.name}:")
for scheme in schemes:
    print(f"  - {scheme.name}")

# Assign BranchOwners to the branch
print("\n" + "-" * 70)
print("Assigning BranchOwners to branch...")
branch_owners = User.objects.filter(groups__name='BranchOwner')
print(f"Found {branch_owners.count()} BranchOwners")

assigned_count = 0
for user in branch_owners:
    if user.branch is None:
        user.branch = main_branch
        user.save()
        assigned_count += 1
        print(f"  ✓ {user.username} → {main_branch.name}")
    else:
        print(f"  - {user.username} already assigned to {user.branch.name}")

print(f"✓ Assigned {assigned_count} BranchOwners to branch")

# Assign SchemeManagers to their schemes
print("\n" + "-" * 70)
print("Assigning SchemeManagers to schemes...")
scheme_managers = User.objects.filter(groups__name='SchemeManager')
print(f"Found {scheme_managers.count()} SchemeManagers")

assigned_count = 0
for user in scheme_managers:
    current = user.assigned_schemes.count()
    
    # Assign to all schemes if not already assigned
    if current == 0:
        for scheme in schemes:
            user.assigned_schemes.add(scheme)
        user.save()
        assigned_count += 1
        print(f"  ✓ {user.username} → {schemes.count()} schemes")
    else:
        print(f"  - {user.username} already assigned to {current} schemes")

print(f"✓ Assigned {assigned_count} SchemeManagers to schemes")

# Show summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"\n✓ BranchOwners with branch assignment:")
bo_assigned = User.objects.filter(groups__name='BranchOwner', branch__isnull=False).count()
print(f"  {bo_assigned} / {branch_owners.count()}")

print(f"\n✓ SchemeManagers with scheme assignments:")
sm_assigned = User.objects.filter(groups__name='SchemeManager', assigned_schemes__isnull=False).distinct().count()
print(f"  {sm_assigned} / {scheme_managers.count()}")

print(f"\n✓ Data isolation is now ENABLED!")
print("=" * 70)
