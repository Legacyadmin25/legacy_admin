# import_data/views/lapsed_policy_reactivation.py

import csv
from io import TextIOWrapper
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from import_data.models import (
    LapsedPolicyReactivationImport,
    LapsedPolicyReactivationRowLog,
)
from import_data.forms import LapsedReactivateUploadForm
from members.models import Policy


# Utility function for reading CSV files
def read_csv(file):
    """Helper function to read CSV and decode its content"""
    f = file.open('r', encoding='utf-8')
    text = f.read()
    f.close()
    return text.splitlines()


# Utility function for validating date fields
def validate_date(date_str):
    """Helper function to validate date format (YYYY-MM-DD)"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


# Function to compute changes between original and updated fields
def compute_changes(original, updates):
    """
    Compare original Policy instance and updates dict,
    return a dict of changed fields and their [old, new] values.
    """
    diffs = {}
    for field, new_val in updates.items():
        old_val = getattr(original, field, None)
        if new_val is not None and str(old_val) != str(new_val):
            diffs[field] = [old_val, new_val]
    return diffs


@method_decorator(login_required, name='dispatch')
class LapsedPolicyReactivationUploadView(View):
    """
    Upload form for lapsed-policy reactivation.
    """
    template_name = 'import_data/lapsed_policy_reactivation_import.html'
    form_class = LapsedReactivateUploadForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        # Create a batch for the uploaded file
        batch = LapsedPolicyReactivationImport.objects.create(
            file=request.FILES['file'],
            uploaded_by=request.user
        )
        return redirect(
            'import_data:lapsed_policy_reactivation_preview',
            pk=batch.pk
        )


@method_decorator(login_required, name='dispatch')
class LapsedPolicyReactivationPreviewView(View):
    """
    Preview & apply lapsed-policy reactivation.
    """
    template_name = 'import_data/lapsed_policy_reactivation_preview.html'

    def get(self, request, pk):
        batch = get_object_or_404(LapsedPolicyReactivationImport, pk=pk)
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        preview_rows = []
        for idx, row in enumerate(reader, start=1):
            if idx > 10:
                break  # Preview only the first 10 rows

            membership_number = row.get('membership_number', '').strip()
            policy = Policy.objects.filter(membership_number=membership_number).first()

            # Handle policy not found case
            if not policy:
                preview_rows.append({
                    'row': idx,
                    'membership_number': membership_number,
                    'status': 'Not Found',
                    'changes': {},
                    'errors': {'membership_number': 'Policy not found'},
                })
                continue

            # Prepare the updates
            updates = {}
            if not policy.is_active:
                updates['is_active'] = True

            # Handle date reactivation
            new_start_date = row.get('new_start_date', '').strip()
            if new_start_date:
                cover_date = validate_date(new_start_date)
                if cover_date:
                    updates['cover_date'] = cover_date
                else:
                    preview_rows.append({
                        'row': idx,
                        'membership_number': membership_number,
                        'status': 'Error',
                        'changes': {},
                        'errors': {'new_start_date': 'Invalid date (YYYY-MM-DD)'}
                    })
                    continue

            # Compute changes
            diffs = compute_changes(policy, updates)
            preview_rows.append({
                'row': idx,
                'membership_number': membership_number,
                'status': 'Ready',
                'changes': diffs,
                'errors': {}
            })

        return render(request, self.template_name, {
            'batch': batch,
            'preview_rows': preview_rows
        })

    def post(self, request, pk):
        batch = get_object_or_404(LapsedPolicyReactivationImport, pk=pk)
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        logs = []
        with transaction.atomic():
            for idx, row in enumerate(reader, start=1):
                membership_number = row.get('membership_number', '').strip()
                policy = Policy.objects.filter(membership_number=membership_number).first()

                # Handle policy not found case
                if not policy:
                    LapsedPolicyReactivationRowLog.objects.create(
                        import_batch=batch,
                        row_number=idx,
                        membership_number=membership_number,
                        status='not_found',
                        errors={'membership_number': 'Policy not found'},
                        changes={}
                    )
                    continue

                # Prepare the updates
                updates = {}
                if not policy.is_active:
                    updates['is_active'] = True

                # Handle date reactivation
                new_start_date = row.get('new_start_date', '').strip()
                if new_start_date:
                    cover_date = validate_date(new_start_date)
                    if cover_date:
                        updates['cover_date'] = cover_date
                    else:
                        LapsedPolicyReactivationRowLog.objects.create(
                            import_batch=batch,
                            row_number=idx,
                            membership_number=membership_number,
                            status='error',
                            errors={'new_start_date': 'Invalid date (YYYY-MM-DD)'},
                            changes={}
                        )
                        continue

                # Apply updates and log them
                if updates:
                    for field, val in updates.items():
                        setattr(policy, field, val)
                    policy.save()

                    diffs = compute_changes(policy, updates)
                    LapsedPolicyReactivationRowLog.objects.create(
                        import_batch=batch,
                        row_number=idx,
                        membership_number=membership_number,
                        status='success',
                        errors={},
                        changes=diffs
                    )
                else:
                    LapsedPolicyReactivationRowLog.objects.create(
                        import_batch=batch,
                        row_number=idx,
                        membership_number=membership_number,
                        status='success',
                        errors={},
                        changes={}
                    )

        # Mark batch as completed
        batch.status = 'completed'
        batch.save()
        messages.success(request, "Lapsed policies reactivated successfully.")
        return redirect(
            'import_data:lapsed_policy_reactivation_preview',
            pk=batch.pk
        )
