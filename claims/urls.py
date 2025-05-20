from django.urls import path
from . import views

app_name = "claims"

urlpatterns = [
    path('submit/', views.submit_claim, name='submit'),
    path('status/', views.claim_status, name='status'),
    path('', views.claims_home, name='claims_home'),
]
