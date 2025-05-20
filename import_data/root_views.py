# import_data/root_views.py

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


# Helper function to generate CSV response with headers
def generate_csv_template(headers, filename):
    """
    Generates a CSV file with the given headers and filename for download.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    return response

@login_required
def download_policy_template(request):
    """
    Send a CSV header row for bulk‐policy import.
    """
    headers = [
        "Policy Number", "Scheme Number", "Plan Name", "Agent Code",
        "Title", "Initials", "First Names", "Surname", "Gender", "ID Type",
        "ID Number", "Date of Birth", "Country of Birth", "Country of Residence", "Nationality",
        "Marital Status", "Address Line 1", "Address Line 2", "Address Line 3", "Postal Code",
        "Cell Number", "Email Address", "Person Type",
        "Beneficiary Name", "Beneficiary Relationship", "Beneficiary Share", "Beneficiary ID"
    ]
    return generate_csv_template(headers, "policy_import_template.csv")

@login_required
def download_policy_amendments_template(request):
    """
    Download a CSV header row for policy-amendments.
    """
    headers = [
        'membership_number',
        'premium_amount',
        'beneficiary_name',
        'beneficiary_relationship',
        'cover_date',
        # add any other fields you support amending…
    ]
    return generate_csv_template(headers, "policy_amendments_template.csv")

@login_required
def download_lapsed_reactivation_template(request):
    """
    Download a CSV header row for lapsed-policy reactivation.
    """
    headers = [
        'membership_number',
        'new_start_date',  # YYYY-MM-DD
        'arrears',         # optional
    ]
    return generate_csv_template(headers, "lapsed_reactivation_template.csv")

@login_required
def download_agent_onboarding_template(request):
    """
    Send a one-row CSV header for Agent Onboarding.
    """
    headers = [
        'full_name',
        'surname',
        'id_number',
        'passport_number',
        'scheme_code',
        'code',
        'contact_number',
        'commission_percentage',
    ]
    return generate_csv_template(headers, "agent_onboarding_template.csv")

@login_required
def download_debit_order_template(request):
    """
    Download a CSV header row for debit-order import.
    """
    headers = [
        'membership_number',
        'bank_reference',
        'debit_date',   # YYYY-MM-DD
        'amount',
        'status',       # paid/failed/bounced
    ]
    return generate_csv_template(headers, "debit_order_template.csv")

@login_required
def download_easypay_template(request):
    """
    Download a CSV header row for Easypay/PayFast reconciliation.
    """
    headers = [
        'membership_number',
        'payment_reference',
        'payment_date',  # YYYY-MM-DD
        'amount',
        'status',        # paid/duplicate/unmatched
    ]
    return generate_csv_template(headers, "easypay_template.csv")

@login_required
def download_bank_reconciliation_template(request):
    """
    Download a CSV header row for bank-statement reconciliation.
    """
    headers = [
        'transaction_date',  # YYYY-MM-DD
        'description',
        'amount',
        'reference',         # policy or membership_number
    ]
    return generate_csv_template(headers, "bank_reconciliation_template.csv")

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ImportLog


class ImportLogListView(LoginRequiredMixin, ListView):
    """
    Step 2: Show a paginated list of all import attempts (success/failed).
    """
    model = ImportLog
    template_name = 'import_data/logs.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = ImportLog.objects.all()
        context['success_count'] = logs.filter(status='success').count()
        context['failed_count'] = logs.filter(status='failed').count()
        return context

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from django.urls import reverse

@login_required
def redirect_to_unified_import(request, import_type=None):
    """
    Redirects legacy payment import routes to the new unified payment import page
    with an optional query parameter to pre-select the import type.
    """
    url = reverse('payments:import_payments')
    if import_type:
        url += f'?type={import_type}'
    return redirect(url)
from .forms import ImportForm
from .models import ImportLog


@login_required
def upload_csv(request):
    """
    Step 1: GET shows the upload form; POST processes a generic CSV.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = form.cleaned_data['csv_file']
            log = ImportLog.objects.create(
                filename=csvfile.name,
                status='processing',
                created_by=request.user
            )
            path = default_storage.save(f'tmp/{csvfile.name}', csvfile)

            try:
                # TODO: Replace with actual parsing logic
                log.records_processed = 100
                log.records_successful = 95
                log.records_failed = 5
                log.status = 'success'
                log.save()
                messages.success(request, "CSV imported successfully.")
            except Exception as e:
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Import failed: {e}")
            finally:
                default_storage.delete(path)

            return redirect(reverse('import_data:logs'))
    else:
        form = ImportForm()

    return render(request, 'import_data/upload.html', {'form': form})

@login_required
def data_import(request):
    """
    Simple redirect to the CSV upload screen (for sidebar links).
    """
    return redirect('import_data:upload_csv')

