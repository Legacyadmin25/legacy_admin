# settings_app/models.py (FULL corrected and expanded version)

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

# Get the custom User model
User = get_user_model()

# ─── SCHEME ─────────────────────────────────────────────────────────────



class SchemeDocument(models.Model):
    scheme = models.ForeignKey('schemes.Scheme', on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='scheme_docs/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# ─── BRANCH ─────────────────────────────────────────────────────────────

class Branch(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    cell = models.CharField(max_length=20, blank=True, null=True)
    physical_address = models.CharField(max_length=200, blank=True)
    street = models.CharField(max_length=100, blank=True)
    town = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)

    modified_user = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='settings_branch_modifications'
    )
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name


# ─── AGENT ──────────────────────────────────────────────────────────────
# settings_app/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core import signing
from django.urls import reverse

class Agent(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent',
        null=True,
        blank=True
    )
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.SET_NULL,
        related_name="agents",
        null=True,
        blank=True
    )
    full_name = models.CharField(max_length=200)
    surname = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=10)
    email = models.EmailField()
    id_number = models.CharField(max_length=13, blank=True, null=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    commission_percentage = models.FloatField(blank=True, null=True)
    commission_rand_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255)
    address3 = models.CharField(max_length=255)
    code = models.CharField(max_length=10)

    # ─── Internal Notes ─────────────────────────────────────────────
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this agent"
    )

    # ─── DIY‐Signup Token Fields ─────────────────────────────────────────────
    diy_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Signed token for DIY signup links"
    )
    diy_token_created = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the current diy_token was issued"
    )

    def __str__(self):
        return f"{self.full_name} ({self.scheme.name if self.scheme else 'No Scheme'})"

    def generate_diy_token(self):
        signer = signing.TimestampSigner()
        token = signer.sign(self.pk)
        self.diy_token = token
        self.diy_token_created = timezone.now()
        self.save(update_fields=['diy_token', 'diy_token_created'])
        return token

    def revoke_diy_token(self):
        self.diy_token = None
        self.diy_token_created = None
        self.save(update_fields=['diy_token', 'diy_token_created'])

    def get_diy_url(self):
        if not self.diy_token:
            return "#"
        return reverse('members:diy_signup_start', args=[self.diy_token])

    def get_full_diy_link(self):
        if not self.diy_token:
            return None
        domain = getattr(settings, "SITE_URL", "https://yourdomain.com")
        return domain + self.get_diy_url()

    def save(self, *args, **kwargs):
        if not self.diy_token:
            self.generate_diy_token()
        super().save(*args, **kwargs)




# ─── UNDERWRITER ────────────────────────────────────────────────────────

class Underwriter(models.Model):
    name = models.CharField(max_length=255)
    fsp_number = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    address1 = models.CharField(max_length=255, blank=True, null=True)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    address3 = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    logo = models.ImageField(upload_to='underwriter_logos/', blank=True, null=True)
    disclaimer = models.TextField(blank=True, null=True)
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UnderwriterDocument(models.Model):
    name = models.CharField(max_length=255)
    document = models.FileField(upload_to='underwriter_documents/')
    underwriter = models.ForeignKey(Underwriter, on_delete=models.CASCADE, related_name='documents')

    def __str__(self):
        return self.name


# ─── PLAN ───────────────────────────────────────────────────────────────

USER_TYPE_CHOICES = [
    ('Spouse', 'Spouse'),
    ('Child', 'Child'),
    ('Extended', 'Extended'),
    ('Adult', 'Adult'),
    ('Extended Child', 'Extended Rider 1'),
]


from schemes.models import Plan as SchemePlan

class PlanMemberTier(models.Model):
    plan = models.ForeignKey(SchemePlan, on_delete=models.CASCADE, related_name='tiers')
    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES)
    age_from = models.PositiveIntegerField()
    age_to = models.PositiveIntegerField()
    cover = models.DecimalField(max_digits=10, decimal_places=2)
    premium = models.DecimalField(max_digits=10, decimal_places=2)
    underwriter_cover = models.DecimalField(max_digits=10, decimal_places=2)
    underwriter_premium = models.DecimalField(max_digits=10, decimal_places=2)
    extended_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user_type} - {self.cover}"


# ─── AI PRIVACY & COMPLIANCE ────────────────────────────────────────────

