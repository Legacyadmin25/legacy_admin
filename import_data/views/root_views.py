# root_views.py (helper function for file upload)
from django.core.files.storage import default_storage
from import_data.models import ImportLog
import pandas as pd

def handle_file_upload(request, form, import_type):
    if form.is_valid():
        csvfile = form.cleaned_data['csv_file']
        log = ImportLog.objects.create(
            import_type=import_type,
            filename=csvfile.name,
            status='processing',
            created_by=request.user
        )
        path = default_storage.save(f'tmp/{csvfile.name}', csvfile)
        return path, log
    return None, None
