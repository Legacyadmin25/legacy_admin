from django.urls import path
from . import views

app_name = 'reports'  # Add this line

urlpatterns = [
    path('full_policy_report/', views.full_policy_report, name='full_policy_report'),
    path('plan_fee_report/', views.plan_fee_report, name='plan_fee_report'),
    path('generate_report/', views.generate_report, name='generate_report'),
]