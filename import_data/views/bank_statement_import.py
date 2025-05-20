# import_data/views/bank_statement_import.py

import csv
from io import TextIOWrapper
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db import transaction

from import_data.models import BankReconciliationImport, BankReconciliationRowLog
from import_data.forms import ImportForm
from members.models import Policy
from django.db.models import Q

# Helper function for reading CSV files
def read_csv(file):
    """Helper function to read CSV and decode its content"""
    f = file.open('rb')
    text = f.read().decode('utf-8')
    f.close()
    return text.splitlines()

# import_data/views/bank_statement_import.py

import csv
from io import TextIOWrapper
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db import transaction

from import_data.models import BankReconciliationImport, BankReconciliationRowLog
from import_data.forms import ImportForm
from members.models import Policy
from django.db.models import Q

# Helper function for reading CSV files
def read_csv(file):
    """Helper function to read CSV and decode its content"""
    f = file.open('rb')
    text = f.read().decode('utf-8')
    f.close()
    return text.splitlines()

class BankStatementImportView(View):
    """
    Handles the upload of bank statement files (CSV), parses them, and previews the data.
    """
    template_name = 'import_data/bank_reconciliation_import.html'
    form_class = ImportForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['csv_file']
            try:
                # Create log entry for the import
                batch = BankReconciliationImport.objects.create(
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

                    # Validation
                    errors = []
                    transaction_date = row.get('transaction_date', '').strip()
                    amount = row.get('amount', '').strip()

                    # Basic validation
                    if not transaction_date:
                        errors.append("Missing transaction date")
                    if not amount or not amount.replace('.', '', 1).isdigit():
                        errors.append("Invalid amount")

                    preview_rows.append({
                        'row_number': idx,
                        'transaction_date': transaction_date,
                        'amount': amount,
                        'status': 'error' if errors else 'ok',
                        'errors': errors,
                    })

                request.session['bank_reconciliation_batch'] = batch.id
                return render(request, 'import_data/bank_reconciliation_preview.html', {
                    'preview_rows': preview_rows
                })
            except Exception as e:
                messages.error(request, f"An error occurred while processing the file: {e}")
                return render(request, self.template_name, {'form': form})

        return render(request, self.template_name, {'form': form})



@method_decorator(login_required, name='dispatch')
class BankReconciliationPreviewView(View):
    """
    Preview and apply the uploaded bank statement file, log each row, and apply necessary changes.
    """
    template_name = 'import_data/bank_reconciliation_preview.html'

    def post(self, request):
        batch_id = request.session.get('bank_reconciliation_batch')
        batch = get_object_or_404(BankReconciliationImport, id=batch_id)

        # Read the file again
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        logs = []
        with transaction.atomic():
            for idx, row in enumerate(reader, start=1):
                transaction_date = row.get('transaction_date', '').strip()
                amount = row.get('amount', '').strip()

                # Validate and log any errors
                errors = []
                if not transaction_date:
                    errors.append("Missing transaction date")
                if not amount or not amount.replace('.', '', 1).isdigit():
                    errors.append("Invalid amount")

                log = BankReconciliationRowLog(
                    import_batch=batch,
                    row_number=idx,
                    transaction_date=transaction_date,
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
                policy = Policy.objects.filter(membership_number=row.get('reference', '')).first()
                if policy:
                    # Logic to reconcile the bank statement with a policy
                    pass

                log.status = 'success'
                log.save()
                logs.append(log)

        return render(request, self.template_name, {'logs': logs})
