"""
Payment import logs views for viewing and managing import logs.
"""
import os
import logging
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.core.paginator import Paginator

from .models import PaymentImport

logger = logging.getLogger(__name__)

def is_staff_or_admin(user):
    """Check if user is staff, admin, or superuser"""
    return user.is_staff or user.is_superuser or user.groups.filter(name__in=['Admin', 'Branch Manager']).exists()


@login_required
@user_passes_test(is_staff_or_admin)
def import_log_list(request):
    """
    Display a list of all import logs with filtering and pagination.
    """
    # Get query parameters for filtering
    import_type = request.GET.get('import_type', '')
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_id = request.GET.get('user_id', '')
    
    # Start with all imports
    imports = PaymentImport.objects.all().order_by('-created_at')
    
    # Apply filters
    if import_type:
        imports = imports.filter(import_type=import_type)
    if status:
        imports = imports.filter(status=status)
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            imports = imports.filter(created_at__date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            imports = imports.filter(created_at__date__lte=date_to)
        except ValueError:
            pass
    if user_id:
        imports = imports.filter(imported_by_id=user_id)
    
    # Pagination
    paginator = Paginator(imports, 20)  # Show 20 imports per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get users for filter dropdown
    users = User.objects.filter(is_staff=True).order_by('first_name', 'last_name')
    
    context = {
        'page_obj': page_obj,
        'import_types': dict(PaymentImport.IMPORT_TYPES),
        'statuses': dict(PaymentImport.STATUS_CHOICES),
        'users': users,
        'filters': {
            'import_type': import_type,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
            'user_id': user_id,
        }
    }
    
    return render(request, 'payments/import_log_list.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def download_error_csv(request, log_id):
    """
    Download the error CSV for a specific import log.
    """
    import_log = get_object_or_404(PaymentImport, pk=log_id)
    
    if not import_log.error_csv:
        messages.error(request, "No error CSV file found for this import.")
        return redirect('payments:import_log_list')
    
    try:
        # Get the file path
        file_path = import_log.error_csv.path
        
        # Check if file exists
        if not os.path.exists(file_path):
            messages.error(request, "Error CSV file not found on server.")
            return redirect('payments:import_log_list')
        
        # Prepare response
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
            
    except Exception as e:
        logger.error(f"Error downloading error CSV for import {log_id}: {str(e)}")
        messages.error(request, f"Error downloading file: {str(e)}")
        return redirect('payments:import_log_list')
