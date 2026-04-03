from django.urls import path, include

# Import the auto-save URLs
from .urls_autosave import urlpatterns as autosave_urlpatterns

app_name = 'members'

# Include all auto-save related URLs
urlpatterns = autosave_urlpatterns
