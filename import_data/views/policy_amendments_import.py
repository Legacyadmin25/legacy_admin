# import_data/views/policy_amendments_import.py

import csv
from io import TextIOWrapper

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from import_data.models import PolicyAmendmentImport, PolicyAmendmentRowLog
from import_data.forms import PolicyAmendmentUploadForm
from members.models import Policy


# Helper function for reading CSV files
def read_csv(file):
    """Helper function to read and decode CSV content."""
    f = file.open('r', encoding='utf-8')
    text = f.read()
    f.close()
    return text.splitlines()


# Helper function to validate if the policy exists
def get_policy_by_membership(membership_number):
    """Retrieve a policy by membership number or return None if not found."""
    try:
        return Policy.objects.get(membership_number=membership_number)
    except Policy.DoesNotExist:
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
class PolicyAmendmentImportView(View):
    """
    Handles the upload of policy amendment CSV files.
    """
    template_name = 'import_data/policy_amendments_import.html'
    form_class = PolicyAmendmentUploadForm

    def get(self, request):
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        # Create the batch for uploaded file
        batch = PolicyAmendmentImport.objects.create(
            file=request.FILES['file'],
            uploaded_by=request.user
        )
        return redirect(
            'import_data:policy_amendments_preview',
            pk=batch.pk
        )


@method_decorator(login_required, name='dispatch')
class PolicyAmendmentPreviewView(View):
    """
    Preview and apply policy amendments.
    """
    template_name = 'import_data/policy_amendments_preview.html'

    def get(self, request, pk):
        batch = get_object_or_404(PolicyAmendmentImport, pk=pk)
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        preview_rows = []
        for idx, row in enumerate(reader, start=1):
            if idx > 10:
                break  # Preview only the first 10 rows

            membership_number = row.get('membership_number', '').strip()
            policy = get_policy_by_membership(membership_number)

            # If policy is not found
            if not policy:
                preview_rows.append({
                    'row': idx,
                    'membership_number': membership_number,
                    'status': 'Not Found',
                    'changes': {},
                    'errors': {'membership_number': 'Policy not found'}
                })
                continue

            updates = {
                k: v for k, v in row.items()
                if k != 'membership_number' and v.strip()
            }
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
        batch = get_object_or_404(PolicyAmendmentImport, pk=pk)
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        logs = []
        with transaction.atomic():
            for idx, row in enumerate(reader, start=1):
                membership_number = row.get('membership_number', '').strip()
                policy = get_policy_by_membership(membership_number)

                if not policy:
                    PolicyAmendmentRowLog.objects.create(
                        import_batch=batch,
                        row_number=idx,
                        membership_number=membership_number,
                        status='not_found',
                        errors={'membership_number': 'Policy not found'},
                        changes={}
                    )
                    continue

                updates = {
                    k: v for k, v in row.items()
                    if k != 'membership_number' and v.strip()
                }
                diffs = compute_changes(policy, updates)

                if not diffs:
                    # No changes to the policy
                    PolicyAmendmentRowLog.objects.create(
                        import_batch=batch,
                        row_number=idx,
                        membership_number=membership_number,
                        status='success',
                        errors={},
                        changes={}
                    )
                    continue

                # Apply the changes
                for field, new_val in updates.items():
                    setattr(policy, field, new_val)
                policy.save()

                PolicyAmendmentRowLog.objects.create(
                    import_batch=batch,
                    row_number=idx,
                    membership_number=membership_number,
                    status='success',
                    errors={},
                    changes=diffs
                )

        batch.status = 'completed'
        batch.save()
        messages.success(request, "Policy amendments applied successfully.")
        return redirect(
            'import_data:policy_amendments_preview',
            pk=batch.pk
        )
