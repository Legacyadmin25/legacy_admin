# import_data/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone


# Constants for Choices
CATEGORY_POLICY = 'policy'
CATEGORY_AGENT = 'agent'
CATEGORY_PAYMENT = 'payment'

CATEGORY_CHOICES = [
    (CATEGORY_POLICY, 'Policy'),
    (CATEGORY_AGENT, 'Agent'),
    (CATEGORY_PAYMENT, 'Payment'),
]

STATUS_PENDING = 'pending'
STATUS_PROCESSING = 'processing'
STATUS_SUCCESS = 'success'
STATUS_FAILED = 'failed'

STATUS_CHOICES = [
    (STATUS_PENDING, 'Pending'),
    (STATUS_PROCESSING, 'Processing'),
    (STATUS_SUCCESS, 'Success'),
    (STATUS_FAILED, 'Failed'),
]


class ImportLog(models.Model):
    import_type = models.CharField(
        max_length=20,
        help_text="General type of data being imported (for legacy support)",
        default='legacy'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_POLICY,
        help_text="High-level import category (e.g., policy, agent, payment)"
    )
    subtype = models.CharField(
        max_length=50,
        blank=True,
        help_text="Specific subtype like 'bulk', 'amendment', 'easypay'"
    )
    filename = models.CharField(max_length=255)
    records_processed = models.PositiveIntegerField(default=0)
    records_successful = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who initiated the import"
    )

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['subtype']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        """Refactor __str__ method for consistency"""
        subtype = f" - {self.subtype}" if self.subtype else ""
        return f"{self.get_category_display()} Import{subtype} - {self.filename} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Auto-set completed_at when status is success or failed"""
        if self.status in {STATUS_SUCCESS, STATUS_FAILED} and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class PolicyAmendmentImport(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='policy_amendment_imports'
    )
    file = models.FileField(upload_to='imports/policy_amendments/')
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )

    def __str__(self):
        return f"Amendment Import #{self.id} by {self.uploaded_by} on {self.uploaded_at.date()}"


class PolicyAmendmentRowLog(models.Model):
    import_batch = models.ForeignKey(
        PolicyAmendmentImport,
        related_name='row_logs',
        on_delete=models.CASCADE
    )
    row_number = models.PositiveIntegerField()
    membership_number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[('success', 'Success'), ('error', 'Error'), ('not_found', 'Not Found')]
    )
    errors = models.JSONField(blank=True, null=True)
    changes = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Row {self.row_number}: {self.membership_number} -> {self.status}"


class LapsedPolicyReactivationImport(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='policy_reactivation_imports'
    )
    file = models.FileField(upload_to='imports/policy_reactivations/')
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )

    def __str__(self):
        return f"Reactivation Import #{self.id} by {self.uploaded_by} on {self.uploaded_at.date()}"


class LapsedPolicyReactivationRowLog(models.Model):
    import_batch = models.ForeignKey(
        LapsedPolicyReactivationImport,
        related_name='row_logs',
        on_delete=models.CASCADE
    )
    row_number = models.PositiveIntegerField()
    membership_number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[('success', 'Success'), ('error', 'Error'), ('not_found', 'Not Found')]
    )
    errors = models.JSONField(blank=True, null=True)
    changes = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Reactivation Row {self.row_number}: {self.membership_number} -> {self.status}"


class AgentOnboardingImport(models.Model):
    file = models.FileField(upload_to='imports/agent_onboarding/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='agent_onboarding_imports'
    )

    def __str__(self):
        return f"Agent Onboarding #{self.id} @ {self.uploaded_at:%Y-%m-%d %H:%M}"


class AgentOnboardingRowLog(models.Model):
    import_batch = models.ForeignKey(
        AgentOnboardingImport,
        related_name='row_logs',
        on_delete=models.CASCADE
    )
    row_number = models.PositiveIntegerField()
    full_name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    id_number = models.CharField(max_length=20, blank=True, null=True)
    passport_number = models.CharField(max_length=20, blank=True, null=True)
    scheme_code = models.CharField(max_length=50)
    code = models.CharField("Agent Code", max_length=50)
    contact_number = models.CharField(max_length=20)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=[('success', 'Success'), ('error', 'Error')]
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Row {self.row_number}: {self.status}"

class BankReconciliationImport(models.Model):
    file = models.FileField(upload_to='bank_reconciliation/')
    date_imported = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bank Reconciliation Import - {self.file.name}"

class BankReconciliationRowLog(models.Model):
    import_batch = models.ForeignKey(
        BankReconciliationImport,
        related_name='row_logs',
        on_delete=models.CASCADE
    )
    row_number = models.PositiveIntegerField()
    transaction_date = models.CharField(max_length=50)
    amount = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[('success', 'Success'), ('error', 'Error')]
    )
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Row {self.row_number}: {self.status}"
