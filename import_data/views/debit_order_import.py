# import_data/views/debit_order_import.py

import csv
from io import TextIOWrapper

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db import transaction

from import_data.models import DebitOrderImport, DebitOrderRowLog
from import_data.forms import ImportForm
from members.models import Policy

# Helper function for reading CSV files
def read_csv(file):
    """Helper function to read CSV and decode its content"""
    f = file.open('rb')
    text = f.read().decode('utf-8')
    f.close()
    return text.splitlines()


# Validation function for debit order data
def validate_debit_order_row(row):
    """Validate a single row of debit order data and return errors if found"""
    errors = []
    membership_number = row.get('membership_number', '').strip()
    bank_reference = row.get('bank_reference', '').strip()
    amount = row.get('amount', '').strip()

    if not membership_number:
        errors.append("Missing membership number")
    
    if not bank_reference:
        errors.append("Missing bank reference")
    
    if not amount or not amount.replace('.', '', 1).isdigit():
        errors.append("Invalid amount")

    return errors, amount


@method_decorator(login_required, name='dispatch')
class DebitOrderImportView(View):
    """
    Handles the upload of debit order files (CSV), parses them, and previews the data.
    """
    template_name = 'import_data/debit_order_import.html'
    form_class = ImportForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['csv_file']
            # Create log entry for the import
            batch = DebitOrderImport.objects.create(
                file=file,
                uploaded_by=request.user
            )

            # Read the CSV file
            lines = read_csv(batch.file)
            reader = csv.DictReader(lines)

            preview_rows = []
            for idx, row in enumerate(reader, start=1):
                if idx > 10:
                    break  # Preview only the first 10 rows

                # Validate the debit order row
                errors, amount = validate_debit_order_row(row)

                preview_rows.append({
                    'row_number': idx,
                    'membership_number': row.get('membership_number', '').strip(),
                    'bank_reference': row.get('bank_reference', '').strip(),
                    'amount': amount,
                    'status': 'error' if errors else 'ok',
                    'errors': errors,
                })

            request.session['debit_order_batch'] = batch.id
            return render(request, 'import_data/debit_order_preview.html', {
                'preview_rows': preview_rows
            })

        return render(request, self.template_name, {'form': form})


@method_decorator(login_required, name='dispatch')
class DebitOrderPreviewView(View):
    """
    Preview and apply the uploaded debit order file, log each row, and apply necessary changes.
    """
    template_name = 'import_data/debit_order_preview.html'

    def post(self, request):
        batch_id = request.session.get('debit_order_batch')
        batch = get_object_or_404(DebitOrderImport, id=batch_id)

        # Read the file again
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        logs = []
        with transaction.atomic():
            for idx, row in enumerate(reader, start=1):
                membership_number = row.get('membership_number', '').strip()
                bank_reference = row.get('bank_reference', '').strip()
                amount = row.get('amount', '').strip()

                # Validate and log any errors
                errors, amount = validate_debit_order_row(row)

                log = DebitOrderRowLog(
                    import_batch=batch,
                    row_number=idx,
                    membership_number=membership_number,
                    bank_reference=bank_reference,
                    amount=amount,
                    status='pending',  # required by the model
                )

                if errors:
                    log.status = 'error'
                    log.error_message = "; ".join(errors)
                    log.save()
                    logs.append(log)
                    continue

                # If no errors, create the necessary reconciliation entry
                # Here, you can link the payment or policy (if required)
                policy = Policy.objects.filter(membership_number=membership_number).first()
                if policy:
                    # Logic to reconcile the debit order with a policy
                    pass

                log.status = 'success'
                log.save()
                logs.append(log)

        return render(request, self.template_name, {'logs': logs})
