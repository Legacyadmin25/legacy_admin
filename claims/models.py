from django.db import models
from django.utils import timezone
from members.models import Member
from payments.models import Payment


class Claim(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    claim_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    document = models.FileField(upload_to='claim_docs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    submitted_date = models.DateTimeField(auto_now_add=True)
    payments = models.ManyToManyField(Payment, related_name='claims', blank=True)
    
    # Audit fields
    _original_status = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original status for change detection
        self._original_status = self.status
    
    def __str__(self):
        return f"Claim {self.id} - {self.member.first_name} {self.member.last_name} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """Save claim and log status changes to audit trail"""
        super().save(*args, **kwargs)
        
        # Log status changes for audit trail
        if self._original_status and self._original_status != self.status:
            from audit.operations import audit_claim_status_change
            from audit.middleware import get_request_context
            request = get_request_context()
            user = request.user if request and hasattr(request, 'user') else None
            
            audit_claim_status_change(
                self,
                old_status=self._original_status,
                new_status=self.status,
                user=user,
                reason='Status updated through admin or API'
            )
            self._original_status = self.status
        
    def is_recent(self):
        """Check if claim was submitted in the last 30 days"""
        return (timezone.now() - self.submitted_date).days <= 30
