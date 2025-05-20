"""
Payment utilities for managing payments, policy status updates, receipt generation, and import logging.
"""
import logging
import csv
import os
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Max
from django.conf import settings
from django.core.files.base import ContentFile
from members.models import Policy
from .models import ImportLog, RowLog

logger = logging.getLogger(__name__)

def update_policy_status(policy):
    """
    Update a policy's status based on payment activity.
    
    Rules:
    - If payment is overdue > X days → mark as "Lapsed"
    - If payment is within grace period → show "On Trial"
    - Otherwise → "Active"
    
    Returns:
    - The updated policy object
    """
    try:
        # Default grace period is 30 days, but can be configured in settings
        grace_period_days = getattr(settings, 'PAYMENT_GRACE_PERIOD_DAYS', 30)
        
        # Get the last payment date
        last_payment = policy.payments.filter(status='COMPLETED').order_by('-date').first()
        
        if not last_payment:
            # No payments yet, check if policy is new (within grace period)
            if policy.start_date:
                days_since_start = (timezone.now().date() - policy.start_date).days
                if days_since_start <= grace_period_days:
                    policy.status = 'trial'
                    policy.lapse_reason = None
                else:
                    policy.status = 'lapsed'
                    policy.lapse_reason = 'No payments received'
            else:
                policy.status = 'lapsed'
                policy.lapse_reason = 'No start date or payments'
        else:
            # Calculate days since last payment
            days_since_payment = (timezone.now().date() - last_payment.date).days
            
            # Update policy based on days since last payment
            if days_since_payment > grace_period_days:
                policy.status = 'lapsed'
                policy.lapse_reason = f'Payment overdue by {days_since_payment - grace_period_days} days'
            elif days_since_payment > 0:
                policy.status = 'trial'
                policy.lapse_reason = None
            else:
                policy.status = 'active'
                policy.lapse_reason = None
                
        # Save the updated policy
        policy.last_payment_date = last_payment.date if last_payment else None
        policy.last_payment_amount = last_payment.amount if last_payment else None
        policy.save(update_fields=['status', 'lapse_reason', 'last_payment_date', 'last_payment_amount'])
        
        logger.info(f"Updated policy {policy.id} status to {policy.status}")
        return policy
        
    except Exception as e:
        logger.error(f"Error updating policy status: {str(e)}")
        return policy

