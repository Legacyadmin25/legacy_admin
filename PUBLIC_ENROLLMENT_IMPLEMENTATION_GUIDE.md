# Public Enrollment System - Implementation Guide

## Overview

This module implements a two-track policy enrollment system:
1. **Internal Track**: Agents/staff logged into the system (existing)
2. **Public Track**: Self-service clients via secure shared links (NEW)

---

## Key Features Implemented

### 1. **Secure Token-Based Links**
- Agents generate unique tokens for client enrollment
- Format: `/apply/{token}/`
- Can have expiry dates
- Tracked for analytics (times used, last used date)

### 2. **Multi-Step Public Enrollment**
6-step wizard flow:
1. Personal Details (name, ID/passport, contact)
2. Address Information
3. Plan Selection + Payment Method
4. Payment Details (if debit order)
5. Conditional Questions (smart Q&A based on answers)
6. POPIA Consent + Terms & Conditions

### 3. **Smart Conditional Questions**
- Questions stored in `EnrollmentQuestionBank`
- Support for conditional logic: "Show Q if answer to Q1 = X"
- Question types: text, number, email, phone, date, choice, yes/no, checkbox
- Saves full response journey in `ApplicationAnswer`

### 4. **OTP Verification**
- Sent at END of enrollment (after all questions + consent)
- 6-digit code, 15-minute expiry
- 3 attempts before lockout
- Can resend up to 3 times
- Tracks IP address & user agent

### 5. **POPIA Compliance**
- Tracks all consent types separately
- Documents version control (T&C version, privacy policy version)
- IP address + user agent captured
- Full audit trail

### 6. **Application Review Workflow**
- Applications stored in same DB but separate model
- Visible to scheme/branch managers
- Dashboard for reviewing submitted applications
- Approve/Reject with notes
- Approved applications convert to actual Policy + Member

---

## Database Models

### `EnrollmentLink`
```
- token (unique)
- scheme (FK)
- branch (FK)
- agent (FK, optional)
- is_active (boolean)
- expires_at (optional)
- times_used (tracking)
- created_by (user)
```

### `PublicApplication`
```
- application_id (APP-20260328-001)
- Personal data (first_name, email, phone, etc.)
- Identification (ID number encrypted, passport encrypted)
- Address fields
- scheme (FK), plan (FK)
- payment_method + bank details (encrypted if debit order)
- status (draft, submitted, approved, rejected, completed)
- converted_policy (FK if approved + converted)
- converted_member (FK if approved + converted)
```

### `ApplicationAnswer`
```
- application (FK)
- question_key (e.g., 'spouse_coverage')
- question_text (full question)
- answer (response)
- answer_type (text, choice, etc.)
```

### `OTPVerification`
```
- application (OneToOne)
- phone_number
- otp_code (6 digits)
- status (pending, verified, expired, failed)
- verification_attempts, max_attempts
- expires_at, resend_count
```

### `POPIAConsent`
```
- application (FK)
- consent_type (data_processing, marketing_sms, etc.)
- consented (boolean)
- terms_version, privacy_version
- ip_address, user_agent
- accepted_at
```

### `EnrollmentQuestionBank`
```
- scheme (FK)
- question_key (unique per scheme)
- question_text, question_order
- question_type (text, choice, yes/no, etc.)
- options (JSON for multi-choice)
- conditional_on (if logic)
- conditional_value (equals this)
- is_required, is_active
```

---

## API Endpoints

### Public Enrollment Routes
```
/apply/{token}/                          # Entry point
/apply/step1/personal/                   # Personal details
/apply/step2/address/                    # Address
/apply/step3/plan/                       # Plan + payment method
/apply/step4/payment/                    # Bank details (conditional)
/apply/step5/questions/                  # Conditional questions
/apply/step6/consent/                    # POPIA consent
/apply/otp/verify/                       # OTP entry
/apply/otp/resend/                       # Resend OTP (AJAX)
/apply/success/{app_id}/                 # Success page
```

### Admin Routes (to be created)
```
/admin/applications/                     # Dashboard
/admin/applications/{id}/review/         # Review application
/admin/applications/{id}/approve/        # Approve
/admin/applications/{id}/reject/         # Reject
```

