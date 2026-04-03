"""
Public Enrollment Models - For self-service policy applications
Separate from admin-created policies for tracking and approval workflow
"""

from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from encrypted_model_fields.fields import EncryptedCharField
import uuid
import secrets


# Helper functions for default values (must be module-level for migration serialization)
def generate_enrollment_token():
    """Generate a unique secure token for enrollment links"""
    return secrets.token_urlsafe(48)


def generate_otp_code():
    """Generate a 6-digit OTP code"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


class EnrollmentLink(models.Model):
    """
    Secure token-based links for public enrollment
    Agents/branches can share these links with clients
    Format: /apply/{token}?scheme={scheme_id}&branch={branch_id}&agent={agent_id}
    """
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_enrollment_token,
        help_text="Unique token for this enrollment link"
    )
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.CASCADE,
        related_name='enrollment_links'
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='enrollment_links'
    )
    agent = models.ForeignKey(
        'settings_app.Agent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollment_links',
        help_text="Agent who generated this link (optional)"
    )
    
    # Link settings
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Link expires after this date (optional)"
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_enrollment_links'
    )
    
    # Tracking
    times_used = models.IntegerField(default=0, help_text="Number of times link was accessed")
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.scheme.name} - {self.branch.name} - {self.token[:8]}..."
    
    def is_valid(self):
        """Check if link can still be used"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
    
    def mark_used(self):
        """Track that link was used"""
        self.times_used += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['times_used', 'last_used_at'])
    
    def get_apply_url(self, request=None):
        """Generate full URL for this enrollment link"""
        base_url = f"/apply/{self.token}/"
        if request:
            return request.build_absolute_uri(base_url)
        return base_url


