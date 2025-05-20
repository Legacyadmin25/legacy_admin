from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
import uuid
import json
import random
import string

class DIYApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('incomplete', 'Incomplete'),
    ]
    
    PAYMENT_METHODS = [
        ('debit_order', 'Debit Order'),
        ('eft', 'Electronic Funds Transfer (EFT)'),
        ('easypay', 'Easypay QR Code'),
    ]
    
    PREMIUM_FREQUENCY = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ]
    
    # Application Information
    application_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    current_step = models.PositiveIntegerField(default=1)
    
    # Agent Information (if applicable)
    agent = models.ForeignKey(
        'settings_app.Agent', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='diy_applications'
    )
    agent_code = models.CharField(max_length=50, blank=True, null=True)
    
    # Plan Information
    plan = models.ForeignKey(
        'schemes.Plan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='diy_applications'
    )
    monthly_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    premium_frequency = models.CharField(max_length=20, choices=PREMIUM_FREQUENCY, default='monthly')
    has_spouse = models.BooleanField(default=False)
    has_children = models.BooleanField(default=False)
    has_extended_family = models.BooleanField(default=False)
    children_count = models.PositiveIntegerField(default=0)
    extended_family_members = models.PositiveIntegerField(default=0)
    
    # Payment Information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    payment_reference = models.CharField(max_length=50, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Debit Order Details (if applicable)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    account_type = models.CharField(max_length=20, blank=True, null=True)
    branch_code = models.CharField(max_length=20, blank=True, null=True)
    account_holder_name = models.CharField(max_length=100, blank=True, null=True)
    debit_day = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        null=True, blank=True,
        default=1
    )
    
    # OTP Verification
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_generated_at = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    otp_attempts = models.PositiveIntegerField(default=0)
    
    # Resume Later Functionality
    resume_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    resume_token_expires_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    
    # Consent Information
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    popia_consent = models.BooleanField(default=False)
    fsca_disclosure = models.BooleanField(default=False)
    
    # PDF Certificate
    certificate_generated = models.BooleanField(default=False)
    certificate_generated_at = models.DateTimeField(null=True, blank=True)
    certificate_url = models.URLField(blank=True, null=True)
    certificate_file = models.FileField(upload_to='certificates/%Y/%m/', blank=True, null=True)
    certificate_download_count = models.PositiveIntegerField(default=0)
    
    # Additional Data
    form_data = models.JSONField(default=dict, blank=True)  # Store raw form data
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'DIY Application'
        verbose_name_plural = 'DIY Applications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_policy_type_display()} - {self.reference_number}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            # Generate a reference number if not set
            self.reference_number = self._generate_reference_number()
        
        # Update timestamps
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def _generate_reference_number(self):
        """Generate a unique reference number in the format: DIY-YYYYMM-XXXX"""
        from datetime import datetime
        now = datetime.now()
        prefix = f"DIY-{now.year}{now.month:02d}-"
        
        # Find the highest existing reference number with this prefix
        highest = 0
        for app in DIYApplication.objects.filter(reference_number__startswith=prefix):
            try:
                num = int(app.reference_number.split('-')[-1])
                if num > highest:
                    highest = num
            except (ValueError, IndexError):
                pass
        
        # Generate the new reference number
        return f"{prefix}{highest + 1:04d}"
        
    def generate_otp(self):
        """Generate a 6-digit OTP code"""
        otp = ''.join(random.choices('0123456789', k=6))
        self.otp_code = otp
        self.otp_generated_at = timezone.now()
        self.otp_attempts = 0
        self.save(update_fields=['otp_code', 'otp_generated_at', 'otp_attempts'])
        return otp
        
    def verify_otp(self, code):
        """Verify the OTP code"""
        # Check if OTP is expired (15 minutes)
        if not self.otp_generated_at or (timezone.now() - self.otp_generated_at).total_seconds() > 900:
            return False, "OTP has expired. Please request a new one."
            
        # Check if too many attempts
        if self.otp_attempts >= 3:
            return False, "Too many failed attempts. Please request a new OTP."
            
        # Check if code matches
        if self.otp_code != code:
            self.otp_attempts += 1
            self.save(update_fields=['otp_attempts'])
            return False, "Invalid OTP code. Please try again."
            
        # OTP is valid
        self.otp_verified = True
        self.save(update_fields=['otp_verified'])
        return True, "OTP verified successfully."
        
    def generate_resume_token(self):
        """Generate a token for resuming the application later"""
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        self.resume_token = token
        self.resume_token_expires_at = timezone.now() + timezone.timedelta(days=7)
        self.save(update_fields=['resume_token', 'resume_token_expires_at'])
        return token
        
    def get_resume_url(self):
        """Get the URL for resuming the application"""
        if not self.resume_token:
            self.generate_resume_token()
        return reverse('members:diy_resume', kwargs={'token': self.resume_token})
        
    def can_resume(self):
        """Check if the application can be resumed"""
        if not self.resume_token or not self.resume_token_expires_at:
            return False
        return timezone.now() < self.resume_token_expires_at
    
    def calculate_premium(self):
        """Calculate the monthly premium based on policy details"""
        # Base premium calculation (simplified example)
        base_amount = float(self.cover_amount)
        
        # Base rate (1% of cover amount)
        premium = base_amount * 0.01
        
        # Apply discounts for higher cover amounts
        if base_amount > 50000:
            premium *= 0.9  # 10% discount for > R50k
        elif base_amount > 30000:
            premium *= 0.95  # 5% discount for > R30k
        
        # Add for extended family if selected
        if self.has_extended_family and self.extended_family_members > 0:
            premium += (self.extended_family_members * 50)  # R50 per extended family member
        
        # Ensure minimum premium of R50
        premium = max(50, round(premium, 2))
        
        return premium
    
    def send_confirmation_email(self):
        """Send confirmation email to the applicant"""
        if not hasattr(self, 'applicant'):
            return False
            
        subject = f"Application Confirmation - {self.reference_number}"
        html_message = render_to_string('emails/diy_application_confirmation.html', {
            'application': self,
            'applicant': self.applicant,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.applicant.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            # Log the error
            print(f"Error sending confirmation email: {e}")
            return False


class DIYApplicant(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('life_partner', 'Life Partner'),
        ('other', 'Other'),
    ]
    
    # Application reference
    application = models.OneToOneField(
        DIYApplication,
        on_delete=models.CASCADE,
        related_name='applicant',
        primary_key=True
    )
    
    # Personal Information
    title = models.CharField(max_length=10)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=13, unique=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    
    # Contact Information
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Address Information
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='South Africa')
    
    # Additional Information
    is_south_african = models.BooleanField(default=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'DIY Applicant'
        verbose_name_plural = 'DIY Applicants'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_age(self):
        """Calculate age from date of birth"""
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


class DIYBeneficiary(models.Model):
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other_relative', 'Other Relative'),
        ('friend', 'Friend'),
        ('trust', 'Trust'),
        ('estate', 'Estate'),
    ]
    
    application = models.ForeignKey(
        DIYApplication,
        on_delete=models.CASCADE,
        related_name='beneficiaries'
    )
    
    # Beneficiary Information
    full_name = models.CharField(max_length=200)
    id_number = models.CharField(max_length=13, blank=True, null=True)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100)]
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Additional Information
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'DIY Beneficiary'
        verbose_name_plural = 'DIY Beneficiaries'
        ordering = ['-is_primary', 'id']
    
    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()}) - {self.percentage}%"
    
    def clean(self):
        """Validate that the total percentage doesn't exceed 100%"""
        from django.core.exceptions import ValidationError
        
        if self.percentage > 100:
            raise ValidationError({'percentage': 'Percentage cannot exceed 100%'})
        
        # Calculate total percentage including this beneficiary
        if self.pk:  # If updating an existing instance
            total = DIYBeneficiary.objects.filter(
                application=self.application
            ).exclude(
                pk=self.pk
            ).aggregate(
                total=models.Sum('percentage')
            )['total'] or 0
        else:  # If creating a new instance
            total = DIYBeneficiary.objects.filter(
                application=self.application
            ).aggregate(
                total=models.Sum('percentage')
            )['total'] or 0
        
        if total + self.percentage > 100:
            raise ValidationError({
                'percentage': f'Total percentage exceeds 100%. Current total: {total}%'
            })


