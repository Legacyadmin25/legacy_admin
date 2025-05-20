# import_data/views/bulk_policy_import.py

import pandas as pd
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from import_data.forms import ImportForm
from import_data.models import ImportLog
from import_data.views.root_views import handle_file_upload  # Import centralized file handling


# List of required fields for each policy
REQUIRED_MAIN_FIELDS = [
    'Policy Number', 'Scheme No', 'Plan Name', 'Agent Code',
    'First Name', 'Surname', 'ID Number', 'Date of Birth',
    'Address Line 1', 'Beneficiary First Name', 'Beneficiary Surname', 'Beneficiary ID Number'
]


def process_policy_file(file_path):
    """
    Helper function to process the uploaded CSV/Excel file and return grouped policy data.
    """
    try:
        # Read CSV as a dataframe using pandas (assuming Excel format here)
        df = pd.read_excel(file_path)
        grouped = df.groupby('Policy Number')
        policy_groups = []

        for policy_number, group in grouped:
            members = group.to_dict('records')
            main_member = next((m for m in members if str(m.get('Member Type', '')).lower() == 'main'), None)

            if not main_member:
                continue  # Skip if no main member

            # Check for missing required fields
            missing = [field for field in REQUIRED_MAIN_FIELDS if pd.isna(main_member.get(field)) or main_member.get(field) == '']
            policy_groups.append({
                'policy_number': policy_number,
                'members': members,
                'main_member': main_member,
                'missing_fields': missing,
            })
        
        return policy_groups

    except Exception as e:
        raise ValueError(f"Error processing the file: {str(e)}")


class BulkPolicyImportView(View):
    """
    Handles the bulk policy CSV file upload, parsing, and logging.
    """
    def get(self, request):
        form = ImportForm()
        return render(request, 'import_data/policy_upload.html', {'form': form})

    def post(self, request):
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            path, log = handle_file_upload(request, form, 'policy')
            if not path:
                return redirect('import_data:data')

            try:
                # Process the CSV/Excel file
                policy_groups = process_policy_file(default_storage.open(path))

                # Store preview data in session for preview step
                request.session['import_preview'] = policy_groups
                log.status = 'pending'
                log.records_processed = len(policy_groups)
                log.save()

                # Clean up the temporary file
                default_storage.delete(path)

                return redirect('import_data:policy_bulk_preview')

            except ValueError as e:
                # Handle errors with a custom message (like file processing issues)
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Import failed: {e}")
                return redirect('import_data:data')

            except Exception as e:
                # Handle other unforeseen errors
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
                messages.error(request, f"Unexpected error: {e}")
                return redirect('import_data:data')

        return render(request, 'import_data/policy_upload.html', {'form': form})


class PolicyBulkPreviewView(View):
    """
    Previews the uploaded bulk policy CSV data.
    """
    def get(self, request):
        preview_data = request.session.get('import_preview', [])
        return render(request, 'import_data/policy_preview.html', {'policies': preview_data})
