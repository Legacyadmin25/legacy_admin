import json
import time
import logging
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q, Sum, Count, F, Case, When, Value, IntegerField
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse

from members.models import Policy, Member
from payments.models import Payment
from .models import ReportQuery, ReportExecutionLog, SavedReport
from .utils import parse_ai_query, generate_ai_summary

logger = logging.getLogger(__name__)


@login_required
def report_dashboard(request):
    """Main dashboard for AI reports"""
    # Get user's saved reports
    saved_reports = SavedReport.objects.filter(user=request.user).order_by('-last_accessed')[:5]
    recent_queries = ReportQuery.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Sample questions for the UI
    sample_questions = [
        "List all claims paid this year",
        "Agent commission report for " + timezone.now().strftime("%B"),
        "Policy lapse report by branch",
        "Monthly premium collection for the last 6 months",
        "Top performing agents by premium collected"
    ]
    
    context = {
        'saved_reports': saved_reports,
        'recent_queries': recent_queries,
        'sample_questions': sample_questions,
    }
    return render(request, 'reports_ai/dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def process_report_query(request):
    """Process natural language query and return report data"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({'error': 'Query cannot be empty'}, status=400)
        
        # Parse the query using AI
        try:
            parsed_query = parse_ai_query(query, request.user)
        except Exception as e:
            logger.error(f"Error parsing query with AI: {str(e)}")
            return JsonResponse(
                {'error': 'Could not process your query. Please try rephrasing.'}, 
                status=400
            )
        
        # Create report query record
        report_query = ReportQuery.objects.create(
            user=request.user,
            original_query=query,
            report_type=parsed_query['report_type'],
            filters=parsed_query.get('filters', {})
        )
        
        # Generate report data
        report_data = generate_report(report_query)
        
        return JsonResponse({
            'success': True,
            'report_type': report_query.report_type,
            'filters': report_query.filters,
            'data': report_data,
            'report_id': report_query.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.exception("Error processing report query")
        return JsonResponse(
            {'error': 'An unexpected error occurred'}, 
            status=500
        )


def generate_report(report_query):
    """Generate report data based on the query"""
    start_time = time.time()
    execution_log = ReportExecutionLog.objects.create(
        report_query=report_query,
        status='pending'
    )
    
    try:
        report_type = report_query.report_type
        filters = report_query.filters or {}
        
        # Apply role-based filtering
        filters.update(get_role_based_filters(report_query.user))
        
        # Generate report data based on type
        if report_type == 'commissions':
            data = generate_commission_report(filters)
        elif report_type == 'lapses':
            data = generate_lapse_report(filters)
        elif report_type == 'claims':
            data = generate_claims_report(filters)
        elif report_type == 'payments':
            data = generate_payments_report(filters)
        elif report_type == 'debit_orders':
            data = generate_debit_order_report(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        # Generate AI summary
        try:
            data['ai_summary'] = generate_ai_summary(report_type, data, filters)
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            data['ai_summary'] = ""
        
        # Update execution log
        execution_time = time.time() - start_time
        execution_log.status = 'success'
        execution_log.execution_time = execution_time
        execution_log.record_count = len(data.get('rows', []))
        execution_log.save()
        
        return data
        
    except Exception as e:
        logger.exception("Error generating report")
        execution_log.status = 'error'
        execution_log.error_message = str(e)
        execution_log.save()
        raise


def get_role_based_filters(user):
    """Apply role-based access control to filters"""
    filters = {}
    
    if user.groups.filter(name='branch_owner').exists():
        filters['branch_id'] = user.branch.id if hasattr(user, 'branch') else None
    elif user.groups.filter(name='agent').exists():
        filters['agent_id'] = user.id
    elif user.groups.filter(name='scheme_manager').exists():
        filters['scheme_id__in'] = list(user.managed_schemes.values_list('id', flat=True))
    
    return filters


def generate_commission_report(filters):
    """Generate agent commission report"""
    # This is a simplified example - adjust based on your commission structure
    from django.db.models.functions import TruncMonth
    
    # Base query
    query = Payment.objects.filter(
        status='completed',
        **filters
    )
    
    # Group by month and agent
    report_data = query.annotate(
        month=TruncMonth('payment_date')
    ).values('month', 'agent__first_name', 'agent__last_name').annotate(
        total_commission=Sum('commission_amount'),
        payment_count=Count('id')
    ).order_by('-month')
    
    # Format response
    return {
        'columns': ['Month', 'Agent', 'Total Commission', 'Payment Count'],
        'rows': [
            [
                row['month'].strftime('%B %Y'),
                f"{row['agent__first_name']} {row['agent__last_name']}",
                float(row['total_commission'] or 0),
                row['payment_count']
            ]
            for row in report_data
        ],
        'summary': {
            'total_commission': float(query.aggregate(total=Sum('commission_amount'))['total'] or 0),
            'total_payments': query.count()
        }
    }


def generate_lapse_report(filters):
    """Generate policy lapse report"""
    # Get lapsed policies based on your criteria
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    lapsed_policies = Policy.objects.filter(
        status='active',
        last_payment_date__lt=thirty_days_ago,
        **filters
    ).select_related('member', 'scheme')
    
    # Format response
    return {
        'columns': ['Policy Number', 'Member', 'Last Payment', 'Days Overdue', 'Premium'],
        'rows': [
            [
                policy.policy_number,
                policy.member.full_name,
                policy.last_payment_date.strftime('%Y-%m-%d') if policy.last_payment_date else 'Never',
                (timezone.now().date() - policy.last_payment_date.date()).days \
                    if policy.last_payment_date else 'N/A',
                float(policy.premium or 0)
            ]
            for policy in lapsed_policies
        ],
        'summary': {
            'total_policies': lapsed_policies.count(),
            'total_premium': float(sum(p.premium or 0 for p in lapsed_policies))
        }
    }


def generate_claims_report(filters):
    """Generate claims report"""
    claims = Claim.objects.filter(**filters).select_related('policy', 'member')
    
    return {
        'columns': ['Claim ID', 'Member', 'Policy', 'Amount', 'Status', 'Date'],
        'rows': [
            [
                claim.id,
                claim.member.full_name,
                claim.policy.policy_number if claim.policy else 'N/A',
                float(claim.amount or 0),
                claim.status,
                claim.claim_date.strftime('%Y-%m-%d') if claim.claim_date else ''
            ]
            for claim in claims
        ],
        'summary': {
            'total_claims': claims.count(),
            'total_amount': float(claims.aggregate(total=Sum('amount'))['total'] or 0)
        }
    }


def generate_payments_report(filters):
    """Generate payments report"""
    payments = Payment.objects.filter(**filters).select_related('member', 'policy')
    
    return {
        'columns': ['Date', 'Member', 'Policy', 'Amount', 'Method', 'Status'],
        'rows': [
            [
                payment.payment_date.strftime('%Y-%m-%d'),
                payment.member.full_name if payment.member else 'N/A',
                payment.policy.policy_number if payment.policy else 'N/A',
                float(payment.amount or 0),
                payment.get_payment_method_display(),
                payment.status
            ]
            for payment in payments
        ],
        'summary': {
            'total_payments': payments.count(),
            'total_amount': float(payments.aggregate(total=Sum('amount'))['total'] or 0)
        }
    }


def generate_debit_order_report(filters):
    """Generate debit order collection report"""
    from django.db.models.functions import TruncDay
    
    debit_orders = Payment.objects.filter(
        payment_method='debit_order',
        **filters
    )
    
    # Group by day and status
    daily_totals = debit_orders.annotate(
        day=TruncDay('payment_date')
    ).values('day', 'status').annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-day')
    
    return {
        'columns': ['Date', 'Status', 'Total Amount', 'Count'],
        'rows': [
            [
                row['day'].strftime('%Y-%m-%d'),
                row['status'],
                float(row['total_amount'] or 0),
                row['count']
            ]
            for row in daily_totals
        ],
        'summary': {
            'total_collected': float(debit_orders.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0),
            'success_rate': (debit_orders.filter(status='completed').count() / debit_orders.count()) * 100 \
                if debit_orders.exists() else 0
        }
    }


@login_required
def view_saved_report(request, report_id):
    """View a saved report"""
    saved_report = get_object_or_404(SavedReport, id=report_id, user=request.user)
    
    # Update last accessed time
    saved_report.save()  # This will update last_accessed due to auto_now=True
    
    # Get the report data
    report_data = generate_report(saved_report.report_query)
    
    context = {
        'report': saved_report,
        'report_data': report_data,
        'is_saved': True
    }
    return render(request, 'reports_ai/report_view.html', context)


@login_required
@require_http_methods(["POST"])
def save_report(request):
    """Save a report for future reference"""
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        report_name = data.get('name', '').strip()
        
        if not report_name:
            return JsonResponse({'error': 'Report name is required'}, status=400)
        
        report_query = get_object_or_404(ReportQuery, id=report_id, user=request.user)
        
        # Create or update saved report
        saved_report, created = SavedReport.objects.update_or_create(
            user=request.user,
            report_query=report_query,
            defaults={'name': report_name}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Report saved successfully',
            'saved_report_id': saved_report.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.exception("Error saving report")
        return JsonResponse(
            {'error': 'An error occurred while saving the report'}, 
            status=500
        )


@login_required
@require_http_methods(["POST"])
def export_report(request, format_type):
    """Export report in various formats"""
    try:
        data = json.loads(request.body)
        report_type = data.get('report_type')
        filters = data.get('filters', {})
        
        # Apply role-based filtering
        filters.update(get_role_based_filters(request.user))
        
        # Generate report data
        if report_type == 'commissions':
            report_data = generate_commission_report(filters)
        elif report_type == 'lapses':
            report_data = generate_lapse_report(filters)
        elif report_type == 'claims':
            report_data = generate_claims_report(filters)
        elif report_type == 'payments':
            report_data = generate_payments_report(filters)
        elif report_type == 'debit_orders':
            report_data = generate_debit_order_report(filters)
        else:
            return JsonResponse({'error': 'Invalid report type'}, status=400)
        
        # Export based on format
        if format_type == 'csv':
            return export_to_csv(report_data, report_type)
        elif format_type == 'pdf':
            return export_to_pdf(report_data, report_type)
        else:
            return JsonResponse({'error': 'Unsupported export format'}, status=400)
            
    except Exception as e:
        logger.exception("Error exporting report")
        return JsonResponse(
            {'error': 'An error occurred while exporting the report'}, 
            status=500
        )


def export_to_csv(report_data, report_name):
    """Export report data to CSV"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(report_data['columns'])
    
    # Write data rows
    for row in report_data['rows']:
        writer.writerow(row)
    
    # Create response
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_name}_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response


def export_to_pdf(report_data, report_name):
    """Export report data to PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    elements.append(Paragraph(report_name, styles['Title']))
    
    # Create table
    data = [report_data['columns']] + report_data['rows']
    table = Table(data)
    
    # Add style
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    # Apply style to table
    table.setStyle(style)
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    # Create response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