class AIRequestLog(models.Model):
    """
    Log of all AI requests made through the system for compliance and auditing
    """
    ACTION_CHOICES = (
        ('search', 'AI Search'),
        ('summarize', 'Content Summarization'),
        ('insight', 'Data Insights'),
        ('suggestion', 'Tier Suggestion'),
        ('other', 'Other AI Action'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ai_requests')
    timestamp = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    prompt_summary = models.CharField(max_length=255, blank=True, null=True, 
                                     help_text="High-level summary of the prompt (no PII)")
    model_used = models.CharField(max_length=50, blank=True, null=True)
    response_status = models.BooleanField(default=True, help_text="Whether the request was successful")
    
    class Meta:
        verbose_name = "AI Request Log"
        verbose_name_plural = "AI Request Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"


class AIUserConsent(models.Model):
    """
    Tracks user consent for AI features
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_consent')
    search_consent = models.BooleanField(default=False, help_text="Consent for AI-powered search")
    insight_consent = models.BooleanField(default=False, help_text="Consent for AI-powered insights")
    suggestion_consent = models.BooleanField(default=False, help_text="Consent for AI-powered suggestions")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI User Consent"
        verbose_name_plural = "AI User Consents"
    
    def __str__(self):
        return f"AI consent for {self.user}"


class AISettings(models.Model):
    """
    Global AI settings for the application
    Singleton model - only one instance should exist
    """
    default_model = models.CharField(max_length=50, default="gpt-4o", 
                                     help_text="Default OpenAI model to use")
    enable_logging = models.BooleanField(default=True, 
                                        help_text="Whether to log AI requests")
    require_consent = models.BooleanField(default=True, 
                                         help_text="Whether to require explicit consent for AI features")
    max_tokens = models.IntegerField(default=1000, 
                                    help_text="Maximum tokens for AI responses")
    temperature = models.FloatField(default=0.7, 
                                   help_text="Temperature for AI responses (0.0-1.0)")
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, 
                                   related_name='ai_settings_updates')
    
    class Meta:
        verbose_name = "AI Settings"
        verbose_name_plural = "AI Settings"
    
    def __str__(self):
        return f"AI Settings (last updated: {self.last_updated})"
    
    @classmethod
    def get_settings(cls):
        """Get the global AI settings, creating if needed"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


# ─── USERS & RIGHTS ─────────────────────────────────────────────────────

class UserRole(models.Model):
    """Role model for user permissions in Branch-Scheme-Agent hierarchy"""
    ROLE_CHOICES = (
        ('internal_admin', 'Internal Admin'),
        ('branch_owner', 'Branch Owner'),
        ('scheme_manager', 'Scheme Manager'),
        ('compliance_auditor', 'Compliance Auditor'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='role')
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES)
    branch = models.ForeignKey('settings_app.Branch', on_delete=models.SET_NULL, null=True, blank=True, 
                              related_name='assigned_users')
    scheme = models.ForeignKey('schemes.Scheme', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='assigned_users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_type_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to ensure role consistency"""
        # If role is internal_admin, clear branch and scheme
        if self.role_type == 'internal_admin':
            self.branch = None
            self.scheme = None
        
        # If role is branch_owner, clear scheme
        elif self.role_type == 'branch_owner':
            self.scheme = None
            
        # If role is scheme_manager, ensure branch is set to scheme's branch
        elif self.role_type == 'scheme_manager' and self.scheme:
            self.branch = self.scheme.branch
            
        # If role is compliance_auditor, clear branch and scheme
        elif self.role_type == 'compliance_auditor':
            self.branch = None
            self.scheme = None
            
        super().save(*args, **kwargs)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.username

class UserGroup(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class PagePermission(models.Model):
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)
    page_name = models.CharField(max_length=100)
    has_rights = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_write = models.BooleanField(default=False)
    is_update = models.BooleanField(default=False)
    is_payment_reversal = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.group.name} - {self.page_name}"

class Settings(models.Model):
    # Add your global settings here
    site_name = models.CharField(max_length=255, default="Legacy Admin")
    site_description = models.TextField(blank=True, default="")

    def __str__(self):
        return "Global Settings"

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class UserImportLog(models.Model):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    success_count = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)

    def __str__(self):
        return f"{self.uploaded_by} on {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
