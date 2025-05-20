from django.urls import path
from .views.dashboards import (
    BranchDashboardView,
    SchemeDashboardView,
    AgentDetailView,
    regenerate_diy_link
)
from .views.ai_insights import scheme_insights, branch_insights

urlpatterns = [
    # Branch Dashboard
    path('branch/<int:pk>/', BranchDashboardView.as_view(), name='branch_dashboard'),
    
    # Scheme Dashboard
    path('scheme/<int:pk>/', SchemeDashboardView.as_view(), name='scheme_dashboard'),
    
    # Agent Detail
    path('agent/<int:pk>/', AgentDetailView.as_view(), name='agent_detail'),
    path('agent/<int:agent_id>/regenerate-diy-link/', regenerate_diy_link, name='agent_regenerate_diy_link'),
    
    # Reports
    path('branch/<int:pk>/reports/', BranchDashboardView.as_view(), name='branch_reports'),
    path('scheme/<int:pk>/reports/', SchemeDashboardView.as_view(), name='scheme_reports'),
    
    # AI Insights
    path('branch/<int:pk>/insights/', branch_insights, name='branch_insights'),
    path('scheme/<int:pk>/insights/', scheme_insights, name='scheme_insights'),
]
