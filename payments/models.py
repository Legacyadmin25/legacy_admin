from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from members.models import Member, Policy
import uuid
import json

# Get the custom User model
User = get_user_model()

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CHECK', 'Check'),
        ('CREDIT', 'Credit Card'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('DEBIT_ORDER', 'Debit Order'),
        ('EASYPAY', 'EasyPay'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in decimal"
    )
    date = models.DateField(
        help_text="Date when payment was made"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        help_text="Method used for payment"
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='COMPLETED',
        help_text="Current status of the payment"
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="External reference number (e.g., EasyPay or bank reference)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional payment notes"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_payments',
        help_text="User who created this payment record"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_payments',
        help_text="User who last updated this payment record"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When payment record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        help_text="When payment record was last updated"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user who created/updated this payment"
    )

    class Meta:
        ordering = ['-date']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['member']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"Payment #{self.id} - {self.member} (${self.amount})"

class PaymentReceipt(models.Model):
    RECEIPT_STATUS = [
        ('GENERATED', 'Generated'),
        ('PRINTED', 'Printed'),
        ('EMAILED', 'Emailed'),
        ('WHATSAPP', 'Sent via WhatsApp'),
        ('DOWNLOADED', 'Downloaded'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='receipts')
    receipt_number = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=RECEIPT_STATUS,
        default='GENERATED',
        help_text="Current status of the receipt"
    )
    pdf_file = models.FileField(
        upload_to='receipts/',
        null=True,
        blank=True,
        help_text="PDF version of the receipt"
    )
    sent_to = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email or phone number where receipt was sent"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the receipt was sent"
    )
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_receipts',
        help_text="User who sent this receipt"
    )
    
    def __str__(self):
        return f"Receipt for Payment #{self.payment.id} - {self.receipt_number}"
        
    def generate_pdf(self):
        """Generate PDF receipt"""
        # This will be implemented later
        pass
        
    def send_email(self, email):
        """Send receipt via email"""
        # This will be implemented later
        pass
        
    def send_whatsapp(self, phone_number):
        """Send receipt via WhatsApp"""
        # This will be implemented later
        pass


class PaymentImport(models.Model):
    IMPORT_TYPES = [
        ('EASYPAY', 'EasyPay Import'),
        ('LINKSERV', 'Linkserv Debit Order Import'),
        ('OTHER', 'Other Import'),
    ]
    
    IMPORT_STATUS = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partially Completed'),
    ]
    
    import_type = models.CharField(
        max_length=20,
        choices=IMPORT_TYPES,
        help_text="Type of payment import"
    )
    file = models.FileField(
        upload_to='payment_imports/',
        help_text="Imported file (CSV, TXT, or Excel)"
    )
    status = models.CharField(
        max_length=20,
        choices=IMPORT_STATUS,
        default='PENDING',
        help_text="Current status of the import"
    )
    imported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payment_imports',
        help_text="User who imported this file"
    )
    imported_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the file was imported"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the import was processed"
    )
    total_records = models.IntegerField(
        default=0,
        help_text="Total number of records in the import"
    )
    successful_records = models.IntegerField(
        default=0,
        help_text="Number of successfully processed records"
    )
    failed_records = models.IntegerField(
        default=0,
        help_text="Number of failed records"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the import"
    )
    
    def __str__(self):
        return f"{self.get_import_type_display()} - {self.imported_at.strftime('%Y-%m-%d')}"


class ImportRecord(models.Model):
    RECORD_STATUS = [
        ('PENDING', 'Pending'),
        ('MATCHED', 'Matched'),
        ('UNMATCHED', 'Unmatched'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
        ('MANUAL', 'Manually Processed'),
    ]
    
    payment_import = models.ForeignKey(
        PaymentImport,
        on_delete=models.CASCADE,
        related_name='records',
        help_text="The import this record belongs to"
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_records',
        help_text="The payment created from this record (if any)"
    )
    status = models.CharField(
        max_length=20,
        choices=RECORD_STATUS,
        default='PENDING',
        help_text="Current status of this import record"
    )
    reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Reference number from the import"
    )
    identifier = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Member identifier (ID, policy number, EasyPay number)"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in the import"
    )
    date = models.DateField(
        help_text="Date of the payment in the import"
    )
    raw_data = models.JSONField(
        help_text="Raw data from the import file"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if processing failed"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this record was processed"
    )
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_import_records',
        help_text="User who processed this record (if manual)"
    )
    
    def __str__(self):
        return f"Import Record {self.id} - {self.reference or 'No Reference'}"