---

## How It Works

### Client Workflow

**1. Agent generates link**
```bash
python manage.py create_enrollment_link --scheme=1 --branch=1 --agent=5 --expires=7
```
Output: `/apply/abc123xyz/`

**2. Share link with client**
- Via SMS
- Via email
- As QR code

**3. Client accesses link** → Validation → Start enrollment

**4. Complete 6-step wizard**
- Auto-validates ID numbers (Luhn check)
- Shows conditional questions based on responses
- Shows applicable plans by age
- Collects bank details if debit order selected

**5. Review & Confirm POPIA consent**

**6. Enter OTP** sent to phone number

**7. Application submitted**
- Application status → "submitted"
- Branch/Scheme manager reviews
- Email sent to applicant with reference number

**8. Admin approves application**
- Application status → "approved"
- System converts to actual Policy + Member
- Member receives policy number + documents
- Application → "completed"

---

## Setup Instructions

### 1. Add to Django Settings

```python
# settings.py

INSTALLED_APPS = [
    # ... existing apps
    'members',  # Already installed
]

# Add to main urls.py
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('apply/', include('members.urls_public_enrollment')),  # Public enrollment
    path('', include('members.urls')),  # Existing admin routes
]
```

### 2. Create Models (Migrations)

```bash
python manage.py makemigrations members
python manage.py migrate members
```

### 3. Create Sample Questions (Management Command - Optional)

```python
# Create seed data
from members.models_public_enrollment import EnrollmentQuestionBank
from schemes.models import Scheme

scheme = Scheme.objects.get(id=1)

# Question 1: Include spouse?
EnrollmentQuestionBank.objects.create(
    scheme=scheme,
    question_key='spouse_coverage',
    question_text='Do you want to include your spouse in the policy?',
    question_type='yes_no',
    question_order=1,
    is_required=True
)

# Question 2: Spouse ID (conditional)
EnrollmentQuestionBank.objects.create(
    scheme=scheme,
    question_key='spouse_id_number',
    question_text='Please enter your spouse ID number',
    question_type='text',
    question_order=2,
    conditional_on='spouse_coverage',
    conditional_value='Yes',
    is_required=True
)

# Question 3: Number of children
EnrollmentQuestionBank.objects.create(
    scheme=scheme,
    question_key='children_count',
    question_text='Do you want to include children?',
    question_type='choice',
    options=['No', 'Yes - up to 2', 'Yes - up to 4'],
    question_order=3,
    is_required=True
)
```

### 4. Generate Enrollment Links

**Via CLI:**
```bash
python manage.py create_enrollment_link \
    --scheme=1 \
    --branch=1 \
    --agent=5 \
    --expires=30 \
    --count=10 \
    --user=1
```

**Output:**
```
✓ Link 1: abc123xyz...
✓ Link 2: def456uvw...
✓ Link 3: ghi789rst...

✅ Created 10 enrollment link(s)
Scheme: Chegutu Funeral Scheme
Branch: Harare Branch
Agent: John Smith
Expires: 2026-04-28 12:00

📱 Share these links with clients:
https://yoursite.com/apply/abc123xyz/
https://yoursite.com/apply/def456uvw/
...
```

---

## Conversion to Policy (Admin Process)

### 1. Browse Submitted Applications
Admin dashboard shows:
- New submissions
- Submitted date
- Client name
- Application reference
- Status

### 2. Review Application
- View all answers to questions
- Check POPIA consents
- Review payment method & bank details
- See OTP verification status

### 3. Approve or Reject
**If Approve:**
- Application converted to Policy + Member
- New Member created (if not exists)
- Policy linked to Member
- Client receives confirmation email with policy #
- Application marked "completed"

**If Reject:**
- Add rejection reason
- Client receives rejection email
- Application marked "rejected"

### 4. Utility Functions
```python
from members.utils_public_enrollment import convert_application_to_policy

# Convert to policy
success, policy = convert_application_to_policy(application, reviewed_by=user)

if success:
    print(f"Policy created: {policy.policy_number}")
```

---

## Configuration

