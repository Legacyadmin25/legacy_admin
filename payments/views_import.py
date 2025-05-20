"""
Payment import views for EasyPay and Linkserv integration.
"""
import csv
import io
import json
import logging
import os
import pandas as pd
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator

from members.models import Member, Policy
from .models import Payment, PaymentImport, ImportRecord
from .forms import PaymentImportForm
from .utils.policy_utils import update_policy_status

logger = logging.getLogger(__name__)

def is_staff_or_admin(user):
    """Check if user is staff, admin, or superuser"""
    return user.is_staff or user.is_superuser or user.groups.filter(name__in=['Admin', 'Branch Manager']).exists()

@login_required
@user_passes_test(is_staff_or_admin)
def import_payments(request):
    """
    Unified payment import page for EasyPay, Debit Orders, and Bank Reconciliation.
    """
    if request.method == 'POST':
        # Get the import type from the form
        import_type = request.POST.get('import_type')
        
        # Create a new PaymentImport instance
        payment_import = PaymentImport(
            import_type=import_type,
            file=request.FILES.get('file'),
            notes=request.POST.get('notes', ''),
            imported_by=request.user
        )
        payment_import.save()
        
        # Process the import based on type
        if import_type == 'EASYPAY':
            messages.success(request, 'EasyPay file uploaded successfully. Processing has begun.')
            return redirect('payments:process_easypay_import', import_id=payment_import.id)
        elif import_type == 'LINKSERV':
            messages.success(request, 'Debit Order file uploaded successfully. Processing has begun.')
            return redirect('payments:process_linkserv_import', import_id=payment_import.id)
        elif import_type == 'BANK_RECONCILIATION':
            messages.success(request, 'Bank Reconciliation file uploaded successfully. Processing has begun.')
            # Redirect to the bank reconciliation processing view
            return redirect('payments:import_detail', import_id=payment_import.id)
        else:
            messages.warning(request, f'Unknown import type: {import_type}')
            return redirect('payments:import_payments')
    
    # Pre-select the import type if provided in the URL
    import_type = request.GET.get('type')
    initial_data = {}
    if import_type:
        if import_type == 'easypay':
            initial_data['import_type'] = 'EASYPAY'
        elif import_type == 'debit_orders':
            initial_data['import_type'] = 'LINKSERV'
        elif import_type == 'bank_reconciliation':
            initial_data['import_type'] = 'BANK_RECONCILIATION'
    
    # Get recent imports for each type
    recent_imports = PaymentImport.objects.order_by('-imported_at')[:15]
    
    context = {
        'recent_imports': recent_imports,
        'import_type': import_type,
    }
    return render(request, 'payments/import_payments.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def process_easypay_import(request, import_id):
    """
    Process an EasyPay import file.
    
    EasyPay format is typically:
    - Reference Number (EasyPay number)
    - Amount
    - Date
    - Transaction ID
    """
    payment_import = get_object_or_404(PaymentImport, pk=import_id)
    
    if payment_import.status != 'PENDING':
        messages.warning(request, f"This import has already been processed (status: {payment_import.get_status_display()}).")
        return redirect('payments:import_payments')
    
    # Update status to processing
    payment_import.status = 'PROCESSING'
    payment_import.save()
    
    try:
        # Read the file
        file_content = payment_import.file.read().decode('utf-8')
        
        # Determine if it's CSV or TXT
        if payment_import.file.name.endswith('.csv'):
            # Parse CSV
            reader = csv.reader(io.StringIO(file_content))
            rows = list(reader)
            # Skip header row if present
            if rows and any(header.lower() in rows[0][0].lower() for header in ['reference', 'amount', 'date']):
                rows = rows[1:]
        else:
            # Parse TXT (assuming tab or pipe delimited)
            delimiter = '|' if '|' in file_content else '\t'
            reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)
            rows = list(reader)
            # Skip header row if present
            if rows and any(header.lower() in rows[0][0].lower() for header in ['reference', 'amount', 'date']):
                rows = rows[1:]
        
        # Process rows
        total_records = len(rows)
        payment_import.total_records = total_records
        payment_import.save()
        
        matched_count = 0
        unmatched_count = 0
        
        for row in rows:
            # Extract data (adjust indices based on file format)
            if len(row) >= 3:
                reference = row[0].strip()
                try:
                    amount = float(row[1].replace('R', '').replace(',', '').strip())
                except (ValueError, IndexError):
                    amount = 0
                
                try:
                    date_str = row[2].strip()
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                        try:
                            payment_date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format worked, use today's date
                        payment_date = timezone.now().date()
                except (ValueError, IndexError):
                    payment_date = timezone.now().date()
                
                # Create import record
                import_record = ImportRecord(
                    payment_import=payment_import,
                    reference=reference,
                    identifier=reference,  # EasyPay number is the identifier
                    amount=amount,
                    date=payment_date,
                    raw_data=json.dumps(row)
                )
                
                # Try to match with a member
                member = None
                
                # First try to match by EasyPay number
                members = Member.objects.filter(
                    Q(easypay_number=reference) | 
                    Q(id_number=reference) |
                    Q(policies__policy_number=reference)
                )
                
                if members.exists():
                    member = members.first()
                    policy = member.policies.first() if hasattr(member, 'policies') else None
                    
                    # Create payment
                    payment = Payment.objects.create(
                        member=member,
                        policy=policy,
                        amount=amount,
                        date=payment_date,
                        payment_method='EASYPAY',
                        status='COMPLETED',
                        reference_number=reference,
                        notes=f"Imported from EasyPay file on {timezone.now().date()}",
                        created_by=request.user
                    )
                    
                    # Update import record
                    import_record.payment = payment
                    import_record.status = 'PROCESSED'
                    import_record.processed_at = timezone.now()
                    import_record.save()
                    
                    # Update policy status
                    if policy:
                        update_policy_status(policy)
                    
                    matched_count += 1
                else:
                    # No match found
                    import_record.status = 'UNMATCHED'
                    import_record.error_message = "No matching member found for this reference."
                    import_record.save()
                    unmatched_count += 1
            else:
                # Invalid row format
                import_record = ImportRecord(
                    payment_import=payment_import,
                    status='FAILED',
                    error_message="Invalid row format",
                    raw_data=json.dumps(row),
                    date=timezone.now().date(),
                    amount=0
                )
                import_record.save()
                unmatched_count += 1
        
        # Update import status
        payment_import.successful_records = matched_count
        payment_import.failed_records = unmatched_count
        payment_import.status = 'COMPLETED' if unmatched_count == 0 else 'PARTIAL'
        payment_import.processed_at = timezone.now()
        payment_import.save()
        
        messages.success(
            request, 
            f"Import completed: {matched_count} payments processed, {unmatched_count} unmatched records."
        )
        
    except Exception as e:
        logger.error(f"Error processing EasyPay import: {str(e)}")
        payment_import.status = 'FAILED'
        payment_import.notes = f"Error: {str(e)}"
        payment_import.save()
        messages.error(request, f"Error processing import: {str(e)}")
    
    return redirect('payments:import_detail', import_id=payment_import.id)

