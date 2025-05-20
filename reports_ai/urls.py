from django.urls import path
from . import views

app_name = 'reports_ai'

urlpatterns = [
    # Report Dashboard
    path('', views.report_dashboard, name='dashboard'),
    
    # Report Processing
    path('process-query/', views.process_report_query, name='process_query'),
    path('save-report/', views.save_report, name='save_report'),
    path('saved/<int:report_id>/', views.view_saved_report, name='view_saved_report'),
    
    # Export Endpoints
    path('export/csv/', views.export_report, {'format_type': 'csv'}, name='export_csv'),
    path('export/pdf/', views.export_report, {'format_type': 'pdf'}, name='export_pdf'),
    
    # API Endpoints
    path('api/process-query/', views.process_report_query, name='api_process_query'),
    path('api/save-report/', views.save_report, name='api_save_report'),
]