def calculate_outstanding_balance(policy):
    """
    Calculate the outstanding balance for a policy.
    
    Returns:
    - The outstanding balance (can be negative if overpaid)
    """
    try:
        if not policy.premium:
            return 0
            
        # Get the total amount paid
        total_paid = policy.payments.filter(status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate expected payments based on start date
        if not policy.start_date:
            return 0
            
        months_active = (timezone.now().date().year - policy.start_date.year) * 12
        months_active += timezone.now().date().month - policy.start_date.month
        
        # If we're past the payment day in the current month, add one more month
        if hasattr(policy, 'payment_day') and policy.payment_day and timezone.now().date().day >= policy.payment_day:
            months_active += 1
            
        expected_total = months_active * policy.premium
        
        # Calculate outstanding balance
        outstanding = expected_total - total_paid
        
        return outstanding
    except Exception as e:
        logger.error(f"Error calculating outstanding balance: {str(e)}")
        return 0


def create_import_log(file_name, import_type, user, total_records=0, successful_records=0, failed_records=0, notes=None):
    """
    Create an import log entry.
    
    Args:
        file_name: Name of the imported file
        import_type: Type of import (EASYPAY, LINKSERV, etc.)
        user: User who performed the import
        total_records: Total number of records in the import
        successful_records: Number of successfully processed records
        failed_records: Number of failed records
        notes: Additional notes about the import
        
    Returns:
        The created ImportLog instance
    """
    try:
        import_log = ImportLog.objects.create(
            file_name=file_name,
            import_type=import_type,
            user=user,
            total_records=total_records,
            successful_records=successful_records,
            failed_records=failed_records,
            notes=notes
        )
        logger.info(f"Created import log: {import_log.id} for {file_name}")
        return import_log
    except Exception as e:
        logger.error(f"Error creating import log: {str(e)}")
        return None


def create_row_log(import_log, row_number, status, data, error_message=None):
    """
    Create a row log entry for a specific row in an import.
    
    Args:
        import_log: The ImportLog instance this row belongs to
        row_number: Row number in the import file
        status: Status of the row (SUCCESS, ERROR, UNMATCHED)
        data: The data from the row (as JSON or string)
        error_message: Error message if status is ERROR or UNMATCHED
        
    Returns:
        The created RowLog instance
    """
    try:
        row_log = RowLog.objects.create(
            import_log=import_log,
            row_number=row_number,
            status=status,
            data=data,
            error_message=error_message
        )
        return row_log
    except Exception as e:
        logger.error(f"Error creating row log: {str(e)}")
        return None


def generate_error_csv(import_log):
    """
    Generate a CSV file with error details for failed rows.
    
    Args:
        import_log: The ImportLog instance to generate the error CSV for
        
    Returns:
        The URL to the generated CSV file, or None if no errors
    """
    try:
        # Get all error rows for this import
        error_rows = RowLog.objects.filter(import_log=import_log, status__in=['ERROR', 'UNMATCHED'])
        
        if not error_rows.exists():
            return None
            
        # Create CSV content
        csv_content = []
        
        # Add header row
        header = ['Row Number', 'Status', 'Error Message', 'Data']
        csv_content.append(header)
        
        # Add error rows
        for row in error_rows:
            csv_content.append([row.row_number, row.get_status_display(), row.error_message, row.data])
        
        # Generate CSV file
        filename = f"error_log_{import_log.id}_{uuid.uuid4().hex[:8]}.csv"
        csv_file = ContentFile(b'')
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            
        # Read the file and save to import_log.error_file
        with open(filename, 'rb') as f:
            import_log.error_file.save(filename, ContentFile(f.read()))
            
        # Delete the temporary file
        if os.path.exists(filename):
            os.remove(filename)
            
        import_log.save()
        return import_log.error_file.url
        
    except Exception as e:
        logger.error(f"Error generating error CSV: {str(e)}")
        return None


def update_row_status(row_log, new_status, error_message=None):
    """
    Update the status of a row log entry.
    
    Args:
        row_log: The RowLog instance to update
        new_status: The new status (SUCCESS, ERROR, UNMATCHED, FIXED)
        error_message: New error message if applicable
        
    Returns:
        The updated RowLog instance
    """
    try:
        row_log.status = new_status
        if error_message is not None:
            row_log.error_message = error_message
        row_log.updated_at = timezone.now()
        row_log.save()
        
        # Update the import log counts
        import_log = row_log.import_log
        successful_count = RowLog.objects.filter(import_log=import_log, status='SUCCESS').count()
        error_count = RowLog.objects.filter(import_log=import_log, status__in=['ERROR', 'UNMATCHED']).count()
        
        import_log.successful_records = successful_count
        import_log.failed_records = error_count
        import_log.save()
        
        return row_log
    except Exception as e:
        logger.error(f"Error updating row status: {str(e)}")
        return row_log

def generate_payment_summary_for_ai(policy):
    """
    Generate a payment summary for the AI tab.
    
    Returns:
    - A string with payment summary information
    """
    try:
        # Get payment history
        payments = policy.payments.filter(status='COMPLETED').order_by('-date')
        
        if not payments.exists():
            return "No payment history available for this policy."
            
        # Get last payment
        last_payment = payments.first()
        
        # Count payments in the last 6 months
        six_months_ago = timezone.now().date() - timedelta(days=180)
        recent_payments = payments.filter(date__gte=six_months_ago).count()
        
        # Calculate payment consistency
        total_expected = 6  # We expect 6 monthly payments in 6 months
        consistency_percentage = min(100, int((recent_payments / total_expected) * 100))
        
        # Generate consistency message
        if consistency_percentage == 100:
            consistency_msg = "Member has paid consistently for the last 6 months."
        elif consistency_percentage >= 80:
            consistency_msg = f"Member has paid {consistency_percentage}% consistently over the last 6 months."
        elif consistency_percentage >= 50:
            consistency_msg = f"Member has made {recent_payments} out of 6 expected payments in the last 6 months."
        else:
            consistency_msg = f"Member has missed several payments, with only {recent_payments} payments in the last 6 months."
        
        # Get payment method info
        payment_methods = {}
        for payment in payments[:6]:  # Look at last 6 payments
            method = payment.get_payment_method_display()
            payment_methods[method] = payment_methods.get(method, 0) + 1
            
        most_common_method = max(payment_methods.items(), key=lambda x: x[1])[0] if payment_methods else "Unknown"
        
        # Format the summary
        summary = f"{consistency_msg} "
        summary += f"Last payment of R{last_payment.amount} was made via {last_payment.get_payment_method_display()} on {last_payment.date.strftime('%d %b %Y')}. "
        
        # Add outstanding balance info
        outstanding = calculate_outstanding_balance(policy)
        if outstanding > 0:
            summary += f"Outstanding balance: R{outstanding:.2f}."
        elif outstanding < 0:
            summary += f"Account is in credit by R{abs(outstanding):.2f}."
        else:
            summary += "Account is fully paid up to date."
            
        return summary
        
    except Exception as e:
        logger.error(f"Error generating payment summary for AI: {str(e)}")
        return "Unable to generate payment summary due to an error."
