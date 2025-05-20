from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Max


class Member(models.Model):
    TITLE_CHOICES = [
        ('Mr', 'Mr.'), ('Mrs', 'Mrs.'), ('Ms', 'Ms.'),
        ('Miss', 'Miss.'), ('Dr', 'Dr.'), ('Prof', 'Prof.'),
        ('Other', 'Other...')
    ]
    MARITAL_STATUS_CHOICES = [
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Widowed', 'Widowed'),
        ('Partnered', 'Partnered'),
        ('Divorced', 'Divorced'),
    ]

    title = models.CharField(max_length=20, choices=TITLE_CHOICES, blank=True, null=True)
    first_name = models.CharField(max_length=255, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=255, verbose_name=_('Last Name'))
    id_number = models.CharField(max_length=13, blank=True, null=True, verbose_name=_('ID Number'))
    passport_number = models.CharField(max_length=20, blank=True, verbose_name=_('Passport Number'))
    gender = models.CharField(max_length=6, choices=[('Female','Female'),('Male','Male')], verbose_name=_('Gender'))
    date_of_birth = models.DateField(verbose_name=_('Date of Birth'))
    phone_number = models.CharField(max_length=20, verbose_name=_('Phone Number'))
    whatsapp_number = models.CharField(max_length=20, blank=True, verbose_name=_('WhatsApp Number'))
    email = models.EmailField(blank=True, verbose_name=_('Email'))
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES, verbose_name=_('Marital Status'), blank=True, null=True)

    nationality = models.CharField(max_length=100, blank=True, verbose_name=_('Nationality'))
    country_of_birth = models.CharField(max_length=100, blank=True, verbose_name=_('Country of Birth'))
    country_of_residence = models.CharField(max_length=100, blank=True, verbose_name=_('Country of Residence'))

    physical_address_line_1 = models.CharField(max_length=255, blank=True, verbose_name=_('Address line 1'))
    physical_address_line_2 = models.CharField(max_length=255, blank=True, verbose_name=_('Address line 2'))
    physical_address_city = models.CharField(max_length=100, blank=True, verbose_name=_('City'))
    physical_address_postal_code = models.CharField(max_length=10, blank=True, verbose_name=_('Postal code'))
    
    # Spouse information
    spouse_first_name = models.CharField(max_length=100, blank=True, verbose_name=_("Spouse's First Name"))
    spouse_last_name = models.CharField(max_length=100, blank=True, verbose_name=_("Spouse's Last Name"))
    spouse_id_number = models.CharField(max_length=13, blank=True, null=True, verbose_name=_("Spouse's ID Number"))
    spouse_date_of_birth = models.DateField(null=True, blank=True, verbose_name=_("Spouse's Date of Birth"))
    spouse_gender = models.CharField(
        max_length=6, 
        choices=[('Female', 'Female'), ('Male', 'Male')], 
        blank=True, 
        verbose_name=_("Spouse's Gender")
    )
    spouse_phone_number = models.CharField(max_length=20, blank=True, verbose_name=_("Spouse's Phone Number"))
    spouse_email = models.EmailField(blank=True, verbose_name=_("Spouse's Email"))
    spouse_passport_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Spouse's Passport Number"))
    spouse_nationality = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Spouse's Nationality"))
    spouse_country_of_birth = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Spouse's Country of Birth"))
    spouse_country_of_residence = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Spouse's Country of Residence"))

    created_at = models.DateTimeField(auto_now_add=True)
    
    def validate_id_number(self, id_number):
        """Validate South African ID number using Luhn algorithm"""
        from utils.luhn import luhn_check
        return luhn_check(id_number)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


from django.db import models
from settings_app.models import Agent  # Import the Agent model

