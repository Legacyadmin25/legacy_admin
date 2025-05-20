from django.urls import path, include
from . import views
from .views.agents import bulk_agent_actions, regenerate_diy_token
from .views.underwriters import (
    UnderwriterListView, UnderwriterCreateView, UnderwriterUpdateView, UnderwriterDeleteView
)
from .views.plans import (
    PlanListView, PlanCreateView, PlanUpdateView, plan_deactivate, export_plans_csv, clone_plan,
    plan_template_download, plan_import, plan_delete
)
from .views.dashboards import (
    BranchDashboardView, SchemeDashboardView, AgentDetailView
)
from .views.test_openai import TestOpenAIView
from .views.api import suggest_tiers
from .views.ai_privacy_test import (
    ai_privacy_dashboard, update_ai_consent, test_redact_pii, test_ai_insight
)
from members.communications.views import sms_sending

app_name = 'settings'

urlpatterns = [
    # General settings
    path('', views.general_settings, name='general_settings'),
    
    # Role-based Dashboards
    path('dashboards/', include('settings_app.urls_dashboards')),

    # Supplementary Benefits
    path('supplements/', include('supplements.urls', namespace='supplements')),

    # Branch Setup
    path('branch-setup/', views.BranchListView.as_view(), name='branch'),
    path('branch-setup/create/', views.BranchCreateView.as_view(), name='branch_create'),
    path('branch-setup/<int:pk>/edit/', views.BranchUpdateView.as_view(), name='branch_edit'),
    path('branch-setup/<int:pk>/delete/', views.BranchDeleteView.as_view(), name='branch_delete'),
    path('branch-export-csv/', views.export_branches_csv, name='branch_export_csv'),

    # Scheme Setup
    path('scheme-setup/', views.SchemeListView.as_view(), name='scheme'),
    path('scheme-setup/create/', views.SchemeCreateView.as_view(), name='scheme_create'),
    path('scheme-setup/<int:pk>/edit/', views.SchemeUpdateView.as_view(), name='scheme_edit'),
    path('scheme-setup/<int:pk>/delete/', views.SchemeDeleteView.as_view(), name='scheme_delete'),
    path('scheme-setup/documents/upload/', views.upload_scheme_document, name='scheme_doc_upload'),
    path('scheme-setup/documents/<int:pk>/delete/', views.delete_scheme_document, name='scheme_doc_delete'),

    # Agent Dashboard
    path('agent-dashboard/', views.AgentDashboardView.as_view(), name='agent_dashboard'),
    
    # Agent Setup
    path('agent-setup/', views.agent_setup, name='agent'),
    path('agent-setup/add/', views.agent_setup, name='agent_create'),
    path('agent-setup/<int:pk>/edit/', views.agent_setup, name='agent_edit'),
    path('agent-setup/<int:pk>/delete/', views.AgentDeleteView.as_view(), name='agent_delete'),
    path('agent-setup/export/csv/', views.export_agents_csv, name='agent_export_csv'),
    path('agent/diy-link/', views.AgentDIYLinkView.as_view(), name='agent_diy_link'),

    # Bulk and Token Actions
    path('agents/bulk-actions/', bulk_agent_actions, name='bulk_agent_actions'),
    path('agents/<int:agent_id>/regenerate-token/', regenerate_diy_token, name='agent_regenerate_token'),
    path('agents/export/', views.export_agents_csv, name='agent_export_csv'),

    # Plan Setup
    path('plan-setup/', PlanListView.as_view(), name='plan'),
    path('plan-setup/create/', PlanCreateView.as_view(), name='plan_create'),
    path('plan-setup/edit/<int:pk>/', PlanUpdateView.as_view(), name='plan_edit'),
    path('plan-setup/deactivate/<int:pk>/', plan_deactivate, name='plan_deactivate'),
    path('plan-setup/export/', export_plans_csv, name='plan_export'),
    path('plan-setup/clone/<int:pk>/', clone_plan, name='plan_clone'),
    path('plan-setup/template/', plan_template_download, name='plan_template'),
    path('plan-setup/import/', plan_import, name='plan_import'),
    path('plan-setup/delete/<int:pk>/', plan_delete, name='plan_delete'),
    path('plan-setup/simple-create/', views.simple_create_plan, name='simple_create_plan'),
    path('api/suggest-tiers/', suggest_tiers, name='api_suggest_tiers'),

    # AI Privacy Controls
    path('ai-privacy/', ai_privacy_dashboard, name='ai_privacy_dashboard'),
    path('ai-privacy/update-consent/', update_ai_consent, name='update_ai_consent'),
    path('ai-privacy/test-redact-pii/', test_redact_pii, name='test_redact_pii'),
    path('ai-privacy/test-insight/', test_ai_insight, name='test_ai_insight'),

    # User Setup
    path('user-setup/', views.UserListView.as_view(), name='user_setup'),
    path('user-setup/add/', views.UserCreateView.as_view(), name='user_create'),
    path('user-setup/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('user-setup/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('user-setup/import/', views.import_users_view, name='user_import'),
    path('user-setup/template/', views.user_template_download, name='user_template_download'),

    # Underwriter Setup
    path('underwriters/', UnderwriterListView.as_view(), name='underwriter'),
    path('underwriters/add/', UnderwriterCreateView.as_view(), name='underwriter_add'),
    path('underwriters/edit/<int:pk>/', UnderwriterUpdateView.as_view(), name='underwriter_edit'),
    path('underwriters/delete/<int:pk>/', UnderwriterDeleteView.as_view(), name='underwriter_delete'),

    # Permissions & Communications
    path('manage-rights/', views.manage_rights_view, name='manage_rights'),
    path('sms-sending/', sms_sending, name='sms_sending'),
    
    # Test OpenAI Configuration
    path('test-openai/', TestOpenAIView.as_view(), name='test_openai'),
]
