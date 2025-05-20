"""
Utility functions for policy-related operations.
"""
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F
from django.core.exceptions import ValidationError

from payments.models import Payment
from members.models import Policy

def update_policy_status(policy):
    """
    Update the status of a policy based on its payments.
    
    Args:
        policy: The Policy instance to update
        
    Returns:
        bool: True if the status was updated, False otherwise
    """
    if not policy:
        return False
        
    try:
        with transaction.atomic():
            # Get total paid amount for the policy
            total_paid = Payment.objects.filter(
                policy=policy,
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Update the policy's paid amount
            policy.total_paid = total_paid
            
            # Calculate outstanding balance
            policy.outstanding_balance = max(0, policy.premium - total_paid)
            
            # Update status based on payments
            if total_paid >= policy.premium:
                policy.status = 'ACTIVE'
            elif policy.status == 'PENDING' and total_paid > 0:
                policy.status = 'ACTIVE'
            elif policy.status == 'ACTIVE' and total_paid < policy.premium:
                policy.status = 'LAPSED'
                
            policy.last_updated = timezone.now()
            policy.save(update_fields=[
                'total_paid', 
                'outstanding_balance', 
                'status', 
                'last_updated'
            ])
            return True
            
    except Exception as e:
        # Log the error and return False
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating policy {policy.id} status: {str(e)}")
        return False

def calculate_outstanding_balance(policy):
    """
    Calculate the outstanding balance for a policy.
    
    Args:
        policy: The Policy instance
        
    Returns:
        float: The outstanding balance
    """
    if not policy:
        return 0.0
        
    try:
        total_paid = Payment.objects.filter(
            policy=policy,
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return max(0, policy.premium - total_paid)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error calculating outstanding balance for policy {policy.id}: {str(e)}")
        return 0.0
