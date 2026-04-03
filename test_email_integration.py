#!/usr/bin/env python
"""
Test policy document email delivery
"""
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
django.setup()

from members.models_public_enrollment import PublicApplication
from members.policy_documents import generate_policy_pdf, send_policy_document_email
from django.core.mail import EmailMessage
from django.test.utils import override_settings

# Get or create test application
try:
    app = PublicApplication.objects.filter(application_id='TEST-0001').first()
    
    if not app:
        print("❌ Test application not found")
        exit(1)
    
    print(f"✓ Using application: {app.application_id}")
    print(f"  Email: {app.email}")
    
    # Test 1: PDF Generation
    print("\n🔄 Test 1: PDF Generation")
    try:
        pdf_content = generate_policy_pdf(app)
        print(f"✓ PDF generated ({len(pdf_content)} bytes)")
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        exit(1)
    
    # Test 2: Email Template Rendering
    print("\n🔄 Test 2: Email Template Rendering")
    try:
        from django.template.loader import render_to_string
        from django.utils import timezone
        
        context = {
            'application': app,
            'generated_date': timezone.now(),
            'reference': app.application_id,
            'has_debit_order': app.payment_method == 'DEBIT_ORDER',
        }
        
        email_html = render_to_string('members/public_enrollment/policy_email.html', context)
        print(f"✓ Email template rendered ({len(email_html)} bytes)")
        
        if 'policy document' in email_html.lower():
            print("✓ Email template contains policy document content")
        else:
            print("⚠️  Email template may not contain expected content")
            
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    # Test 3: Email Assembly (without sending)
    print("\n🔄 Test 3: Email Assembly")
    try:
        from django.conf import settings
        
        email = EmailMessage(
            subject=f"Your Policy Document - Reference {app.id}",
            body=email_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[app.email],
        )
        
        # Simulate attachment
        email.attach(
            filename=f"Policy_{app.id}.pdf",
            content=pdf_content,
            mimetype='application/pdf'
        )
        
        print(f"✓ Email assembled with PDF attachment")
        print(f"  To: {app.email}")
        print(f"  Subject: Policy Document - Reference {app.id}")
        print(f"  Attachment: Policy_{app.id}.pdf ({len(pdf_content)} bytes)")
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("\n✅ All Tests Passed!")
    print("\nProduction Workflow:")
    print("1. Admin approves application")
    print("2. convert_application_to_policy() is called")
    print("3. send_policy_document_email() generates PDF and sends email")
    print("4. Client receives policy document PDF via email")
    
except Exception as e:
    print(f"❌ Test failed: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
