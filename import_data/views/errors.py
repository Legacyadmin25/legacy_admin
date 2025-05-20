# import_data/views/errors.py

from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from import_data.models import ImportLog
import csv

@staff_member_required
def download_error_csv(request, log_id):
    """
    Downloads the error log for failed imports as a CSV file.
    """
    try:
        # Use get() to directly fetch the log entry. This will raise an exception if not found.
        log = ImportLog.objects.get(id=log_id, status="failed")
    except ImportLog.DoesNotExist:
        return HttpResponse("No error log found.", content_type="text/plain")
    
    if not log.error_message:
        return HttpResponse("No error messages found for this log.", content_type="text/plain")

    # Prepare the CSV response
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="import_errors_{log_id}.csv"'

    # Write to the CSV file
    writer = csv.writer(response)
    writer.writerow(["Policy Number", "Error"])

    for line in log.error_message.strip().split("\n"):
        # Handle both cases: policy_number with error, or just error message
        if ":" in line:
            policy_number, error = line.split(":", 1)
            writer.writerow([policy_number.strip(), error.strip()])
        else:
            writer.writerow(["", line.strip()])

    return response