class PublicApplication(models.Model):
    """
    Self-service policy application from public users
    Separate from admin-created policies - requires review before conversion to policy
    """
    STATUS_CHOICES = [
        ('draft', 'Draft - In Progress'),
        ('submitted', 'Submitted - Awaiting Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed - Policy Created'),
    ]
    
    # Application reference
    application_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="e.g., APP-20260328-001"
    )
    
    # Applicant Info (from form)
    title = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    
    # Identification
    id_number = EncryptedCharField(max_length=13, blank=True, null=True)
    passport_number = EncryptedCharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=6,
        choices=[('Female', 'Female'), ('Male', 'Male')]
    )
    
    # Address
    physical_address_line_1 = models.CharField(max_length=255)
    physical_address_line_2 = models.CharField(max_length=255, blank=True)
    physical_address_city = models.CharField(max_length=100)
    physical_address_postal_code = models.CharField(max_length=10, blank=True)
    
    # Marital & Family
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ('Single', 'Single'),
            ('Married', 'Married'),
            ('Widowed', 'Widowed'),
            ('Partnered', 'Partnered'),
            ('Divorced', 'Divorced'),
        ]
    )
    
    # Scheme & Plan Selection
    enrollment_link = models.ForeignKey(
        EnrollmentLink,
        on_delete=models.SET_NULL,
        null=True,
        related_name='applications'
    )
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.PROTECT,
        related_name='public_applications'
    )
    plan = models.ForeignKey(
        'schemes.Plan',
        on_delete=models.PROTECT,
        related_name='public_applications'
    )
    
    # Payment Method
    PAYMENT_METHOD_CHOICES = [
        ('DEBIT_ORDER', 'Debit Order'),
        ('EFT', 'EFT Transfer'),
        ('EASYPAY', 'EasyPay'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='DEBIT_ORDER'
    )
    
    # Bank Details (if debit order)
    bank = models.ForeignKey(
        'branches.Bank',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    branch_code = models.CharField(max_length=10, blank=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    account_number = EncryptedCharField(max_length=20, blank=True)
    debit_instruction_day = models.CharField(max_length=20, blank=True)
    
    # Status & Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Review
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, help_text="Admin notes on approval/rejection")
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection if applicable")
    
    # Conversion
    converted_policy = models.OneToOneField(
        'members.Policy',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_application'
    )
    converted_member = models.OneToOneField(
        'members.Member',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_application'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.application_id} - {self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate application ID on first save"""
        if not self.application_id:
            today = timezone.now().strftime('%Y%m%d')
            count = PublicApplication.objects.filter(
                created_at__date=timezone.now().date()
            ).count()
            self.application_id = f"APP-{today}-{count + 1:03d}"
        super().save(*args, **kwargs)
    
    def submit(self):
        """Mark application as submitted"""
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()
    
    def approve(self, user=None):
        """Approve application"""
        self.status = 'approved'
        self.reviewed_by = user
        self.save()
    
    def reject(self, reason, user=None):
        """Reject application"""
        self.status = 'rejected'
        self.review_notes = reason
        self.reviewed_by = user
        self.save()


class ApplicationAnswer(models.Model):
    """
    Stores answers to conditional questions during public enrollment
    Allows tracking full applicant response journey
    """
    application = models.ForeignKey(
        PublicApplication,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question_key = models.CharField(
        max_length=100,
        help_text="e.g., 'spouse_coverage', 'children_count'"
    )
    question_text = models.TextField(help_text="The actual question shown")
    answer = models.TextField()
    answer_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('choice', 'Choice/Selection'),
            ('number', 'Number'),
            ('yes_no', 'Yes/No'),
        ],
        default='text'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.application.application_id} - {self.question_key}"


class EnrollmentOTPVerification(models.Model):
    """
    OTP (One-Time Password) for phone verification in public enrollment
    Sent at the END of form submission for confirmation
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
        ('failed', 'Max Attempts Failed'),
    ]
    
    application = models.OneToOneField(
        PublicApplication,
        on_delete=models.CASCADE,
        related_name='otp_verification'
    )
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(
        max_length=6,
        default=generate_otp_code
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Tracking
    sent_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.IntegerField(default=0, help_text="Track failed attempts")
    max_attempts = models.IntegerField(default=3)
    
    # Retry & Expiry
    expires_at = models.DateTimeField(help_text="OTP expires after 15 minutes")
    resend_count = models.IntegerField(default=0)
    max_resends = models.IntegerField(default=3)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"OTP for {self.application.application_id} - {self.status}"
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def verify_otp(self, entered_otp):
        """Verify entered OTP"""
        if self.status != 'pending':
            return False, "OTP already used or failed"
        
        if self.is_expired():
            self.status = 'expired'
            self.save()
            return False, "OTP has expired"
        
        if self.verification_attempts >= self.max_attempts:
            self.status = 'failed'
            self.save()
            return False, "Maximum verification attempts exceeded"
        
        self.verification_attempts += 1
        
        if entered_otp != self.otp_code:
            self.save()
            remaining = self.max_attempts - self.verification_attempts
            return False, f"Invalid OTP. {remaining} attempts remaining"
        
        # Success
        self.status = 'verified'
        self.verified_at = timezone.now()
        self.save()
        return True, "Phone number verified successfully"
    
    def can_resend(self):
        """Check if OTP can be resent"""
        return self.resend_count < self.max_resends and self.status == 'pending'
    
    def resend(self):
        """Generate new OTP for resend"""
        if not self.can_resend():
            return False
        
        self.otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        self.sent_at = timezone.now()
        self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        self.resend_count += 1
        self.save()
        return True


class POPIAConsent(models.Model):
    """
    POPIA (Protection of Personal Information Act) Consent Tracking
    Required for South African compliance
    """
    CONSENT_TYPES = [
        ('data_processing', 'Data Processing'),
        ('marketing_sms', 'Marketing via SMS'),
        ('marketing_email', 'Marketing via Email'),
        ('data_sharing', 'Data Sharing with Partners'),
    ]
    
    application = models.ForeignKey(
        PublicApplication,
        on_delete=models.CASCADE,
        related_name='popia_consents'
    )
    
    consent_type = models.CharField(max_length=50, choices=CONSENT_TYPES)
    consented = models.BooleanField(
        default=False,
        help_text="Whether applicant gave consent for this type"
    )
    
    # Document version tracking
    terms_and_conditions_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Version of T&Cs accepted"
    )
    privacy_policy_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Version of privacy policy accepted"
    )
    
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address at time of consent"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser info at time of consent"
    )
    
    class Meta:
        unique_together = ['application', 'consent_type']
        ordering = ['-accepted_at']
    
    def __str__(self):
        return f"{self.application.application_id} - {self.consent_type}"


class EnrollmentQuestionBank(models.Model):
    """
    Question templates for different plans/schemes
    Supports conditional logic (if answer X, show question Y)
    """
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.CASCADE,
        related_name='enrollment_questions'
    )
    
    question_key = models.CharField(
        max_length=100,
        help_text="e.g., 'spouse_coverage'"
    )
    question_text = models.TextField()
    question_order = models.IntegerField(default=0, help_text="Display order")
    
    QUESTION_TYPE = [
        ('text', 'Text Input'),
        ('number', 'Number'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('date', 'Date'),
        ('choice', 'Multiple Choice'),
        ('yes_no', 'Yes/No'),
        ('checkbox', 'Checkbox'),
    ]
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE)
    
    # Options for choice questions
    options = models.JSONField(
        null=True,
        blank=True,
        help_text='For choice questions: ["Option 1", "Option 2"]'
    )
    
    # Conditional logic
    conditional_on = models.CharField(
        max_length=100,
        blank=True,
        help_text="Show this question if: sibling_question_key"
    )
    conditional_value = models.CharField(
        max_length=200,
        blank=True,
        help_text="...equals this value"
    )
    
    is_required = models.BooleanField(default=True)
    help_text_content = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheme', 'question_order']
        unique_together = ['scheme', 'question_key']
    
    def __str__(self):
        return f"{self.scheme.name} - {self.question_key}"
    
    def should_show(self, previous_answers):
        """Determine if this question should be shown based on previous answers"""
        if not self.conditional_on:
            return True
        
        # Find the answer to the conditional question
        if self.conditional_on in previous_answers:
            return str(previous_answers[self.conditional_on]) == self.conditional_value
        
        return False
