# import_data/views/logs.py

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count

from import_data.models import ImportLog

class ImportLogListView(LoginRequiredMixin, ListView):
    """
    Displays a paginated list of all import logs, with counts for success and failure.
    """
    model = ImportLog
    template_name = 'import_data/logs.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Use annotate() to combine the counting of success and failure logs into a single query
        log_counts = ImportLog.objects.aggregate(
            success_count=Count('id', filter=ImportLog.objects.filter(status=ImportLog.STATUS_SUCCESS)),
            failed_count=Count('id', filter=ImportLog.objects.filter(status=ImportLog.STATUS_FAILED)),
        )

        # Add success and failure counts to the context
        ctx['success_count'] = log_counts['success_count']
        ctx['failed_count'] = log_counts['failed_count']

        return ctx