### OTP Settings
```python
# settings.py
OTP_EXPIRY_MINUTES = 15  # OTP valid for 15 minutes
OTP_MAX_ATTEMPTS = 3     # Max failed verification attempts
OTP_MAX_RESENDS = 3      # Max times OTP can be resent
```

### Email Settings
Ensure SMTP is configured for sending:
- Confirmation emails to client
- Rejection emails to client
- Admin notifications

### SMS Settings (BulkSMS)
OTP sent via SMS requires:
- BULKSMS_USERNAME
- BULKSMS_PASSWORD
- Valid .env configuration

---

## Security Features

### 1. **Token Security**
- Unique 48-character URL-safe token
- Can expire
- One-time tracking

### 2. **Data Encryption**
- PII fields encrypted: ID#, passport, account#
- Uses `FIELD_ENCRYPTION_KEY` from Phase 8

### 3. **OTP Verification**
- 6-digit random code
- 15-minute expiry
- 3 attempts before lockout
- Resend limited to 3 times

### 4. **POPIA Compliance**
- Separate consent tracking
- Document versioning
- IP + user agent capture
- Full audit trail

### 5. **Access Control**
- Public facing: No auth required
- Review & approval: Branch/Scheme managers only
- Conversion: Admin only

---

## Testing Checklist

### Public Client Flow
- [ ] Access link from email/SMS
- [ ] Enter personal details (SA ID validation)
- [ ] Enter address
- [ ] Select plan + payment method
- [ ] Conditional questions show/hide correctly
- [ ] Bank details shown only for debit order
- [ ] Review screen shows all data
- [ ] POPIA consent required
- [ ] OTP sent to phone
- [ ] OTP verification works (success + failure cases)
- [ ] Application submitted successfully
- [ ] Confirmation page shows reference #

### Admin Review Flow
- [ ] Dashboard shows submitted applications
- [ ] Can view full application details
- [ ] Can approve application
- [ ] Approved → Converted to Policy + Member
- [ ] Member receives confirmation email
- [ ] Can reject with reason
- [ ] Rejected → Client receives rejection email

### Edge Cases
- [ ] Expired link cannot be used
- [ ] Invalid token shows error
- [ ] OTP expires after 15 min
- [ ] Max OTP attempts → locked
- [ ] OTP resend works (max 3 times)
- [ ] Session times out → safe redirect
- [ ] Required fields validation
- [ ] Payment details only shown for debit order

---

## Next Phase: Admin Views

Create Django admin views for:
1. Application dashboard/list view
2. Application detail/review page
3. Approve/reject actions
4. Conversion to policy process
5. Statistics/analytics dashboard

---

## File Structure

```
members/
├── models_public_enrollment.py      # Public enrollment models
├── forms_public_enrollment.py       # Public enrollment forms
├── views_public_enrollment.py       # Public enrollment views
├── utils_public_enrollment.py       # Utility functions
├── urls_public_enrollment.py        # URL routing
└── management/commands/
    └── create_enrollment_link.py    # CLI tool for link generation

templates/
└── members/public_enrollment/
    ├── start.html                   # Entry page
    ├── step1_personal.html
    ├── step2_address.html
    ├── step3_plan_selection.html
    ├── step4_payment_details.html
    ├── step5_questions.html
    ├── step6_consent.html
    ├── otp_verification.html
    ├── success.html
    └── emails/
        ├── policy_confirmation.html
        └── application_rejected.html
```

---

## Important Notes

### Database Migration to Existing Systems
If replicating to existing deployment:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Sample Questions Setup
Create questions for each scheme via:
1. Django admin interface (if you add to admin.py)
2. Management command
3. API endpoint (create later)

### POPIA Compliance
Store links to:
- Terms & Conditions document
- Privacy Policy document
- POPIA notice

Ensure clients accept before submitting.

---

## Optional Enhancements

- [ ] ID document OCR upload (extract ID# from photo)
- [ ] Proof of residence upload
- [ ] Bank statement upload (for debit order verification)
- [ ] WhatsApp notifications instead of SMS
- [ ] Email follow-up reminders
- [ ] Application tracking via email link
- [ ] Premium calculator on plan selection
- [ ] Document e-signature
- [ ] Real-time applicant chat support
