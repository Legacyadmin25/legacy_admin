from django.urls import path
from . import views
from . import views_detail
from . import views_import
from . import views_logs

app_name = 'payments'

urlpatterns = [
    # Payment capture and search
    path('',                      views.policy_payment,              name='policy_payment'),
    path('list/',                 views.payment_list,               name='payment_list'),
    path('history/',              views.payment_history,            name='payment_history'),
    path('unpaid/',               views.unpaid_policies,            name='unpaid_policies'),
    
    # Payment detail, update, delete
    path('<int:pk>/',             views_detail.payment_detail,       name='detail'),
    path('<int:pk>/update/',      views_detail.PaymentUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/',      views_detail.PaymentDeleteView.as_view(), name='delete'),
    path('detail/<int:payment_id>/', views.payment_detail,          name='payment_detail'),
    
    # Export functionality
    path('export/csv/',           views.export_payments_csv,         name='export_csv'),
    path('export/excel/',         views.export_payments_excel,       name='export_excel'),
    
    # Import functionality
    path('import/',               views_import.import_payments,      name='import_payments'),
    path('import/<int:import_id>/easypay/', 
                                 views_import.process_easypay_import, name='process_easypay_import'),
    path('import/<int:import_id>/linkserv/', 
                                 views_import.process_linkserv_import, name='process_linkserv_import'),
    path('import/<int:import_id>/bank-reconciliation/', 
                                 views_import.process_bank_reconciliation_import, name='process_bank_reconciliation_import'),
    path('import/<int:import_id>/', 
                                 views_import.import_detail,         name='import_detail'),
    path('import/record/<int:record_id>/process/', 
                                 views_import.process_unmatched_record, name='process_unmatched_record'),
    
    # Import logs
    path('imports/',              views_logs.import_log_list,     name='import_log_list'),
    path('imports/<int:log_id>/download-errors/', 
                                 views_logs.download_error_csv,    name='download_error_csv'),
]