@login_required
@user_passes_test(is_staff_or_admin)
def process_bank_reconciliation_import(request, import_id):
    """
    Process a bank reconciliation import file.
    
    Bank reconciliation format typically includes:
    - Transaction Date
    - Description
    - Reference
    - Amount
    """
    payment_import = get_object_or_404(PaymentImport, pk=import_id)
    
    if payment_import.status != 'PENDING':
        messages.warning(request, f"This import has already been processed (status: {payment_import.get_status_display()}).")
        return redirect('payments:import_payments')
    
    # Update status to processing
    payment_import.status = 'PROCESSING'
    payment_import.save()
    
    try:
        # Read the file
        file_extension = os.path.splitext(payment_import.file.name)[1].lower()
        
        if file_extension in ['.csv', '.txt']:
            # Read CSV file
            file_content = payment_import.file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(file_content))
            rows = list(reader)
            # Skip header row if present
            if rows and any(header.lower() in str(rows[0]).lower() for header in ['date', 'description', 'reference', 'amount']):
                headers = rows[0]
                rows = rows[1:]
            else:
                headers = ['Date', 'Description', 'Reference', 'Amount']
        elif file_extension in ['.xls', '.xlsx']:
            # Read Excel file
            df = pd.read_excel(payment_import.file)
            headers = df.columns.tolist()
            rows = df.values.tolist()
        else:
            messages.error(request, f"Unsupported file format: {file_extension}")
            payment_import.status = 'FAILED'
            payment_import.save()
            return redirect('payments:import_detail', import_id=payment_import.id)
        
        # Find column indices
        date_col = next((i for i, h in enumerate(headers) if 'date' in str(h).lower()), 0)
        desc_col = next((i for i, h in enumerate(headers) if 'desc' in str(h).lower()), 1)
        ref_col = next((i for i, h in enumerate(headers) if 'ref' in str(h).lower()), 2)
        amount_col = next((i for i, h in enumerate(headers) if 'amount' in str(h).lower()), 3)
        
        # Process rows
        total_rows = len(rows)
        matched_count = 0
        unmatched_count = 0
        
        for row in rows:
            if len(row) <= max(date_col, desc_col, ref_col, amount_col):
                continue  # Skip rows with insufficient columns
            
            try:
                # Extract data
                try:
                    if isinstance(row[date_col], str):
                        transaction_date = datetime.strptime(row[date_col], '%Y-%m-%d').date()
                    else:
                        transaction_date = row[date_col].date() if hasattr(row[date_col], 'date') else datetime.now().date()
                except (ValueError, AttributeError):
                    transaction_date = datetime.now().date()
                
                description = str(row[desc_col]) if row[desc_col] else ''
                reference = str(row[ref_col]) if row[ref_col] else ''
                
                # Clean and parse amount
                amount_str = str(row[amount_col]).replace(',', '').strip()
                try:
                    amount = float(amount_str)
                except ValueError:
                    # Try to extract numeric value from string with currency symbols
                    import re
                    amount_match = re.search(r'[\d.,]+', amount_str)
                    if amount_match:
                        amount = float(amount_match.group().replace(',', ''))
                    else:
                        amount = 0.0
                
                # Skip zero or negative amounts
                if amount <= 0:
                    continue
                
                # Look for policy reference in reference or description
                policy_ref = reference
                if not policy_ref or len(policy_ref) < 4:
                    # Try to extract policy number from description
                    import re
                    ref_match = re.search(r'\b([A-Z0-9]{5,})\b', description)
                    if ref_match:
                        policy_ref = ref_match.group(1)
                
                # Create import record
                record = ImportRecord(
                    import_log=payment_import,
                    reference=policy_ref,
                    amount=amount,
                    transaction_date=transaction_date,
                    raw_data=json.dumps({
                        'date': str(row[date_col]),
                        'description': description,
                        'reference': reference,
                        'amount': amount_str
                    })
                )
                
                # Try to match to a policy
                if policy_ref and len(policy_ref) >= 4:
                    policies = Policy.objects.filter(
                        Q(policy_number__iexact=policy_ref) | 
                        Q(membership_number__iexact=policy_ref)
                    )
                    
                    if policies.exists():
                        policy = policies.first()
                        record.status = 'MATCHED'
                        record.save()
                        
                        # Create payment
                        payment = Payment(
                            policy=policy,
                            amount=amount,
                            payment_date=transaction_date,
                            payment_method='BANK_TRANSFER',
                            reference=reference,
                            notes=f"Imported from bank reconciliation: {description}",
                            created_by=request.user,
                            import_record=record
                        )
                        payment.save()
                        
                        # Update policy status if needed
                        update_policy_status(policy)
                        
                        matched_count += 1
                    else:
                        record.status = 'UNMATCHED'
                        record.error_message = 'No policy found with this reference number'
                        record.save()
                        unmatched_count += 1
                else:
                    record.status = 'UNMATCHED'
                    record.error_message = 'Invalid or missing policy reference'
                    record.save()
                    unmatched_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing bank reconciliation row: {str(e)}")
                record = ImportRecord(
                    import_log=payment_import,
                    reference=reference if 'reference' in locals() else '',
                    amount=amount if 'amount' in locals() else 0,
                    transaction_date=transaction_date if 'transaction_date' in locals() else datetime.now().date(),
                    status='ERROR',
                    error_message=str(e),
                    raw_data=json.dumps(row) if isinstance(row, list) else str(row)
                )
                record.save()
                unmatched_count += 1
        
        # Update import status
        payment_import.total_records = total_rows
        payment_import.matched_records = matched_count
        payment_import.failed_records = unmatched_count
        payment_import.status = 'COMPLETED'
        payment_import.save()
        
        messages.success(request, f"Bank reconciliation import completed: {matched_count} matched, {unmatched_count} unmatched records.")
        
    except Exception as e:
        logger.error(f"Error processing bank reconciliation import: {str(e)}")
        payment_import.status = 'FAILED'
        payment_import.error_message = str(e)
        payment_import.save()
        messages.error(request, f"Error processing bank reconciliation import: {str(e)}")
    
    return redirect('payments:import_detail', import_id=payment_import.id)