# Import logging models
IMPORT_TYPES = [
    ('EASYPAY', 'EasyPay'),
    ('LINKSERV', 'Linkserv Debit Order'),
    ('AGENT', 'Agent Onboarding'),
    ('BANK', 'Bank Reconciliation'),
    ('AMENDMENT', 'Policy Amendments'),
    ('REACTIVATION', 'Policy Reactivations'),
    ('OTHER', 'Other Import'),
]

IMPORT_STATUS = [
    ('PENDING', 'Pending'),
    ('PROCESSING', 'Processing'),
    ('COMPLETED', 'Completed'),
    ('PARTIAL', 'Partially Completed'),
    ('FAILED', 'Failed'),
]

ROW_STATUS = [
    ('SUCCESS', 'Success'),
    ('ERROR', 'Error'),
    ('UNMATCHED', 'Unmatched'),
    ('FIXED', 'Manually Fixed'),
    ('PENDING', 'Pending'),
]


class ImportLog(models.Model):
    """
    Logs information about file imports for auditing and tracking.
    """
    file_name = models.CharField(max_length=255)
    import_type = models.CharField(max_length=20, choices=IMPORT_TYPES)
    status = models.CharField(max_length=20, choices=IMPORT_STATUS, default='PENDING')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='imports')
    imported_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    total_records = models.PositiveIntegerField(default=0)
    successful_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    error_file = models.FileField(upload_to='import_errors/', null=True, blank=True)
    
    class Meta:
        ordering = ['-imported_at']
        verbose_name = 'Import Log'
        verbose_name_plural = 'Import Logs'
    
    def __str__(self):
        return f"{self.get_import_type_display()} - {self.file_name} ({self.imported_at.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def success_rate(self):
        if self.total_records == 0:
            return 0
        return (self.successful_records / self.total_records) * 100
    
    @property
    def has_errors(self):
        return self.failed_records > 0


class RowLog(models.Model):
    """
    Logs information about individual rows in an import file.
    """
    import_log = models.ForeignKey(ImportLog, on_delete=models.CASCADE, related_name='rows')
    row_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ROW_STATUS)
    data = models.TextField()  # JSON or string representation of the row data
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fixed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='fixed_rows')
    
    class Meta:
        ordering = ['row_number']
        verbose_name = 'Row Log'
        verbose_name_plural = 'Row Logs'
    
    def __str__(self):
        return f"Row {self.row_number} - {self.status}"


class AIRequestLog(models.Model):
    """Logs information about AI requests for auditing and compliance."""
    REQUEST_TYPES = [
        ('payment_summary', 'Payment Summary'),
        ('policy_summary', 'Policy Summary'),
        ('scheme_summary', 'Scheme Summary'),
        ('agent_summary', 'Agent Summary'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payment_ai_requests')
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPES)
    policy = models.ForeignKey(Policy, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_requests')
    scheme = models.ForeignKey('schemes.Scheme', on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_requests')
    agent = models.ForeignKey('settings_app.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_requests')
    prompt_data = models.TextField(help_text="Anonymized data sent to AI service")
    response_data = models.TextField(help_text="Response received from AI service")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI Request Log'
        verbose_name_plural = 'AI Request Logs'
    
    def __str__(self):
        return f"{self.request_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_prompt_data_json(self):
        """Returns the prompt data as a JSON object"""
        try:
            return json.loads(self.prompt_data)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON data"}
    
    def get_summary_text(self):
        """Returns the AI-generated summary text"""
        return self.response_data
