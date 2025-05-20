import csv
from io import StringIO
import xlsxwriter
from io import BytesIO
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Policy, Member
from settings_app.models import UserRole

@login_required
def export_search_results(request):
    """
    Export search results to CSV or Excel based on the same filters used in the search.
    """
    # Get export format (default to CSV)
    export_format = request.GET.get('format', 'csv')
    
    # Get search parameters (same as in find_policy view)
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    branch_id = request.GET.get('branch', '')
    scheme_id = request.GET.get('scheme', '')
    agent_id = request.GET.get('agent', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    cover_min = request.GET.get('cover_min', '')
    cover_max = request.GET.get('cover_max', '')
    payment_method = request.GET.get('payment_method', '')
    
    # Start with base queryset with all related objects for performance
    policies = Policy.objects.select_related(
        'member', 'plan', 'scheme', 'agent'
    )
    
    # Get user role for filtering
    try:
        user_role = request.user.role.role_type
        user_branch = request.user.role.branch
        user_scheme = request.user.role.scheme
    except (UserRole.DoesNotExist, AttributeError):
        user_role = None
        user_branch = None
        user_scheme = None
    
    # Apply role-based filtering
    if user_role == 'scheme_manager' and user_scheme:
        policies = policies.filter(scheme=user_scheme)
    elif user_role == 'branch_owner' and user_branch:
        policies = policies.filter(scheme__branch=user_branch)
    elif user_role not in ['internal_admin', 'compliance_auditor']:
        # For regular users or agents, only show their own policies
        if hasattr(request.user, 'agent'):
            policies = policies.filter(agent=request.user.agent)
        else:
            policies = policies.none()
    
    # Apply search filter if query exists
    if q:
        policies = policies.filter(
            Q(member__first_name__icontains=q) |
            Q(member__last_name__icontains=q) |
            Q(member__id_number__icontains=q) |
            Q(member__phone_number__icontains=q) |
            Q(policy_number__icontains=q) |
            Q(uw_membership_number__icontains=q)
        )
    
    # Apply advanced filters if provided
    if status:
        if status == 'active':
            policies = policies.filter(is_active=True)
        elif status == 'lapsed':
            policies = policies.filter(is_active=False)
        elif status == 'trial':
            policies = policies.filter(is_trial=True)
    
    # Apply branch filter if selected and user has permission
    if branch_id and branch_id.isdigit() and user_role in ['internal_admin', 'compliance_auditor']:
        policies = policies.filter(scheme__branch_id=branch_id)
    
    # Apply scheme filter if selected and user has permission
    if scheme_id and scheme_id.isdigit():
        policies = policies.filter(scheme_id=scheme_id)
    
    # Apply agent filter if selected
    if agent_id and agent_id.isdigit():
        policies = policies.filter(agent_id=agent_id)
    
    # Apply date range filters
    if date_from:
        try:
            policies = policies.filter(start_date__gte=date_from)
        except ValueError:
            pass  # Invalid date format, ignore
    
    if date_to:
        try:
            policies = policies.filter(start_date__lte=date_to)
        except ValueError:
            pass  # Invalid date format, ignore
    
    # Apply cover amount filters
    if cover_min and cover_min.isdigit():
        policies = policies.filter(cover_amount__gte=cover_min)
    
    if cover_max and cover_max.isdigit():
        policies = policies.filter(cover_amount__lte=cover_max)
    
    # Apply payment method filter
    if payment_method:
        policies = policies.filter(payment_method=payment_method)
    
    # Order by most recent start date first
    policies = policies.order_by('-start_date')
    
    # Define export columns
    columns = [
        'Policy Number', 'Member Name', 'ID Number', 'Phone', 
        'Scheme', 'Plan', 'Premium', 'Cover Amount', 'Status',
        'Agent', 'Start Date', 'Payment Method'
    ]
    
    # Generate filename
    filename = f"policy_search_results"
    
    # Export as CSV
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(columns)
        
        for policy in policies:
            writer.writerow([
                policy.policy_number or policy.uw_membership_number or '',
                f"{policy.member.first_name} {policy.member.last_name}",
                policy.member.id_number or '',
                policy.member.phone_number or '',
                policy.scheme.name if policy.scheme else '',
                policy.plan.name if policy.plan else '',
                f"R{policy.premium}" if policy.premium else 'R0.00',
                f"R{policy.cover_amount}" if policy.cover_amount else 'R0.00',
                'Active' if policy.is_active else ('Trial' if policy.is_trial else 'Lapsed'),
                policy.agent.full_name if policy.agent else '',
                policy.start_date.strftime('%Y-%m-%d') if policy.start_date else '',
                policy.get_payment_method_display() if hasattr(policy, 'get_payment_method_display') else policy.payment_method or ''
            ])
        
        return response
    
    # Export as Excel
    elif export_format == 'excel':
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Policies')
        
        # Add header row
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f0f0f0'})
        for col_num, column_title in enumerate(columns):
            worksheet.write(0, col_num, column_title, header_format)
        
        # Add data rows
        for row_num, policy in enumerate(policies, 1):
            worksheet.write(row_num, 0, policy.policy_number or policy.uw_membership_number or '')
            worksheet.write(row_num, 1, f"{policy.member.first_name} {policy.member.last_name}")
            worksheet.write(row_num, 2, policy.member.id_number or '')
            worksheet.write(row_num, 3, policy.member.phone_number or '')
            worksheet.write(row_num, 4, policy.scheme.name if policy.scheme else '')
            worksheet.write(row_num, 5, policy.plan.name if policy.plan else '')
            worksheet.write(row_num, 6, f"R{policy.premium}" if policy.premium else 'R0.00')
            worksheet.write(row_num, 7, f"R{policy.cover_amount}" if policy.cover_amount else 'R0.00')
            worksheet.write(row_num, 8, 'Active' if policy.is_active else ('Trial' if policy.is_trial else 'Lapsed'))
            worksheet.write(row_num, 9, policy.agent.full_name if policy.agent else '')
            worksheet.write(row_num, 10, policy.start_date.strftime('%Y-%m-%d') if policy.start_date else '')
            worksheet.write(row_num, 11, policy.get_payment_method_display() if hasattr(policy, 'get_payment_method_display') else policy.payment_method or '')
        
        # Auto-adjust column widths
        for i, column in enumerate(columns):
            worksheet.set_column(i, i, len(column) + 5)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    
    # Default to CSV if format not recognized
    else:
        return export_search_results(request)