@login_required
@user_passes_test(is_staff_or_admin)
def process_linkserv_import(request, import_id):
    """
    Process a Linkserv debit order import file.
    
    Linkserv format is typically Excel with:
    - Account Holder
    - Account Number
    - Bank
    - Branch Code
    - Amount
    - Status (Success/Failed)
    - Reference/Policy Number
    """
    payment_import = get_object_or_404(PaymentImport, pk=import_id)
    
    if payment_import.status != 'PENDING':
        messages.warning(request, f"This import has already been processed (status: {payment_import.get_status_display()}).")
        return redirect('payments:import_payments')
    
    # Update status to processing
    payment_import.status = 'PROCESSING'
    payment_import.save()
    
    try:
        # Read Excel file
        df = pd.read_excel(payment_import.file)
        
        # Process rows
        total_records = len(df)
        payment_import.total_records = total_records
        payment_import.save()
        
        matched_count = 0
        unmatched_count = 0
        
        # Determine column names (they might vary)
        reference_col = next((col for col in df.columns if 'reference' in col.lower() or 'policy' in col.lower()), None)
        amount_col = next((col for col in df.columns if 'amount' in col.lower()), None)
        status_col = next((col for col in df.columns if 'status' in col.lower() or 'result' in col.lower()), None)
        
        if not (reference_col and amount_col):
            raise ValueError("Could not identify required columns in the Excel file.")
        
        for _, row in df.iterrows():
            # Extract data
            reference = str(row[reference_col]).strip() if reference_col else ""
            
            try:
                amount = float(str(row[amount_col]).replace('R', '').replace(',', '').strip()) if amount_col else 0
            except ValueError:
                amount = 0
                
            status = str(row[status_col]).lower() if status_col else "success"
            payment_status = 'COMPLETED' if 'success' in status else 'FAILED'
            
            payment_date = timezone.now().date()
            
            # Create import record
            import_record = ImportRecord(
                payment_import=payment_import,
                reference=reference,
                identifier=reference,
                amount=amount,
                date=payment_date,
                raw_data=row.to_json()
            )
            
            # Only process successful payments
            if payment_status == 'COMPLETED':
                # Try to match with a member
                members = Member.objects.filter(
                    Q(policies__policy_number=reference) | 
                    Q(id_number=reference)
                )
                
                if members.exists():
                    member = members.first()
                    policy = member.policies.first() if hasattr(member, 'policies') else None
                    
                    # Create payment
                    payment = Payment.objects.create(
                        member=member,
                        policy=policy,
                        amount=amount,
                        date=payment_date,
                        payment_method='DEBIT_ORDER',
                        status='COMPLETED',
                        reference_number=reference,
                        notes=f"Imported from Linkserv debit order file on {timezone.now().date()}",
                        created_by=request.user
                    )
                    
                    # Update import record
                    import_record.payment = payment
                    import_record.status = 'PROCESSED'
                    import_record.processed_at = timezone.now()
                    import_record.save()
                    
                    # Update policy status
                    if policy:
                        update_policy_status(policy)
                    
                    matched_count += 1
                else:
                    # No match found
                    import_record.status = 'UNMATCHED'
                    import_record.error_message = "No matching member found for this reference."
                    import_record.save()
                    unmatched_count += 1
            else:
                # Failed debit order
                members = Member.objects.filter(
                    Q(policies__policy_number=reference) | 
                    Q(id_number=reference)
                )
                
                if members.exists():
                    member = members.first()
                    policy = member.policies.first() if hasattr(member, 'policies') else None
                    
                    # Create payment record for failed debit
                    payment = Payment.objects.create(
                        member=member,
                        policy=policy,
                        amount=amount,
                        date=payment_date,
                        payment_method='DEBIT_ORDER',
                        status='FAILED',
                        reference_number=reference,
                        notes=f"Failed debit order imported from Linkserv file on {timezone.now().date()}",
                        created_by=request.user
                    )
                    
                    # Update import record
                    import_record.payment = payment
                    import_record.status = 'FAILED'
                    import_record.error_message = "Debit order failed"
                    import_record.processed_at = timezone.now()
                    import_record.save()
                    
                    # Update policy status (may mark as lapsed)
                    if policy:
                        update_policy_status(policy)
                    
                    unmatched_count += 1
                else:
                    # No match found for failed debit
                    import_record.status = 'UNMATCHED'
                    import_record.error_message = "Failed debit order with no matching member."
                    import_record.save()
                    unmatched_count += 1
        
        # Update import status
        payment_import.successful_records = matched_count
        payment_import.failed_records = unmatched_count
        payment_import.status = 'COMPLETED' if unmatched_count == 0 else 'PARTIAL'
        payment_import.processed_at = timezone.now()
        payment_import.save()
        
        messages.success(
            request, 
            f"Import completed: {matched_count} payments processed, {unmatched_count} failed/unmatched records."
        )
        
    except Exception as e:
        logger.error(f"Error processing Linkserv import: {str(e)}")
        payment_import.status = 'FAILED'
        payment_import.notes = f"Error: {str(e)}"
        payment_import.save()
        messages.error(request, f"Error processing import: {str(e)}")
    
    return redirect('payments:import_detail', import_id=payment_import.id)