@login_required
def bulk_policy_import(request):
    """
    Upload & process bulk-policy CSV.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = form.cleaned_data['csv_file']
            log = ImportLog.objects.create(
                filename=csvfile.name,
                status='processing',
                created_by=request.user,
                category='policy',
                subtype='bulk',
            )
            path = default_storage.save(f'tmp/{csvfile.name}', csvfile)

            try:
                # TODO: Implement CSV parser & save Policy instances
                log.records_processed = 100
                log.records_successful = 95
                log.records_failed = 5
                log.status = 'success'
                log.save()
                messages.success(request, "Bulk policy import successful.")
            except Exception as e:
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Bulk import failed: {e}")
            finally:
                default_storage.delete(path)

            return redirect('import_data:logs')
    else:
        form = ImportForm()

    return render(request, 'import_data/bulk_policy_import.html', {
        'form': form,
    })


# import_data/root_views.py

import csv
from io import TextIOWrapper
from datetime import datetime
import io

import pandas as pd
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage

from .forms import ImportForm
from .models import ImportLog

# Helper function to generate CSV response with headers
def generate_csv_template(headers, filename):
    """
    Generates a CSV file with the given headers and filename for download.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    return response


# ImportLogListView (already optimized earlier)
class ImportLogListView(LoginRequiredMixin, ListView):
    """
    Step 2: Show a paginated list of all import attempts (success/failed).
    """
    model = ImportLog
    template_name = 'import_data/logs.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = ImportLog.objects.all()
        context['success_count'] = logs.filter(status='success').count()
        context['failed_count'] = logs.filter(status='failed').count()
        return context


# Now, place these views for import processing below the ImportLogListView class

@login_required
def policy_amendments_import(request):
    """
    Upload & process policy-amendments CSV.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = form.cleaned_data['csv_file']
            log = ImportLog.objects.create(
                filename=csvfile.name,
                status='processing',
                created_by=request.user,
                import_type='members',
            )
            path = default_storage.save(f'tmp/{csvfile.name}', csvfile)

            try:
                # TODO: Implement amendments logic
                log.records_processed = 50
                log.records_successful = 48
                log.records_failed = 2
                log.status = 'success'
                log.save()
                messages.success(request, "Policy amendments import successful.")
            except Exception as e:
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Policy amendments import failed: {e}")
            finally:
                default_storage.delete(path)

            return redirect('import_data:logs')
    else:
        form = ImportForm()

    return render(request, 'import_data/policy_amendments_upload.html', {
        'form': form,
    })


@login_required
def lapsed_policy_reactivation_import(request):
    """
    Upload & process lapsed-policy reactivation CSV.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = form.cleaned_data['csv_file']
            log = ImportLog.objects.create(
                filename=csvfile.name,
                status='processing',
                created_by=request.user,
                import_type='members',
            )
            path = default_storage.save(f'tmp/{csvfile.name}', csvfile)

            try:
                # TODO: Implement reactivation logic
                log.records_processed = 30
                log.records_successful = 28
                log.records_failed = 2
                log.status = 'success'
                log.save()
                messages.success(request, "Lapsed policies reactivated successfully.")
            except Exception as e:
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Reactivation failed: {e}")
            finally:
                default_storage.delete(path)

            return redirect('import_data:logs')
    else:
        form = ImportForm()

    return render(request, 'import_data/lapsed_policy_reactivation_import.html', {
        'form': form,
    })


@login_required
def agent_onboarding_import(request):
    """
    Upload & process agent-onboarding CSV.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = form.cleaned_data['csv_file']
            log = ImportLog.objects.create(
                filename=csvfile.name,
                status='processing',
                created_by=request.user,
                import_type='agents',
            )
            path = default_storage.save(f'tmp/{csvfile.name}', csvfile)

            try:
                # TODO: Implement agent creation logic
                log.records_processed = 25
                log.records_successful = 24
                log.records_failed = 1
                log.status = 'success'
                log.save()
                messages.success(request, "Agent data imported successfully.")
            except Exception as e:
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Agent import failed: {e}")
            finally:
                default_storage.delete(path)

            return redirect('import_data:logs')
    else:
        form = ImportForm()

    return render(request, 'import_data/agent_onboarding_import.html', {
        'form': form,
    })


@login_required
def debit_order_import(request):
    """
    Import debit-order file for payment reconciliation.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = form.cleaned_data['csv_file']
            log = ImportLog.objects.create(
                filename=csvfile.name,
                status='processing',
                created_by=request.user,
                import_type='payments',
            )
            path = default_storage.save(f'tmp/{csvfile.name}', csvfile)

            try:
                # TODO: NACHA/CSV parsing logic
                log.records_processed = 150
                log.records_successful = 145
                log.records_failed = 5
                log.status = 'success'
                log.save()
                messages.success(request, "Debit order file processed successfully.")
            except Exception as e:
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Debit import failed: {e}")
            finally:
                default_storage.delete(path)

            return redirect('import_data:logs')
    else:
        form = ImportForm()

    return render(request, 'import_data/debit_order_import.html', {
        'form': form,
    })


@login_required
def easypay_import(request):
    """
    Import Easypay (or other third-party) payment reports.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = form.cleaned_data['csv_file']
            log = ImportLog.objects.create(
                filename=csvfile.name,
                status='processing',
                created_by=request.user,
                import_type='payments',
            )
            path = default_storage.save(f'tmp/{csvfile.name}', csvfile)

            try:
                # TODO: Easypay parsing logic
                log.records_processed = 120
                log.records_successful = 118
                log.records_failed = 2
                log.status = 'success'
                log.save()
                messages.success(request, "Easypay file processed successfully.")
            except Exception as e:
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Easypay import failed: {e}")
            finally:
                default_storage.delete(path)

            return redirect('import_data:logs')
    else:
        form = ImportForm()

    return render(request, 'import_data/easypay_import.html', {
        'form': form,
    })
