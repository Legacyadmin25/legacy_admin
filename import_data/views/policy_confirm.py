# import_data/views/policy_confirm.py

import csv
import io
from datetime import datetime

from django.shortcuts import redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction

from import_data.models import ImportLog
from members.models import Member, Policy, Dependent, Beneficiary
from schemes.models import Scheme
from settings_app.models import Agent


# Helper function to read and normalize the CSV file
def read_and_normalize_csv(file):
    """Reads the CSV file and normalizes the row data."""
    decoded = file.read().decode('utf-8')
    file.close()
    reader = csv.DictReader(io.StringIO(decoded))
    rows = []

    for raw in reader:
        # Normalize keys to lowercase and strip unnecessary whitespace
        row = {k.strip().lower(): v.strip() for k, v in raw.items() if k}
        if row:
            rows.append(row)
    return rows


# Helper function to get the scheme or return an error message
def get_scheme(scheme_number):
    """Fetch Scheme object by scheme number or return None."""
    try:
        return Scheme.objects.get(scheme_number=scheme_number)
    except Scheme.DoesNotExist:
        return None


# Helper function to compute changes between original and updated fields
def compute_changes(original, updates):
    """Compare original Policy instance and updates dict, return changes."""
    diffs = {}
    for field, new_val in updates.items():
        old_val = getattr(original, field, None)
        if new_val and str(old_val) != str(new_val):
            diffs[field] = [old_val, new_val]
    return diffs


@login_required
def confirm_bulk_policy_import(request):
    """
    Confirm the bulk policy import, create Members, Policies, Dependents & Beneficiaries.
    """
    tmp_path = request.session.get('preview_file_path')
    filename = request.session.get('preview_filename')

    if not tmp_path or not default_storage.exists(tmp_path):
        messages.error(request, "Preview file missing or expired.")
        return redirect('import_data:bulk_policy_upload')

    # Read and normalize CSV rows
    file = default_storage.open(tmp_path, mode='rb')
    rows = read_and_normalize_csv(file)

    # Group rows by membership_number
    groups = {}
    for row in rows:
        membership = row.get('membership_number')
        if membership:
            groups.setdefault(membership, []).append(row)

    # Initialize counters & ImportLog
    total = success = failed = 0
    errors = []

    log = ImportLog.objects.create(
        import_type='bulk_policy',
        category='policy',
        subtype='bulk',
        filename=filename,
        status=ImportLog.STATUS_PROCESSING,
        created_by=request.user
    )

    # Process each membership group
    for policy_no, group_rows in groups.items():
        total += 1
        try:
            main = group_rows[0]
            # Required fields validation
            required = ['id no', 'first names', 'scheme no', 'membership_number']
            if not all(main.get(f) for f in required):
                raise ValueError("Missing required main member fields.")

            # Fetch scheme and agent
            scheme = get_scheme(main['scheme no'])
            if not scheme:
                raise ValueError(f"Scheme not found: {main['scheme no']}")
            agent = Agent.objects.filter(code=main.get('agent', '')).first()

            # Create member and policy within a transaction
            with transaction.atomic():
                # Create Member
                member = Member.objects.create(
                    first_name=main['first names'],
                    last_name=main.get('surname', ''),
                    id_number=main['id no'],
                    cell_number=main.get('cell number', ''),
                    email=main.get('email address', ''),
                    address1=main.get('address line 1', ''),
                    address2=main.get('address line 2', ''),
                    address3=main.get('address line 3', ''),
                    code=main.get('postal code', ''),
                )

                # Create Policy
                policy = Policy.objects.create(
                    member=member,
                    membership_number=main['membership_number'],
                    uw_membership_number=main.get('uw_membership_number', ''),
                    start_date=timezone.now().date(),
                    inception_date=timezone.now().date(),
                    cover_date=timezone.now().date(),
                    scheme=scheme,
                    underwritten_by='BulkImport',
                    branch=scheme.branch,
                )

                # Create Beneficiary
                Beneficiary.objects.create(
                    policy=policy,
                    full_name=main.get('beneficiary name', ''),
                    relationship=main.get('beneficiary relationship', ''),
                    id_number=main.get('beneficiary id', ''),
                    share=100,
                )

                # Create Dependents for remaining rows
                for dep in group_rows[1:]:
                    dob = None
                    if dep.get('date of birth'):
                        dob = datetime.strptime(dep['date of birth'], '%Y-%m-%d').date()
                    Dependent.objects.create(
                        policy=policy,
                        full_name=dep.get('first names', ''),
                        id_number=dep.get('id no', ''),
                        dob=dob,
                        relationship=dep.get('relationship', ''),
                    )

            success += 1

        except Exception as e:
            failed += 1
            errors.append(f"{policy_no}: {e}")

    # Finalize ImportLog
    log.records_processed = total
    log.records_successful = success
    log.records_failed = failed
    log.status = ImportLog.STATUS_SUCCESS if failed == 0 else ImportLog.STATUS_FAILED
    if errors:
        log.error_message = "\n".join(errors[:10])  # Limit the number of error messages
    log.save()  # completed_at is auto-set when status != processing

    # Clean up
    default_storage.delete(tmp_path)
    request.session.pop('preview_file_path', None)
    request.session.pop('preview_filename', None)

    messages.success(request, f"Import complete: {success} succeeded, {failed} failed.")
    return redirect('import_data:import_logs')
