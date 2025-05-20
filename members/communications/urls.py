from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    path('sms-sending/', views.sms_sending, name='sms_sending'),
]
