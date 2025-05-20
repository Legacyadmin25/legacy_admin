# payments/views.py

import uuid
import logging
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum, Count
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import DetailView, UpdateView, DeleteView, ListView
import calendar

from members.models import Member, Policy
from payments.models import Payment, PaymentReceipt, PaymentImport, ImportRecord
from .forms import PaymentForm, PaymentReceiptForm, PaymentFilterForm, PaymentImportForm
from .utils import (
    update_policy_status, 
    calculate_outstanding_balance,
    get_payment_summary_for_member,
    create_payment_receipt, 
    send_receipt_email, 
    get_whatsapp_link
)

logger = logging.getLogger(__name__)

@login_required
def policy_payment(request):
    query = request.GET.get('q', '').strip()
    member = policy = None
    payment_history = []
    payment_form = PaymentForm(prefix='payment')
    receipt_form = PaymentReceiptForm(prefix='receipt')
    success_message = error_message = None
    outstanding_balance = 0
    last_payment = None
    receipt = None
    show_receipt_modal = False
    ai_summary = None
    avg_payment = None
    plan_premium = None
    allow_override = request.user.is_superuser

    if query:
        # Try to find the member by name, ID or policy number
        member = Member.objects.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(id_number__icontains=query)
            | Q(policies__policy_number__icontains=query)
        ).first()

        if not member:
            error_message = "No member found for the given search criteria."
        else:
            # Try to load their policy
            try:
                policy = Policy.objects.get(member=member)
                
                # Calculate outstanding balance
                outstanding_balance = calculate_outstanding_balance(policy)
                
                # Get last payment
                last_payment = Payment.objects.filter(
                    member=member, 
                    status='COMPLETED'
                ).order_by('-date').first()
                
                # Get plan premium for auto-fill
                if policy and policy.plan:
                    plan_premium = policy.plan.premium
                
                # Get AI-powered payment summary for eligible roles
                user_groups = [group.name for group in request.user.groups.all()]
                if request.user.is_superuser or any(role in user_groups for role in ['Internal Admin', 'Branch Owner', 'Scheme Manager']):
                    ai_summary = get_payment_summary_for_member(member, request.user)
                
                # Calculate average payment for the last 6 months
                start_date = timezone.now().date() - timedelta(days=180)
                recent_payments = Payment.objects.filter(
                    member=member,
                    date__gte=start_date,
                    status='COMPLETED'
                )
                if recent_payments.exists():
                    avg_payment = recent_payments.aggregate(Avg('amount'))['amount__avg']
                
            except Policy.DoesNotExist:
                error_message = "No policy found for that member."
            else:
                # Load existing payments with pagination
                all_payments = Payment.objects.filter(member=member).order_by('-date')
                paginator = Paginator(all_payments, 25)  # Show 25 payments per page
                page_number = request.GET.get('page', 1)
                payment_history = paginator.get_page(page_number)

                # Handle payment form submission
                if request.method == 'POST':
                    if 'submit_payment' in request.POST:
                        payment_form = PaymentForm(request.POST, prefix='payment')
                        if payment_form.is_valid():
                            # Check for duplicate payments
                            amount = payment_form.cleaned_data['amount']
                            date = payment_form.cleaned_data['date']
                            method = payment_form.cleaned_data['payment_method']
                            
                            # Check for recent duplicate payments (same amount, date, and method)
                            recent_duplicates = Payment.objects.filter(
                                member=member,
                                amount=amount,
                                date=date,
                                payment_method=method
                            ).exists()
                            
                            if recent_duplicates and 'confirm_duplicate' not in request.POST:
                                # Return the form with a warning
                                context = {
                                    'query': query,
                                    'member': member,
                                    'policy': policy,
                                    'payment_history': payment_history,
                                    'payment_form': payment_form,
                                    'receipt_form': receipt_form,
                                    'outstanding_balance': outstanding_balance,
                                    'last_payment': last_payment,
                                    'warning_message': "This appears to be a duplicate payment. Please confirm if you want to proceed.",
                                    'show_duplicate_warning': True,
                                }
                                return render(request, 'payments/policy_payment.html', context)
                            
                            # Create a new payment
                            payment = Payment.objects.create(
                                member=member,
                                policy=policy,
                                amount=amount,
                                date=date,
                                payment_method=method,
                                status='COMPLETED',
                                notes=payment_form.cleaned_data.get('notes', ''),
                                created_by=request.user,
                                ip_address=request.META.get('REMOTE_ADDR', '')
                            )
                            
                            # Auto-generate receipt
                            receipt = create_payment_receipt(payment, request.user)
                            if receipt:
                                show_receipt_modal = True
                                
                                # Auto-send email if member has email
                                if member.email:
                                    send_receipt_email(receipt, member.email)
                            
                            # Update policy status based on payment
                            update_policy_status(policy)
                            
                            success_message = f"Payment of R{payment.amount} recorded successfully."
                            show_receipt_modal = True
                            
                            # Reset forms for new entry
                            payment_form = PaymentForm(prefix='payment')
                            
                    elif 'send_receipt' in request.POST:
                        receipt_id = request.POST.get('receipt_id')
                        send_method = request.POST.get('send_method')
                        recipient = request.POST.get('recipient')
                        
                        try:
                            receipt = PaymentReceipt.objects.get(id=receipt_id)
                            
                            if send_method == 'email':
                                # Send via email
                                receipt.sent_to = recipient
                                receipt.sent_at = timezone.now()
                                receipt.sent_by = request.user
                                receipt.status = 'EMAILED'
                                receipt.save()
                                success_message = f"Receipt sent to {recipient} via email."
                                
                            elif send_method == 'whatsapp':
                                # Send via WhatsApp
                                receipt.sent_to = recipient
                                receipt.sent_at = timezone.now()
                                receipt.sent_by = request.user
                                receipt.status = 'WHATSAPP'
                                receipt.save()
                                success_message = f"Receipt sent to {recipient} via WhatsApp."
                                
                        except PaymentReceipt.DoesNotExist:
                            error_message = "Receipt not found."
                else:
                    # GET: initialize form with today's date
                    payment_form = PaymentForm(prefix='payment', initial={'date': timezone.now().date()})

    # Prepare filter form for payment history
    filter_form = PaymentFilterForm(request.GET)
    
    context = {
        'query': query,
        'member': member,
        'policy': policy,
        'payment_history': payment_history,
        'payment_form': payment_form,
        'receipt_form': receipt_form,
        'filter_form': filter_form,
        'success_message': success_message,
        'error_message': error_message,
        'outstanding_balance': outstanding_balance,
        'last_payment': last_payment,
        'receipt': receipt,
        'show_receipt_modal': show_receipt_modal,
        'ai_summary': ai_summary,
        'avg_payment': avg_payment,
        'plan_premium': plan_premium,
        'allow_override': allow_override,
        'whatsapp_link': get_whatsapp_link(member.phone, receipt.receipt_number) if receipt and member.phone else None,
    }
    return render(request, 'payments/policy_payment.html', context)