@login_required
@user_passes_test(is_staff_or_admin)
def import_detail(request, import_id):
    """
    Show details of a payment import, including matched and unmatched records.
    """
    payment_import = get_object_or_404(PaymentImport, pk=import_id)
    
    # Get records with pagination
    matched_records = ImportRecord.objects.filter(
        payment_import=payment_import, 
        status__in=['PROCESSED', 'MATCHED']
    ).order_by('-processed_at')
    
    unmatched_records = ImportRecord.objects.filter(
        payment_import=payment_import, 
        status__in=['UNMATCHED', 'FAILED']
    ).order_by('-processed_at')
    
    context = {
        'payment_import': payment_import,
        'matched_records': matched_records,
        'unmatched_records': unmatched_records,
    }
    return render(request, 'payments/import_detail.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
@transaction.atomic
def process_unmatched_record(request, record_id):
    """
    Process an unmatched import record manually.
    Allows admins to match a payment record to a member and create a payment.
    """
    record = get_object_or_404(ImportRecord, pk=record_id, status__in=['UNMATCHED', 'FAILED'])
    
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        payment_method = request.POST.get('payment_method')
        payment_status = request.POST.get('payment_status', 'COMPLETED')
        payment_notes = request.POST.get('payment_notes', '')
        
        if not member_id:
            messages.error(request, "Please select a member to process this payment.")
            return redirect('payments:import_detail', import_id=record.payment_import.id)
        
        try:
            # Get the member and their active policy
            member = Member.objects.get(pk=member_id)
            
            # Try to get an active policy first
            try:
                policy = Policy.objects.get(member=member, status='ACTIVE')
            except Policy.DoesNotExist:
                # If no active policy, try to get any policy
                policy = member.policies.first() if hasattr(member, 'policies') else None
                
                if not policy:
                    messages.warning(request, f"No active policy found for {member}. Payment processed but policy status not updated.")
            
            # Set default payment method based on import type if not provided
            if not payment_method:
                payment_method = 'DEBIT_ORDER' if record.payment_import.import_type == 'LINKSERV' else 'EASYPAY'
            
            # Create payment with enhanced details
            payment = Payment.objects.create(
                member=member,
                policy=policy,
                amount=record.amount,
                date=record.date,
                payment_method=payment_method,
                status=payment_status,
                reference_number=record.reference,
                notes=f"Manually matched from import #{record.payment_import.id}. {payment_notes}",
                created_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Create payment receipt if payment is completed
            if payment_status == 'COMPLETED':
                try:
                    from .utils import generate_receipt_number
                    receipt_number = generate_receipt_number()
                    
                    PaymentReceipt.objects.create(
                        payment=payment,
                        receipt_number=receipt_number,
                        issued_by=request.user,
                        issued_date=timezone.now()
                    )
                    
                    logger.info(f"Receipt {receipt_number} generated for manually matched payment {payment.id}")
                except Exception as receipt_error:
                    logger.error(f"Failed to generate receipt for payment {payment.id}: {str(receipt_error)}")
            
            # Update import record status
            record.payment = payment
            record.status = 'MANUAL'
            record.error_message = ''
            record.processed_at = timezone.now()
            record.processed_by = request.user
            record.save()
            
            # Update policy status if we have a policy
            if policy:
                update_policy_status(policy)
            
            # Update import counts
            payment_import = record.payment_import
            payment_import.successful_records += 1
            payment_import.failed_records -= 1
            payment_import.save()
            
            # Log the action
            logger.info(f"User {request.user} manually matched payment record {record_id} to member {member_id}")
            
            messages.success(
                request, 
                f"Payment of R{record.amount} successfully processed for {member.first_name} {member.last_name}."
            )
            
        except Member.DoesNotExist:
            messages.error(request, "Member not found. Please try again with a valid member.")
        except Exception as e:
            logger.error(f"Error processing unmatched record {record_id}: {str(e)}")
            messages.error(request, f"Error processing payment: {str(e)}")
    
    return redirect('payments:import_detail', import_id=record.payment_import.id)