class Policy(models.Model):
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='policies')
    scheme = models.ForeignKey('schemes.Scheme', on_delete=models.PROTECT, null=True, blank=True)
    plan = models.ForeignKey('schemes.Plan', on_delete=models.PROTECT, null=True, blank=True)
    membership_number = models.CharField(max_length=50, blank=True, null=True)
    uw_membership_number = models.CharField(max_length=50, blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    inception_date = models.DateField(null=True, blank=True)
    cover_date = models.DateField(null=True, blank=True)
    policy_number = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    PAYMENT_METHODS = [
        ('DEBIT_ORDER', 'Debit Order'),
        ('EFT', 'EFT'),
        ('EASYPAY', 'Easypay'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='DEBIT_ORDER')
    bank = models.ForeignKey('branches.Bank', null=True, blank=True, on_delete=models.SET_NULL)
    branch_code = models.CharField(max_length=10, blank=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    debit_instruction_day = models.CharField(max_length=20, blank=True)
    eft_agreed = models.BooleanField(default=False)
    easypay_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    barcode = models.ImageField(upload_to='barcodes/', blank=True, null=True)
    document = models.FileField(upload_to='policies/', blank=True, null=True, help_text='PDF policy document')
    email_sent_at = models.DateTimeField(blank=True, null=True, help_text='When the policy document was emailed to the member')

    otp_confirmed = models.BooleanField(default=False)
    
    # Change this to a ForeignKey to Agent model
    underwritten_by = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True)
    
    cover_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    premium_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unique_policy_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Lapse warning flag
    LAPSE_WARNING_CHOICES = [
        ('none', 'No Warning'),
        ('warning', 'At Risk'),
        ('lapsed', 'Lapsed'),
    ]
    lapse_warning = models.CharField(max_length=10, choices=LAPSE_WARNING_CHOICES, default='none')

    def save(self, *args, **kwargs):
        # Set timestamps
        now = timezone.now()
        if not self.pk:
            self.created_at = now
        self.updated_at = now
        
        # Generate policy number if new
        if not self.policy_number:
            import uuid
            self.policy_number = f"POL-{uuid.uuid4().hex[:8].upper()}"
        
        # Save to get a PK if new
        super().save(*args, **kwargs)
        
        # Generate UW membership number if not set (needs PK)
        if not self.uw_membership_number:
            prefix = "POL"
            if self.scheme and self.scheme.name:
                prefix = self.scheme.name[:3].upper().replace(' ', '')
            self.uw_membership_number = f"{prefix}-{self.pk:06d}"
            # Save again to update the membership number
            kwargs['force_insert'] = False  # Make sure it's an update
            kwargs['force_update'] = True
            super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Policy #{self.policy_number or self.pk} for {self.member}"

    def get_share_message(self):
        return (
            f"Hi {self.member.first_name}, your funeral policy is now active.\n\n"
            f"📄 Membership No: {self.membership_number or '—'}\n"
            f"📘 Plan: {self.plan.name}\n"
            f"💰 EasyPay No: {self.easypay_number or 'Not available'}\n\n"
            "Download your full policy document here:\n"
            f"https://yourdomain.com{reverse('members:download_policy_by_policy', args=[self.pk])}"
        )
        
    def check_lapse_risk(self):
        """
        Check if the policy is at risk of lapsing based on payment history.
        Updates the lapse_warning field and returns the warning level.
        
        Returns:
            str: 'none', 'warning', or 'lapsed'
        """
        from payments.models import Payment
        
        # Get the latest successful payment
        latest_payment = Payment.objects.filter(
            policy=self,
            status='successful'
        ).order_by('-date').first()
        
        if not latest_payment:
            # No payments found
            self.lapse_warning = 'warning'
            self.save(update_fields=['lapse_warning'])
            return self.lapse_warning
        
        # Calculate days since last payment
        days_since_payment = (timezone.now().date() - latest_payment.date).days
        
        # Update lapse warning based on days since last payment
        if days_since_payment > 60:
            self.lapse_warning = 'lapsed'
        elif days_since_payment > 45:
            self.lapse_warning = 'warning'
        else:
            self.lapse_warning = 'none'
        
        self.save(update_fields=['lapse_warning'])
        return self.lapse_warning



class Dependent(models.Model):
    GENDER_CHOICES = [
        ('Female', 'Female'),
        ('Male', 'Male'),
    ]
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='dependents')
    relationship = models.CharField(max_length=50, verbose_name=_('Relationship'))
    id_number = models.CharField(max_length=13, blank=True, verbose_name=_('ID Number'))
    first_name = models.CharField(max_length=255, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=255, verbose_name=_('Last Name'))
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, verbose_name=_('Gender'))
    date_of_birth = models.DateField(verbose_name=_('Date of Birth'))

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.relationship})"


class Beneficiary(models.Model):
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
    ]
    
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='beneficiaries')
    relationship_to_main_member = models.CharField(max_length=50, verbose_name=_('Relationship to Main Member'))
    id_number = models.CharField(max_length=13, blank=True, verbose_name=_('ID Number'))
    first_name = models.CharField(max_length=255, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=255, verbose_name=_('Last Name'))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date of Birth'))
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name=_('Gender'))
    share = models.PositiveSmallIntegerField(default=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.share}% share)"
        
    def save(self, *args, **kwargs):
        # If we have an ID number but no date of birth or gender, try to extract them
        if self.id_number and (not self.date_of_birth or not self.gender):
            valid, id_dob, gender = validate_id_number(self.id_number)
            if valid:
                if not self.date_of_birth:
                    self.date_of_birth = id_dob
                if not self.gender:
                    self.gender = gender
        super().save(*args, **kwargs)


class OtpVerification(models.Model):
    policy = models.OneToOneField(Policy, on_delete=models.CASCADE, related_name='otp')
    code_hash = models.CharField(max_length=128)
    sent_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    resent_count = models.PositiveSmallIntegerField(default=0)

    def generate_new_code(self):
        import random, string, hashlib
        otp = ''.join(random.choices(string.digits, k=6))
        self.code_hash = hashlib.sha256(otp.encode()).hexdigest()
        self.sent_at = timezone.now()
        self.resent_count += 1
        self.attempts = 0
        self.save()
        return otp

    def check_code(self, code):
        import hashlib
        if self.attempts >= 3:
            return False
        if timezone.now() - self.sent_at > timezone.timedelta(minutes=5):
            return False
        if hashlib.sha256(code.encode()).hexdigest() == self.code_hash:
            self.attempts += 1
            self.save()
            return True
        self.attempts += 1
        self.save()
        return False

from django.db import models
from settings_app.models import Agent

class DiySignupLog(models.Model):
    agent        = models.ForeignKey(Agent, on_delete=models.CASCADE)
    member       = models.ForeignKey("self", null=True, on_delete=models.SET_NULL)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent} – {self.completed_at:%Y-%m-%d %H:%M}"
