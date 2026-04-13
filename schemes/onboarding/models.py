from datetime import timedelta
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class BranchSchemeOnboarding(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_REOPENED = 'reopened_for_corrections'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_REOPENED, 'Reopened for Corrections'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    ACCOUNT_TYPE_CHOICES = [
        ('Savings', 'Savings'),
        ('Current', 'Current'),
    ]

    onboarding_token = models.CharField(max_length=48, unique=True, db_index=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='scheme_onboardings')

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)

    company_name = models.CharField(max_length=200, blank=True)
    registration_no = models.CharField(max_length=100, blank=True)
    fsp_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    bank_account_no = models.CharField(max_length=50, blank=True)
    debit_order_no = models.CharField(max_length=50, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='Savings')

    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.CharField(max_length=200, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_scheme_onboardings',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reopened_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name or 'New Scheme'} ({self.branch.name})"

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(36)[:48]

    @classmethod
    def create_with_token(cls, **kwargs):
        kwargs.setdefault('onboarding_token', cls.generate_token())
        if not kwargs.get('expires_at'):
            kwargs['expires_at'] = timezone.now() + timedelta(days=7)
        return cls.objects.create(**kwargs)

    def is_token_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def mark_used(self):
        self.times_used += 1
        self.save(update_fields=['times_used', 'updated_at'])

    def submit(self, submitted_by=''):
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()
        self.submitted_by = submitted_by
        self.reopened_notes = ''
        self.save(update_fields=['status', 'submitted_at', 'submitted_by', 'reopened_notes', 'updated_at'])

    def approve(self, reviewer):
        self.status = self.STATUS_APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

    def reopen(self, reviewer, notes):
        self.status = self.STATUS_REOPENED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.reopened_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'reopened_notes', 'updated_at'])
