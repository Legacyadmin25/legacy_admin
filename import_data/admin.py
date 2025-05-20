# import_data/admin.py

from django.contrib import admin
from .models import ImportLog


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'category',
        'subtype',
        'filename',
        'status',
        'started_at',
        'completed_at',
        'records_processed',  # Add this to display processed records directly
    )
    list_filter = (
        'status',
        'category',
        'subtype',
    )
    search_fields = (
        'filename',
        'import_type',  # Consider removing 'error_message' from search for better performance
    )
    readonly_fields = (
        'created_by',
        'started_at',
        'completed_at',
        'error_message',  # Make 'error_message' readonly to avoid unintentional editing
    )

    date_hierarchy = 'started_at'

    fieldsets = (
        (None, {
            'fields': (
                'import_type',
                'category',
                'subtype',
                'filename',
                'status',
            )
        }),
        ('Statistics', {
            'fields': (
                'records_processed',
                'records_successful',
                'records_failed',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by',
                'started_at',
                'completed_at',
                'error_message',
            )
        }),
    )

    # Optionally, you can add sorting by default
    ordering = ('-started_at',)  # Orders by 'started_at' in descending order by default

    # Add pagination to optimize performance
    list_per_page = 25  # You can adjust this number based on how many records you want per page
