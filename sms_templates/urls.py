from django.urls import path
from . import views

app_name = 'sms_templates'

urlpatterns = [
    path('', views.sms_template, name='list'),
    path('<int:pk>/edit/', views.sms_template_edit, name='edit'),
    path('<int:pk>/delete/', views.sms_template_delete, name='delete'),
]
