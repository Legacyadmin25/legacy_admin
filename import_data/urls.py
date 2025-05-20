# import_data/urls.py

from django.urls import path
from . import root_views
from import_data.views.policy_confirm import confirm_bulk_policy_import
from import_data.views.policy_preview import preview_bulk_policy_import
from import_data.views.policy_amendments_import import (
    PolicyAmendmentImportView, PolicyAmendmentPreviewView
)
from import_data.views.lapsed_policy_reactivation import (
    LapsedPolicyReactivationUploadView, LapsedPolicyReactivationPreviewView
)
from import_data.views.agent_onboarding import (
    AgentOnboardingUploadView, AgentOnboardingPreviewView
)
from import_data.views.logs import ImportLogListView
from import_data.views.errors import download_error_csv
from import_data.views.bank_statement_import import BankStatementImportView, BankReconciliationPreviewView

app_name = 'import_data'

urlpatterns = [
    # Bulk Policy
    path('policy/bulk/', root_views.bulk_policy_import, name='bulk_policy_upload'),
    path('policy/bulk/template/download/', root_views.download_policy_template, name='download_policy_template'),
    path('policy/bulk/preview/', preview_bulk_policy_import, name='bulk_policy_preview'),
    path('policy/bulk/confirm/', confirm_bulk_policy_import, name='confirm_bulk_policy_import'),

    # Policy Amendments
    path('policy/amendments/', PolicyAmendmentImportView.as_view(), name='policy_amendments_import'),
    path('policy/amendments/template/download/', root_views.download_policy_amendments_template, name='download_policy_amendments_template'),
    path('policy/amendments/preview/<int:pk>/', PolicyAmendmentPreviewView.as_view(), name='policy_amendments_preview'),

    # Lapsed Reactivations
    path('policy/reactivations/', LapsedPolicyReactivationUploadView.as_view(), name='lapsed_policy_reactivation_import'),
    path('policy/reactivations/template/download/', root_views.download_lapsed_reactivation_template, name='download_lapsed_reactivation_template'),
    path('policy/reactivations/preview/<int:pk>/', LapsedPolicyReactivationPreviewView.as_view(), name='lapsed_policy_reactivation_preview'),

    # Agent Onboarding
    path('agents/onboard/', AgentOnboardingUploadView.as_view(), name='agent_onboarding_import'),
    path('agents/onboard/template/download/', root_views.download_agent_onboarding_template, name='download_agent_onboarding_template'),
    path('agents/onboard/preview/', AgentOnboardingPreviewView.as_view(), name='agent_onboarding_preview'),

    # Debit Orders - Redirected to unified payment import page
    path('payments/debit-orders/', root_views.redirect_to_unified_import, {'import_type': 'debit_orders'}, name='debit_order_file_import'),
    path('payments/debit-orders/template/download/', root_views.download_debit_order_template, name='download_debit_order_template'),

    # Easypay - Redirected to unified payment import page
    path('payments/easypay/', root_views.redirect_to_unified_import, {'import_type': 'easypay'}, name='easypay_file_import'),
    path('payments/easypay/template/download/', root_views.download_easypay_template, name='download_easypay_template'),

    # Bank Reconciliation - Redirected to unified payment import page
    path('payments/bank-reconciliation/', root_views.redirect_to_unified_import, {'import_type': 'bank_reconciliation'}, name='bank_statement_import'),
    path('payments/reconciliation-preview/', BankReconciliationPreviewView.as_view(), name='bank_reconciliation_preview'),
    path('payments/bank-reconciliation/template/download/', root_views.download_bank_reconciliation_template, name='download_bank_reconciliation_template'),

    # Logs & Errors
    path('logs/', ImportLogListView.as_view(), name='import_logs'),
    path('logs/<int:pk>/download-errors/', download_error_csv, name='download_errors'),
]
