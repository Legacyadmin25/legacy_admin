from django.urls import path
from . import views

app_name = 'supplements'

urlpatterns = [
    path('', views.supplementary_benefits_setup, name='setup'),
    path('edit/<int:pk>/', views.edit_benefit, name='edit'),
    path('delete/<int:pk>/', views.delete_benefit, name='delete'),
]
