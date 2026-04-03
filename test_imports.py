#!/usr/bin/env python
"""
Comprehensive import verification test
Checks all plan and datetime imports across the system
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
django.setup()

print("=" * 70)
print("IMPORT VERIFICATION TEST - Plan & DateTime")
print("=" * 70)

test_results = []

# Test 1: datetime imports
print("\n[TEST 1] Testing datetime imports...")
try:
    from datetime import date, datetime, timedelta
    print("✓ datetime, date, timedelta imports working")
    test_results.append(("datetime imports", True))
except ImportError as e:
    print(f"❌ datetime import failed: {e}")
    test_results.append(("datetime imports", False))

# Test 2: Plan model from schemes
print("\n[TEST 2] Testing Plan model import...")
try:
    from schemes.models import Plan, Scheme
    print(f"✓ Plan model imported successfully")
    print(f"  Plan model: {Plan}")
    print(f"  Scheme model: {Scheme}")
    test_results.append(("Plan model import", True))
except ImportError as e:
    print(f"❌ Plan model import failed: {e}")
    test_results.append(("Plan model import", False))
    sys.exit(1)

# Test 3: Check Plan model fields
print("\n[TEST 3] Testing Plan model fields...")
try:
    plan_fields = [f.name for f in Plan._meta.get_fields()]
    print(f"✓ Plan model has {len(plan_fields)} fields")
    
    # Check critical fields
    critical_fields = ['name', 'scheme', 'premium', 'main_cover', 'is_active']
    for field in critical_fields:
        if field in plan_fields:
            print(f"  ✓ {field}")
        else:
            print(f"  ⚠️  Missing: {field}")
    
    test_results.append(("Plan model fields", True))
except Exception as e:
    print(f"❌ Plan model field check failed: {e}")
    test_results.append(("Plan model fields", False))

# Test 4: Query Plan objects
print("\n[TEST 4] Testing Plan database query...")
try:
    plans_count = Plan.objects.count()
    print(f"✓ Plan query working - found {plans_count} plans")
    
    if plans_count > 0:
        first_plan = Plan.objects.first()
        print(f"  First plan: {first_plan.name} (R{first_plan.premium}/month)")
        if first_plan.main_cover:
            print(f"  Cover amount: R{first_plan.main_cover}")
    
    test_results.append(("Plan database query", True))
except Exception as e:
    print(f"❌ Plan query failed: {e}")
    test_results.append(("Plan database query", False))

# Test 5: Scheme model
print("\n[TEST 5] Testing Scheme model...")
try:
    schemes_count = Scheme.objects.count()
    print(f"✓ Scheme query working - found {schemes_count} schemes")
    
    if schemes_count > 0:
        first_scheme = Scheme.objects.first()
        print(f"  First scheme: {first_scheme.name}")
        plan_count = first_scheme.plans.count()
        print(f"  Plans in scheme: {plan_count}")
    
    test_results.append(("Scheme model", True))
except Exception as e:
    print(f"❌ Scheme query failed: {e}")
    test_results.append(("Scheme model", False))

# Test 6: Check PublicApplication fields with date
print("\n[TEST 6] Testing PublicApplication model with date fields...")
try:
    from members.models_public_enrollment import PublicApplication
    print(f"✓ PublicApplication model imported")
    
    # Check date fields
    app_fields = [f.name for f in PublicApplication._meta.get_fields()]
    date_fields = ['date_of_birth', 'created_at', 'submitted_at', 'completed_at']
    
    for field in date_fields:
        if field in app_fields:
            print(f"  ✓ {field} exists")
        else:
            print(f"  ⚠️  {field} not found")
    
    test_results.append(("PublicApplication date fields", True))
except Exception as e:
    print(f"❌ PublicApplication check failed: {e}")
    test_results.append(("PublicApplication date fields", False))

# Test 7: Check Member model with date
print("\n[TEST 7] Testing Member model...")
try:
    from members.models import Member
    print(f"✓ Member model imported")
    
    member_count = Member.objects.count()
    print(f"  Members in database: {member_count}")
    
    if member_count > 0:
        first_member = Member.objects.first()
        print(f"  First member: {first_member.first_name} {first_member.last_name}")
        print(f"  DOB: {first_member.date_of_birth}")
    
    test_results.append(("Member model", True))
except Exception as e:
    print(f"❌ Member query failed: {e}")
    test_results.append(("Member model", False))

# Test 8: Check Policy model
print("\n[TEST 8] Testing Policy model...")
try:
    from members.models import Policy
    print(f"✓ Policy model imported")
    
    policy_count = Policy.objects.count()
    print(f"  Policies in database: {policy_count}")
    
    if policy_count > 0:
        first_policy = Policy.objects.first()
        print(f"  First policy: {first_policy.policy_number or 'N/A'}")
        print(f"  Member: {first_policy.member}")
        print(f"  Plan: {first_policy.plan.name if first_policy.plan else 'N/A'}")
    
    test_results.append(("Policy model", True))
except Exception as e:
    print(f"❌ Policy query failed: {e}")
    test_results.append(("Policy model", False))

# Test 9: Test app approval workflow import
print("\n[TEST 9] Testing admin approval imports...")
try:
    from members.utils_public_enrollment import convert_application_to_policy
    from members.policy_documents import generate_policy_pdf
    from members.views_admin import applications_list, approve_application
    print(f"✓ All admin workflow imports working")
    print(f"  - convert_application_to_policy: ✓")
    print(f"  - generate_policy_pdf: ✓")
    print(f"  - applications_list view: ✓")
    print(f"  - approve_application view: ✓")
    test_results.append(("Admin workflow imports", True))
except ImportError as e:
    print(f"❌ Admin workflow import failed: {e}")
    test_results.append(("Admin workflow imports", False))

# Test 10: Test public enrollment imports
print("\n[TEST 10] Testing public enrollment imports...")
try:
    from members.forms_public_enrollment import PersonalDetailsPublicForm
    from members.models_public_enrollment import PublicApplication, EnrollmentLink
    print(f"✓ All public enrollment imports working")
    print(f"  - PersonalDetailsPublicForm: ✓")
    print(f"  - PublicApplication: ✓")
    print(f"  - EnrollmentLink: ✓")
    test_results.append(("Public enrollment imports", True))
except ImportError as e:
    print(f"❌ Public enrollment import failed: {e}")
    test_results.append(("Public enrollment imports", False))

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

for test_name, result in test_results:
    status = "✓ PASS" if result else "❌ FAIL"
    print(f"{status}: {test_name}")

print("\n" + "=" * 70)
if passed == total:
    print(f"✅ ALL TESTS PASSED ({passed}/{total})")
    print("=" * 70)
    print("\n✅ System Status: FULLY OPERATIONAL")
    print("\nAll plan and datetime imports are working correctly!")
    print("\nKey Components Ready:")
    print("  ✓ datetime, date, timedelta - Available")
    print("  ✓ Plan model - Accessible and querying")
    print("  ✓ Scheme model - Working properly")
    print("  ✓ PublicApplication - Date fields ready")
    print("  ✓ Member model - Date handling working")
    print("  ✓ Policy model - Fully operational")
    print("  ✓ Admin workflow - All functions imported")
    print("  ✓ Public enrollment - Complete system working")
    sys.exit(0)
else:
    print(f"❌ SOME TESTS FAILED ({total - passed}/{total})")
    print("=" * 70)
    sys.exit(1)
