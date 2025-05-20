from django.urls import path
from .views import (
    index,
    branch_dashboard,
    scheme_dashboard,
    export_dashboard_pdf,
    export_dashboard_excel,
)

app_name = 'dashboard'  # Namespace for the app, ensuring URL names are prefixed with 'dashboard:'

urlpatterns = [
    # GET  /dashboard/               → main dashboard view
    path('', index, name='index'),  # This is the URL for the main dashboard page.

    # GET  /dashboard/branch/        → branch-specific dashboard
    path('branch/', branch_dashboard, name='branch_dashboard'),  # This handles the URL for the branch dashboard.

    # GET  /dashboard/scheme/<id>/   → scheme-specific dashboard
    path('scheme/<int:scheme_id>/', scheme_dashboard, name='scheme_dashboard'),  # This URL handles the scheme-specific dashboard.

    # GET  /dashboard/export/pdf/    → export dashboard as PDF
    path('export/pdf/', export_dashboard_pdf, name='dashboard_export_pdf'),  # This URL handles exporting the dashboard as a PDF.

    # GET  /dashboard/export/excel/  → export dashboard as Excel
    path('export/excel/', export_dashboard_excel, name='dashboard_export_excel'),  # This URL handles exporting the dashboard as an Excel file.
]

