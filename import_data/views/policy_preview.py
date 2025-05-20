# import_data/views/policy_preview.py
import io
import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required


@login_required
def preview_bulk_policy_import(request):
    """
    Preview the first 100 rows of a bulk-policy CSV.
    """
    if request.method != 'POST':
        return redirect('import_data:bulk_policy_upload')

    uploaded_file = request.FILES.get('csv_file')
    if not uploaded_file:
        messages.error(request, "No file uploaded.")
        return redirect('import_data:bulk_policy_upload')

    # Temporarily save the uploaded file
    tmp_path = default_storage.save(f"tmp/{uploaded_file.name}", uploaded_file)
    try:
        # Open and decode the CSV in one step
        with default_storage.open(tmp_path, mode='r') as temp_file:
            decoded = temp_file.read().decode('utf-8')

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(decoded))
        rows = []
        for idx, row in enumerate(reader, start=1):
            if idx > 100:  # Only process first 100 rows
                break
            rows.append(row)

        if not rows:
            messages.error(request, "CSV file appears empty.")
            return redirect('import_data:bulk_policy_upload')

        # Store path & filename in session for the apply step
        request.session['preview_file_path'] = tmp_path
        request.session['preview_filename'] = uploaded_file.name

        return render(request, 'import_data/bulk_policy_preview.html', {
            'rows': rows,
            'filename': uploaded_file.name,
            'total_rows': len(rows),
        })

    except Exception as e:
        messages.error(request, f"Could not preview file: {str(e)}")
        return redirect('import_data:bulk_policy_upload')

    finally:
        # Clean up the temporary file after use
        default_storage.delete(tmp_path)
