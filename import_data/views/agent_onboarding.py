# import_data/views/agent_onboarding.py

import csv
from io import TextIOWrapper

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from import_data.models import AgentOnboardingImport, AgentOnboardingRowLog
from import_data.forms import AgentOnboardingUploadForm
from schemes.models import Scheme
from settings_app.models import Agent


# Utility function for reading CSV
def read_csv(file):
    """Helper function to read CSV and decode its content"""
    f = file.open('rb')
    text = f.read().decode('utf-8')
    f.close()
    return text.splitlines()


# Centralized validation function
def validate_row(row):
    """Validates a single row for required fields and returns any errors found"""
    errs = []
    scheme_code = row.get('scheme_code', '').strip()
    agent_code = row.get('code', '').strip()
    commission_raw = row.get('commission_percentage', '').strip()

    try:
        pct = float(commission_raw)
    except (ValueError, TypeError):
        pct = None

    # Validate scheme existence
    if not Scheme.objects.filter(scheme_number=scheme_code).exists():
        errs.append("Scheme not found")
    
    # Validate duplicate agent code
    if Agent.objects.filter(code=agent_code).exists():
        errs.append("Duplicate code")
    
    # Validate commission percentage
    if pct is None or not (0 <= pct <= 100):
        errs.append("Invalid commission")

    return errs, pct


@method_decorator(login_required, name='dispatch')
class AgentOnboardingUploadView(View):
    """
    Upload CSV and preview first 10 agent rows.
    """
    template_name = 'import_data/agent_onboarding_upload.html'
    form_class = AgentOnboardingUploadForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        # Save batch
        batch = AgentOnboardingImport.objects.create(
            file=form.cleaned_data['file'],
            uploaded_by=request.user
        )

        # Read and decode file
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        preview_rows = []
        for idx, row in enumerate(reader, start=1):
            if idx > 10:
                break  # Preview only first 10 rows

            errs, pct = validate_row(row)
            preview_rows.append({
                'row_number': idx,
                'full_name': row.get('full_name', '').strip(),
                'surname': row.get('surname', '').strip(),
                'scheme_code': row.get('scheme_code', '').strip(),
                'code': row.get('code', '').strip(),
                'contact_number': row.get('contact_number', '').strip(),
                'commission_percentage': row.get('commission_percentage', '').strip(),
                'status': 'error' if errs else 'ok',
                'errors': errs,
            })

        request.session['agent_onboarding_batch'] = batch.id
        return render(request, 'import_data/agent_onboarding_preview.html', {
            'preview_rows': preview_rows
        })


@method_decorator(login_required, name='dispatch')
class AgentOnboardingPreviewView(View):
    """
    Apply the uploaded CSV: create Agent records and log each row.
    """
    template_name = 'import_data/agent_onboarding_preview.html'

    def post(self, request):
        batch_id = request.session.get('agent_onboarding_batch')
        batch = get_object_or_404(AgentOnboardingImport, id=batch_id)

        # Read and decode file again
        lines = read_csv(batch.file)
        reader = csv.DictReader(lines)

        logs = []
        with transaction.atomic():
            for idx, row in enumerate(reader, start=1):
                errs, pct = validate_row(row)

                log = AgentOnboardingRowLog(
                    import_batch=batch,
                    row_number=idx,
                    full_name=row.get('full_name', '').strip(),
                    surname=row.get('surname', '').strip(),
                    id_number=row.get('id_number', '').strip() or None,
                    passport_number=row.get('passport_number', '').strip() or None,
                    scheme_code=row.get('scheme_code', '').strip(),
                    code=row.get('code', '').strip(),
                    contact_number=row.get('contact_number', '').strip(),
                    commission_percentage=pct or 0,
                    status='pending',  # required by model
                )

                if errs:
                    log.status = 'error'
                    log.error_message = "; ".join(errs)
                    log.save()
                    logs.append(log)
                    continue

                # Create agent
                try:
                    scheme = Scheme.objects.get(scheme_number=row['scheme_code'])
                except Scheme.DoesNotExist:
                    log.status = 'error'
                    log.error_message = "Scheme not found"
                    log.save()
                    logs.append(log)
                    continue

                agent = Agent(
                    full_name=log.full_name,
                    surname=log.surname,
                    id_number=log.id_number,
                    passport_number=log.passport_number,
                    scheme=scheme,
                    code=log.code,
                    contact_number=log.contact_number,
                    commission_percentage=pct
                )
                agent.save()

                log.status = 'success'
                log.save()
                logs.append(log)

        return render(request, self.template_name, {'logs': logs})
