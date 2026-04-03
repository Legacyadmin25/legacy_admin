#!/usr/bin/env python
"""
Test PDF generation functionality
"""
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
django.setup()

from members.models_public_enrollment import PublicApplication, EnrollmentLink
from members.policy_documents import generate_policy_pdf, send_policy_document_email
from schemes.models import Scheme, Plan
from django.contrib.auth import get_user_model

User = get_user_model()

# Get or create test data
try:
    # Get first application if exists
    app = PublicApplication.objects.first()
    
    if not app:
        print("⚠️  No applications found, creating test application...")
        
        # Get or create scheme and plan
        scheme = Scheme.objects.first()
        if not scheme:
            print("❌ No schemes found. Please create a scheme first")
            exit(1)
        
        plan = Plan.objects.filter(scheme=scheme).first()
        if not plan:
            print("❌ No plans found for scheme. Please create a plan first")
            exit(1)
        
        # Create test application
        app = PublicApplication.objects.create(
            application_id=f"TEST-{PublicApplication.objects.count() + 1:04d}",
            title="Mr",
            first_name="John",
            last_name="Test",
            email="john@example.com",
            phone_number="0123456789",
            date_of_birth=date(1990, 5, 15),
            gender="Male",
            marital_status="Single",
            physical_address_line_1="123 Test Street",
            physical_address_line_2="Test Area",
            physical_address_city="Johannesburg",
            physical_address_postal_code="2000",
            scheme=scheme,
            plan=plan,
            payment_method="DEBIT_ORDER",
            status="submitted"
        )
        print(f"✓ Created test application: {app.application_id}")
    
    print(f"✓ Using application: {app.application_id}")
    print(f"  Patient: {app.first_name} {app.last_name}")
    print(f"  Status: {app.status}")
    
    # Test PDF generation
    print("\n🔄 Testing PDF generation...")
    try:
        pdf_content = generate_policy_pdf(app)
        print(f"✓ PDF generated successfully ({len(pdf_content)} bytes)")
        
        # Save to file for inspection
        with open('generated_policy.pdf', 'wb') as f:
            f.write(pdf_content)
        print("✓ PDF saved to generated_policy.pdf")
        
    except Exception as e:
        print(f"❌ PDF generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("\n✅ PDF Generation Test Passed!")
    print("\nNext steps:")
    print("1. Approve an application via admin to trigger PDF email")
    print("2. Check that PDF is generated and emailed to applicant")
    
except Exception as e:
    print(f"❌ Test failed: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
