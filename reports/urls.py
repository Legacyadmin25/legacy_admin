from django.urls import path
from . import views

app_name = 'reports'  # Add this line

urlpatterns = [
    path('', views.generate_report, name='report_hub'),
    path('all_members_report/', views.all_members_report, name='all_members_report'),
    path('payment_allocation_report/', views.payment_allocation_report, name='payment_allocation_report'),
    path('amendments_report/', views.amendments_report, name='amendments_report'),
    path('generate_report/', views.generate_report, name='generate_report'),
]