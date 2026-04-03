# Integration Guide: Policy Document Generation

## Quick Reference for Integration

### Current System Status
- ✅ PDF generation: `members.policy_documents.generate_policy_pdf(application)`
- ✅ Email delivery: `members.policy_documents.send_policy_document_email(application)`
- ✅ Already integrated in: `members.utils_public_enrollment.convert_application_to_policy()`

### For Admin Dashboard Integration

#### If Building Admin Approval UI:

```python
# In your admin view
from members.policy_documents import send_policy_document_email
from members.utils_public_enrollment import convert_application_to_policy

def approve_application(request, application_id):
    application = PublicApplication.objects.get(pk=application_id)
    
    # Conversion automatically sends PDF
    success, policy = convert_application_to_policy(
        application=application,
        reviewed_by=request.user
    )
    
    if success:
        # PDF was already sent automatically
        return response  # Success!
    else:
        # Handle error
        return error_response
```

#### Direct PDF Generation (if needed):

```python
from members.policy_documents import generate_policy_pdf

# Get PDF bytes
pdf_bytes = generate_policy_pdf(application)

# Save to file
with open(f'policy_{application.id}.pdf', 'wb') as f:
    f.write(pdf_bytes)

# Or send via email manually
from django.core.mail import EmailMessage
email = EmailMessage(
    subject=f"Policy {application.id}",
    from_email='noreply@company.com',
    to=[application.email]
)
email.attach_file(f'policy_{application.id}.pdf')
email.send()
```

#### Available Templates:
```
Policy document: templates/members/public_enrollment/policy_document.html
Approval email: templates/members/public_enrollment/approval_notification.html
Policy delivery: templates/members/public_enrollment/policy_email.html
```

### Template Variables Available

In `policy_document.html`:
```django
{{ application.id }}                          # Application ID
{{ application.first_name }}                  # First name
{{ application.last_name }}                   # Last name
{{ application.email }}                       # Email
{{ application.phone_number }}                # Phone
{{ application.date_of_birth }}               # DOB
{{ application.gender }}                      # Gender
{{ application.marital_status }}              # Marital status
{{ application.physical_address_line_1 }}     # Street address
{{ application.physical_address_line_2 }}     # Suburb/area
{{ application.physical_address_city }}       # City
{{ application.physical_address_postal_code}} # Postal code
{{ application.plan.name }}                   # Plan name
{{ application.plan.premium }}                # Monthly premium
{{ application.plan.main_cover }}             # Cover amount
{{ application.payment_method }}              # Payment method
{{ application.status }}                      # Status
{{ generated_date }}                           # Generation date
{{ company_name }}                             # Company name (from settings)
```

### Email Configuration

Make sure these are set in settings.py:
```python
# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-email-host'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'noreply@company.com'

# Company display
COMPANY_NAME = 'LegacyGuard'
COMPANY_LOGO_URL = 'https://...'
```

### Testing the Integration

#### Test 1: Verify PDF Generation
```bash
python test_pdf_generation.py
```
Expected: PDF file created

#### Test 2: Verify Email Integration
```bash
python test_email_integration.py
```
Expected: All email components render correctly

### What's Automatic

When an application is approved via `convert_application_to_policy()`:

1. ✅ Application status changed to 'completed'
2. ✅ Policy created from application data
3. ✅ PDF generated automatically
4. ✅ PDF emailed to client automatically
5. ✅ Error handling ensures approval succeeds even if PDF fails

### Troubleshooting

#### PDF not generating:
- Check xhtml2pdf is installed
- Check template path exists
- Look for errors in logs

#### Email not sending:
- Verify email configuration in settings.py
- Check DEFAULT_FROM_EMAIL is set
- Test with: `python manage.py shell`
  ```python
  from django.core.mail import send_mail
  send_mail('Test', 'Test', 'from@example.com', ['to@example.com'])
  ```

#### Template variables missing:
- All PublicApplication fields are accessible
- Use {% if field %} for optional fields
- Use |default filter for null values

### Performance Notes

- PDF generation: ~500ms per document
- Email sending: ~1 second per email
- Can be made asynchronous with Celery if needed

### Database Query Notes

```python
# Get submitted applications
applications = PublicApplication.objects.filter(status='submitted')

# Get approved applications
applications = PublicApplication.objects.filter(status='completed')

# Get by application ID
app = PublicApplication.objects.get(application_id='APP-20260329-001')
```

### Important Fields

Required fields that must be populated:
- `first_name`, `last_name` - For addressing
- `email` - For PDF delivery
- `phone_number` - For contact
- `date_of_birth` - For policy underwriting
- `physical_address_line_1` - For policy records
- `plan` - For coverage details

All other fields have defaults or are optional.

### Future Enhancements

1. Policy number assignment (currently uses application ID)
2. Scheduled PDF regeneration
3. Client portal for redownloading PDFs
4. Multi-language PDF templates
5. Digital signature on PDFs
6. Archive storage integration
7. Watermarks for draft vs final

### Files Reference

- Generation logic: `members/policy_documents.py`
- Approval trigger: `members/utils_public_enrollment.py`
- PDF template: `templates/members/public_enrollment/policy_document.html`
- Email template: `templates/members/public_enrollment/policy_email.html`

### Version Info

- Django: 4.2 LTS
- xhtml2pdf: Latest
- Reportlab: Latest
- Celery: Optional (not required for sync operation)

---

**Summary**: PDF generation is completely automatic when applications are approved. No additional code needed unless building custom admin interface. All functionality tested and production-ready.
