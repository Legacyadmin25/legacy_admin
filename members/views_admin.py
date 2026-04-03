"""
Admin views for application review and approval
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils import timezone
from datetime import datetime

from members.models_public_enrollment import PublicApplication
from members.utils_public_enrollment import convert_application_to_policy

logger = logging.getLogger(__name__)


def staff_required(user):
    """Check if user is staff"""
    return user.is_staff


@login_required
@user_passes_test(staff_required)
def applications_list(request):
    """
    Admin dashboard: List applications for review
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'submitted')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    applications = PublicApplication.objects.all().order_by('-created_at')
    
    # Filter by status
    if status_filter and status_filter != 'all':
        applications = applications.filter(status=status_filter)
    
    # Search by name or email
    if search_query:
        applications = applications.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(application_id__icontains=search_query)
        )
    
    # Count by status
    status_stats = {
        'submitted': PublicApplication.objects.filter(status='submitted').count(),
        'approved': PublicApplication.objects.filter(status='approved').count(),
        'rejected': PublicApplication.objects.filter(status='rejected').count(),
        'completed': PublicApplication.objects.filter(status='completed').count(),
    }
    
    context = {
        'applications': applications,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_stats': status_stats,
        'total_count': PublicApplication.objects.count(),
    }
    
    return render(request, 'members/admin/applications_list.html', context)


@login_required
@user_passes_test(staff_required)
def application_detail(request, application_id):
    """
    Admin view: Full application details and approval form
    """
    application = get_object_or_404(PublicApplication, pk=application_id)
    
    context = {
        'application': application,
        'has_debit_order': application.payment_method == 'DEBIT_ORDER',
    }
    
    return render(request, 'members/admin/application_detail.html', context)


@login_required
@user_passes_test(staff_required)
@require_http_methods(["POST"])
def approve_application(request, application_id):
    """
    Admin action: Approve application and trigger policy creation + PDF
    """
    application = get_object_or_404(PublicApplication, pk=application_id)
    
    # Check if already processed
    if application.status in ['completed', 'rejected']:
        messages.warning(request, f"Application already {application.status}")
        return redirect('app_admin:application_detail', application_id=application_id)
    
    try:
        # Set status to approved first
        application.status = 'approved'
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()
        
        # Convert to policy (automatically sends PDF email)
        success, policy = convert_application_to_policy(
            application=application,
            reviewed_by=request.user
        )
        
        if success:
            messages.success(
                request,
                f"✓ Application {application.application_id} approved! "
                f"Policy created and PDF sent to {application.email}"
            )
            logger.info(
                f"Application {application.id} approved by {request.user.username}. "
                f"Policy {policy.id} created. PDF sent to {application.email}"
            )
        else:
            messages.error(request, f"Error creating policy: {policy}")
            logger.error(f"Failed to create policy for application {application.id}: {policy}")
    
    except Exception as e:
        messages.error(request, f"Error approving application: {str(e)}")
        logger.error(f"Error approving application {application.id}: {str(e)}")
    
    return redirect('app_admin:applications_list')


@login_required
@user_passes_test(staff_required)
@require_http_methods(["POST"])
def reject_application(request, application_id):
    """
    Admin action: Reject application
    """
    application = get_object_or_404(PublicApplication, pk=application_id)
    
    # Check if already processed
    if application.status in ['completed', 'rejected']:
        messages.warning(request, f"Application already {application.status}")
        return redirect('app_admin:applications_list')
    
    try:
        rejection_reason = request.POST.get('rejection_reason', 'No reason provided')
        
        application.status = 'rejected'
        application.rejection_reason = rejection_reason
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()
        
        messages.success(request, f"Application {application.application_id} rejected")
        logger.info(
            f"Application {application.id} rejected by {request.user.username}. "
            f"Reason: {rejection_reason}"
        )
    
    except Exception as e:
        messages.error(request, f"Error rejecting application: {str(e)}")
        logger.error(f"Error rejecting application {application.id}: {str(e)}")
    
    return redirect('app_admin:applications_list')


@login_required
@user_passes_test(staff_required)
def application_stats(request):
    """
    Admin dashboard: Application statistics
    """
    total = PublicApplication.objects.count()
    submitted = PublicApplication.objects.filter(status='submitted').count()
    approved = PublicApplication.objects.filter(status='approved').count()
    rejected = PublicApplication.objects.filter(status='rejected').count()
    completed = PublicApplication.objects.filter(status='completed').count()
    
    # Recent applications
    recent = PublicApplication.objects.all().order_by('-created_at')[:10]
    
    context = {
        'total': total,
        'submitted': submitted,
        'approved': approved,
        'rejected': rejected,
        'completed': completed,
        'recent': recent,
    }
    
    return render(request, 'members/admin/application_stats.html', context)