class DIYApplicationDocument(models.Model):
    DOCUMENT_TYPES = [
        ('id_copy', 'ID Copy'),
        ('proof_of_address', 'Proof of Address'),
        ('bank_statement', 'Bank Statement'),
        ('proof_of_income', 'Proof of Income'),
        ('other', 'Other'),
    ]
    
    application = models.ForeignKey(
        DIYApplication,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='diy_application_documents/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    file_type = models.CharField(max_length=50)
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Additional Information
    description = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    
    class Meta:
        verbose_name = 'DIY Application Document'
        verbose_name_plural = 'DIY Application Documents'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.original_filename}"
    
    def save(self, *args, **kwargs):
        # Set original filename and file info if this is a new file
        if self.file and not self.original_filename:
            self.original_filename = self.file.name
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1].lower()
        
        super().save(*args, **kwargs)
    
    def get_file_url(self):
        """Return the URL to access the file"""
        if self.file:
            return self.file.url
        return None
    
    def get_file_icon(self):
        """Return an appropriate icon based on file type"""
        file_type = self.file_type.lower()
        
        if file_type in ['pdf']:
            return 'fa-file-pdf'
        elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            return 'fa-file-image'
        elif file_type in ['doc', 'docx']:
            return 'fa-file-word'
        elif file_type in ['xls', 'xlsx', 'csv']:
            return 'fa-file-excel'
        else:
            return 'fa-file-alt'
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