@login_required
def payment_list(request):
    """
    Show a list of all payments with filtering, pagination, and export options.
    Enhanced with AI summary, role-based restrictions, and improved UI.
    """
    # Apply role-based restrictions
    if request.user.is_superuser:
        # Superusers can see all payments
        base_payments = Payment.objects.select_related('member', 'policy', 'created_by').order_by('-date')
    elif request.user.groups.filter(name="Branch Owner").exists():
        # Branch owners can only see payments from their branch
        try:
            branch = request.user.branchuser.branch
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                Q(policy__plan__scheme__branch=branch) |
                Q(member__policies__plan__scheme__branch=branch)
            ).distinct().order_by('-date')
        except:
            # Fallback if branch relationship not found
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                created_by=request.user
            ).order_by('-date')
    elif request.user.groups.filter(name="Scheme Admin").exists():
        # Scheme admins can only see payments from their scheme
        try:
            scheme = request.user.schemeuser.scheme
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                Q(policy__plan__scheme=scheme) |
                Q(member__policies__plan__scheme=scheme)
            ).distinct().order_by('-date')
        except:
            # Fallback if scheme relationship not found
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                created_by=request.user
            ).order_by('-date')
    else:
        # Regular users can only see payments they created
        base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
            created_by=request.user
        ).order_by('-date')
    
    # Initialize filter form
    filter_form = PaymentFilterForm(request.GET)
    
    # Start with all payments (after role-based filtering)
    payments = base_payments
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        filters = {}
        
        # Date range filter
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')
        if start_date:
            filters['date__gte'] = start_date
        if end_date:
            filters['date__lte'] = end_date
        
        # Payment method filter
        payment_method = filter_form.cleaned_data.get('payment_method')
        if payment_method:
            filters['payment_method'] = payment_method
        
        # Status filter
        status = filter_form.cleaned_data.get('status')
        if status:
            filters['status'] = status
        
        # Amount range filter
        min_amount = filter_form.cleaned_data.get('min_amount')
        max_amount = filter_form.cleaned_data.get('max_amount')
        if min_amount:
            filters['amount__gte'] = min_amount
        if max_amount:
            filters['amount__lte'] = max_amount
        
        # Search filter (member name, ID, reference)
        search = filter_form.cleaned_data.get('search')
        if search:
            payments = payments.filter(
                Q(member__first_name__icontains=search) |
                Q(member__last_name__icontains=search) |
                Q(member__id_number__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(policy__policy_number__icontains=search)
            )
        
        # Apply all other filters
        if filters:
            payments = payments.filter(**filters)
    
    # Handle export requests
    if 'export' in request.GET:
        export_format = request.GET.get('export')
        if export_format == 'csv':
            return export_payments_csv(payments)
        elif export_format == 'excel':
            return export_payments_excel(payments)
    
    # Generate AI summary data for admin users
    payment_methods_summary = None
    average_payment = 0
    top_capturer = None
    
    if request.user.is_superuser or request.user.groups.filter(name__in=["Branch Owner", "Scheme Admin"]).exists():
        # Get payment methods summary
        from django.db.models import Count
        payment_methods_summary = payments.values('payment_method').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        # Calculate average payment for current month
        current_month = timezone.now().month
        current_year = timezone.now().year
        current_month_payments = payments.filter(
            date__month=current_month,
            date__year=current_year
        )
        if current_month_payments.exists():
            average_payment = current_month_payments.aggregate(
                avg=Sum('amount') / Count('id')
            )['avg'] or 0
        
        # Get top capturer
        top_capturer = payments.values('created_by__username').annotate(
            count=Count('id')
        ).order_by('-count').first()
    
    # Paginate results
    paginator = Paginator(payments, 25)  # Show 25 payments per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals for the filtered payments
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    payment_count = payments.count()
    
    return render(request, 'payments/payment_list.html', {
        'payments': page_obj,
        'filter_form': filter_form,
        'total_amount': total_amount,
        'payment_count': payment_count,
        'page_obj': page_obj,
        'payment_methods_summary': payment_methods_summary,
        'average_payment': average_payment,
        'top_capturer': top_capturer,
    })


@login_required
def payment_history(request):
    """
    Show a historical view of all payments with enhanced filtering, analytics, and export options.
    Includes role-based restrictions and AI-powered insights for admin users.
    """
    # Apply role-based restrictions
    if request.user.is_superuser:
        # Superusers can see all payments
        base_payments = Payment.objects.select_related('member', 'policy', 'created_by').order_by('-date')
    elif request.user.groups.filter(name="Branch Owner").exists():
        # Branch owners can only see payments from their branch
        try:
            branch = request.user.branchuser.branch
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                Q(policy__plan__scheme__branch=branch) |
                Q(member__policies__plan__scheme__branch=branch)
            ).distinct().order_by('-date')
        except:
            # Fallback if branch relationship not found
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                created_by=request.user
            ).order_by('-date')
    elif request.user.groups.filter(name="Scheme Admin").exists():
        # Scheme admins can only see payments from their scheme
        try:
            scheme = request.user.schemeuser.scheme
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                Q(policy__plan__scheme=scheme) |
                Q(member__policies__plan__scheme=scheme)
            ).distinct().order_by('-date')
        except:
            # Fallback if scheme relationship not found
            base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
                created_by=request.user
            ).order_by('-date')
    else:
        # Regular users can only see payments they created
        base_payments = Payment.objects.select_related('member', 'policy', 'created_by').filter(
            created_by=request.user
        ).order_by('-date')
    
    # Initialize filter form
    filter_form = PaymentFilterForm(request.GET)
    
    # Start with all payments (after role-based filtering)
    payments = base_payments
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        filters = {}
        
        # Date range filter
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')
        if start_date:
            filters['date__gte'] = start_date
        if end_date:
            filters['date__lte'] = end_date
        
        # Payment method filter
        payment_method = filter_form.cleaned_data.get('payment_method')
        if payment_method:
            filters['payment_method'] = payment_method
        
        # Status filter
        status = filter_form.cleaned_data.get('status')
        if status:
            filters['status'] = status
        
        # Amount range filter
        min_amount = filter_form.cleaned_data.get('min_amount')
        max_amount = filter_form.cleaned_data.get('max_amount')
        if min_amount:
            filters['amount__gte'] = min_amount
        if max_amount:
            filters['amount__lte'] = max_amount
        
        # Search filter (member name, ID, reference)
        search = filter_form.cleaned_data.get('search')
        if search:
            payments = payments.filter(
                Q(member__first_name__icontains=search) |
                Q(member__last_name__icontains=search) |
                Q(member__id_number__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(policy__policy_number__icontains=search)
            )
        
        # Apply all other filters
        if filters:
            payments = payments.filter(**filters)
    
    # Handle export requests
    if 'export' in request.GET:
        export_format = request.GET.get('export')
        if export_format == 'csv':
            return export_payments_csv(payments)
        elif export_format == 'excel':
            return export_payments_excel(payments)
        elif export_format == 'pdf':
            return export_payments_pdf(payments)
    
    # Generate AI summary data for admin users
    payment_methods_summary = None
    average_payment = 0
    top_capturer = None
    payment_trends = None
    
    if request.user.is_superuser or request.user.groups.filter(name__in=["Branch Owner", "Scheme Admin"]).exists():
        # Get payment methods summary
        payment_methods_summary = payments.values('payment_method').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        # Calculate average payment for current month
        current_month = timezone.now().month
        current_year = timezone.now().year
        current_month_payments = payments.filter(
            date__month=current_month,
            date__year=current_year
        )
        if current_month_payments.exists():
            average_payment = current_month_payments.aggregate(
                avg=Sum('amount') / Count('id')
            )['avg'] or 0
        
        # Get top capturer
        top_capturer = payments.values('created_by__username').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        # Generate payment trends analysis
        try:
            # Get payments for the last 3 months
            today = timezone.now().date()
            three_months_ago = today - timedelta(days=90)
            recent_payments = payments.filter(date__gte=three_months_ago)
            
            # Group by month
            monthly_totals = {}
            for payment in recent_payments:
                month_key = f"{payment.date.year}-{payment.date.month}"
                if month_key not in monthly_totals:
                    monthly_totals[month_key] = 0
                monthly_totals[month_key] += payment.amount
            
            # Analyze trends
            if len(monthly_totals) >= 2:
                sorted_months = sorted(monthly_totals.items())
                last_month = sorted_months[-1][0]
                prev_month = sorted_months[-2][0]
                
                last_month_amount = monthly_totals[last_month]
                prev_month_amount = monthly_totals[prev_month]
                
                if last_month_amount > prev_month_amount:
                    percent_increase = ((last_month_amount - prev_month_amount) / prev_month_amount) * 100
                    payment_trends = f"Payments increased by {percent_increase:.1f}% compared to the previous month."
                elif last_month_amount < prev_month_amount:
                    percent_decrease = ((prev_month_amount - last_month_amount) / prev_month_amount) * 100
                    payment_trends = f"Payments decreased by {percent_decrease:.1f}% compared to the previous month."
                else:
                    payment_trends = "Payment amounts remained stable compared to the previous month."
        except Exception as e:
            # If there's any error in trend analysis, just skip it
            logger.error(f"Error generating payment trends: {e}")
            payment_trends = None
    
    # Paginate results
    paginator = Paginator(payments, 25)  # Show 25 payments per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals for the filtered payments
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    payment_count = payments.count()
    
    return render(request, 'payments/payment_history.html', {
        'payments': page_obj,
        'filter_form': filter_form,
        'total_amount': total_amount,
        'payment_count': payment_count,
        'page_obj': page_obj,
        'payment_methods_summary': payment_methods_summary,
        'average_payment': average_payment,
        'top_capturer': top_capturer,
        'payment_trends': payment_trends,
    })


def export_payments_csv(payments):
    """
    Export payments as CSV file
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payments-{timezone.now().strftime("%Y-%m-%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Payment ID', 'Date', 'Member', 'ID Number', 'Policy Number', 'Amount', 'Method', 'Status', 'Reference'])
    
    for payment in payments:
        writer.writerow([
            payment.id,
            payment.date,
            f"{payment.member.first_name} {payment.member.last_name}",
            payment.member.id_number,
            payment.policy.policy_number if payment.policy else "",
            payment.amount,
            payment.get_payment_method_display(),
            payment.get_status_display(),
            payment.reference_number or "",
        ])
    
    return response


def export_payments_excel(payments):
    """
    Export payments as Excel file
    """
    import xlsxwriter
    import io
    from django.http import HttpResponse
    
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Payments')
    
    # Add header row
    header_format = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'color': 'white'})
    headers = ['Payment ID', 'Date', 'Member', 'ID Number', 'Policy Number', 'Amount', 'Method', 'Status', 'Reference']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Add data rows
    for row, payment in enumerate(payments, start=1):
        worksheet.write(row, 0, payment.id)
        worksheet.write(row, 1, payment.date.strftime('%Y-%m-%d'))
        worksheet.write(row, 2, f"{payment.member.first_name} {payment.member.last_name}")
        worksheet.write(row, 3, payment.member.id_number)
        worksheet.write(row, 4, payment.policy.policy_number if payment.policy else "")
        worksheet.write(row, 5, float(payment.amount))
        worksheet.write(row, 6, payment.get_payment_method_display())
        worksheet.write(row, 7, payment.get_status_display())
        worksheet.write(row, 8, payment.reference_number or "")
    
    # Auto-adjust column widths
    for col in range(len(headers)):
        worksheet.set_column(col, col, 15)
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="payments-{timezone.now().strftime("%Y-%m-%d")}.xlsx"'
    
    return response


def export_payments_pdf(payments):
    """
    Export payments as PDF file
    """
    import io
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Add title
    title = Paragraph(f"Payment Report - {timezone.now().strftime('%Y-%m-%d')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Create table data
    data = [
        ['Payment ID', 'Date', 'Member', 'ID Number', 'Policy Number', 'Amount', 'Method', 'Status', 'Reference']
    ]
    
    # Add payment data
    for payment in payments:
        data.append([
            str(payment.id),
            payment.date.strftime('%Y-%m-%d'),
            f"{payment.member.first_name} {payment.member.last_name}" if payment.member else "N/A",
            payment.member.id_number if payment.member else "N/A",
            payment.policy.policy_number if payment.policy else "N/A",
            f"R {payment.amount:.2f}",
            payment.get_payment_method_display(),
            payment.get_status_display(),
            payment.reference_number or ""
        ])
    
    # Create the table
    table = Table(data)
    
    # Add style
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    # Add row coloring for odd rows
    for row in range(1, len(data), 2):
        style.add('BACKGROUND', (0, row), (-1, row), colors.lightgrey)
    
    table.setStyle(style)
    elements.append(table)
    
    # Add summary information
    total_amount = sum(payment.amount for payment in payments)
    summary_text = f"\nTotal Payments: {len(payments)} | Total Amount: R {total_amount:.2f}"
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(summary_text, styles['Normal']))
    
    # Build the PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HTTP response with PDF content
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payments-{timezone.now().strftime("%Y-%m-%d")}.pdf"'
    response.write(pdf)
    
    return response


@login_required
@user_passes_test(lambda u: u.is_staff)
def process_unmatched_record(request, record_id):
    """
    Process an unmatched record from an import file by manually assigning it to a member.
    This allows admins to fix records that couldn't be automatically matched.
    """
    try:
        # Get the row log for the unmatched record
        row_log = get_object_or_404(RowLog, id=record_id, status='ERROR')
        import_log = row_log.import_log
        
        if request.method == 'POST':
            # Get the member ID from the form
            member_id = request.POST.get('member_id')
            payment_method = request.POST.get('payment_method', 'OTHER')
            payment_status = request.POST.get('payment_status', 'COMPLETED')
            payment_notes = request.POST.get('payment_notes', '')
            
            if not member_id:
                messages.error(request, 'Member ID is required')
                return redirect('payments:import_detail', import_id=import_log.id)
            
            # Get the member
            try:
                member = Member.objects.get(id=member_id)
            except Member.DoesNotExist:
                messages.error(request, 'Member not found')
                return redirect('payments:import_detail', import_id=import_log.id)
            
            # Get the policy
            try:
                policy = Policy.objects.get(member=member, status='ACTIVE')
            except Policy.DoesNotExist:
                messages.error(request, 'No active policy found for this member')
                return redirect('payments:import_detail', import_id=import_log.id)
            
            # Create a payment record
            try:
                # Parse the row data from JSON
                row_data = json.loads(row_log.row_data)
                
                # Extract payment details based on import type
                amount = row_data.get('amount', 0)
                reference = row_data.get('reference', '')
                payment_date = row_data.get('date', datetime.now().strftime('%Y-%m-%d'))
                
                # Try to parse the date
                try:
                    payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                except ValueError:
                    payment_date = timezone.now().date()
                
                # Create the payment
                payment = Payment.objects.create(
                    policy=policy,
                    amount=amount,
                    reference=reference,
                    payment_method=payment_method,
                    status=payment_status,
                    payment_date=payment_date,
                    created_by=request.user,
                    notes=f"Manually matched from import {import_log.id}. {payment_notes}"
                )
                
                # Update the row log status
                row_log.status = 'SUCCESS'
                row_log.error_message = ''
                row_log.save()
                
                # Update import log counts
                import_log.successful_records += 1
                import_log.failed_records -= 1
                import_log.save()
                
                messages.success(request, f'Successfully processed payment of {amount} for {member.first_name} {member.last_name}')
                
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
                return redirect('payments:import_detail', import_id=import_log.id)
            
            return redirect('payments:import_detail', import_id=import_log.id)
            
        # If not POST, redirect back to import detail
        return redirect('payments:import_detail', import_id=import_log.id)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('payments:payment_list')


@login_required
@user_passes_test(lambda u: u.is_staff)
def import_detail(request, import_id):
    """
    Display details of an import, including matched and unmatched records.
    Allows for manual fixing of unmatched records.
    """
    try:
        payment_import = get_object_or_404(ImportLog, id=import_id)
        matched_records = RowLog.objects.filter(import_log=payment_import, status='SUCCESS')
        unmatched_records = RowLog.objects.filter(import_log=payment_import, status='ERROR')
        
        context = {
            'payment_import': payment_import,
            'matched_records': matched_records,
            'unmatched_records': unmatched_records,
        }
        
        return render(request, 'payments/import_detail.html', context)
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('payments:payment_list')


@login_required
@user_passes_test(lambda u: u.is_staff)
def payment_detail(request, payment_id):
    """
    Display details of a specific payment
    """
    payment = get_object_or_404(Payment, id=payment_id)
    return render(request, 'payments/payment_detail.html', {'payment': payment})


@login_required
def unpaid_policies(request):
    """
    Display all Active or On Trial policies with no payment in the last 30+ days
    """
    # Get the date 30 days ago
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    
    # Apply role-based restrictions
    if request.user.is_superuser:
        # Superusers can see all policies
        base_policies = Policy.objects.filter(
            status__in=['ACTIVE', 'TRIAL']
        ).select_related('member', 'plan', 'plan__scheme', 'plan__scheme__branch')
    elif request.user.groups.filter(name="Branch Owner").exists():
        # Branch owners can only see policies from their branch
        try:
            branch = request.user.branchuser.branch
            base_policies = Policy.objects.filter(
                status__in=['ACTIVE', 'TRIAL'],
                plan__scheme__branch=branch
            ).select_related('member', 'plan', 'plan__scheme', 'plan__scheme__branch')
        except:
            # Fallback if branch relationship not found
            base_policies = Policy.objects.filter(
                status__in=['ACTIVE', 'TRIAL'],
                created_by=request.user
            ).select_related('member', 'plan', 'plan__scheme', 'plan__scheme__branch')
    elif request.user.groups.filter(name="Scheme Admin").exists():
        # Scheme admins can only see policies from their scheme
        try:
            scheme = request.user.schemeuser.scheme
            base_policies = Policy.objects.filter(
                status__in=['ACTIVE', 'TRIAL'],
                plan__scheme=scheme
            ).select_related('member', 'plan', 'plan__scheme', 'plan__scheme__branch')
        except:
            # Fallback if scheme relationship not found
            base_policies = Policy.objects.filter(
                status__in=['ACTIVE', 'TRIAL'],
                created_by=request.user
            ).select_related('member', 'plan', 'plan__scheme', 'plan__scheme__branch')
    else:
        # Regular users can only see policies they created
        base_policies = Policy.objects.filter(
            status__in=['ACTIVE', 'TRIAL'],
            created_by=request.user
        ).select_related('member', 'plan', 'plan__scheme', 'plan__scheme__branch')
    
    # Find policies with no payments in the last 30 days
    unpaid_policies = []
    for policy in base_policies:
        latest_payment = Payment.objects.filter(
            policy=policy,
            date__gte=thirty_days_ago,
            status='COMPLETED'
        ).order_by('-date').first()
        
        if not latest_payment:
            # Get the last payment date if any
            last_payment = Payment.objects.filter(
                policy=policy,
                status='COMPLETED'
            ).order_by('-date').first()
            
            last_payment_date = last_payment.date if last_payment else None
            days_since_payment = (timezone.now().date() - last_payment_date).days if last_payment_date else None
            
            # Get agent information
            agent = None
            if hasattr(policy, 'agent'):
                agent = policy.agent
            
            # Add policy to unpaid list with additional info
            unpaid_policies.append({
                'policy': policy,
                'last_payment_date': last_payment_date,
                'days_since_payment': days_since_payment,
                'agent': agent,
                'branch': policy.plan.scheme.branch if policy.plan and policy.plan.scheme else None
            })
    
    # Initialize filter form
    filter_form = PaymentFilterForm(request.GET)
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        # Search filter
        search = filter_form.cleaned_data.get('search')
        if search:
            filtered_policies = []
            for policy_data in unpaid_policies:
                policy = policy_data['policy']
                if (search.lower() in policy.policy_number.lower() or 
                    search.lower() in policy.member.first_name.lower() or 
                    search.lower() in policy.member.last_name.lower() or 
                    search.lower() in policy.member.id_number.lower()):
                    filtered_policies.append(policy_data)
            unpaid_policies = filtered_policies
    
    # Sort by days since payment (descending)    
    unpaid_policies.sort(key=lambda x: x['days_since_payment'] if x['days_since_payment'] else float('inf'), reverse=True)
    
    # Paginate results
    paginator = Paginator(unpaid_policies, 25)  # Show 25 policies per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'payments/unpaid_policies.html', {
        'unpaid_policies': page_obj,
        'filter_form': filter_form,
        'page_obj': page_obj,
        'policy_count': len(unpaid_policies),
    })
