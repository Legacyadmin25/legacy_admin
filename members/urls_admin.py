"""
Admin URLs for application review and management
"""
from django.urls import path
from members.views_admin import (
    applications_list,
    application_detail,
    approve_application,
    reject_application,
    application_stats,
)

app_name = 'app_admin'

urlpatterns = [
    # Admin Dashboard
    path('', applications_list, name='applications_list'),
    path('stats/', application_stats, name='application_stats'),
    
    # Application Management
    path('application/<int:application_id>/', application_detail, name='application_detail'),
    path('application/<int:application_id>/approve/', approve_application, name='approve_application'),
    path('application/<int:application_id>/reject/', reject_application, name='reject_application'),
]
