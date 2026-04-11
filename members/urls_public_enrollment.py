"""
Public Enrollment URLs
Separate namespace for public self-service enrollment.

The start view below seeds scheme/agent context into the session and then
redirects into the shared multi-step policy wizard (members:step1_personal).
All old step-specific routes have been removed; the wizard now handles the
full application flow for both staff and link-based public users.
"""

from django.urls import path
from . import views_public_enrollment
from .views_short_links import enrollment_short_redirect

app_name = 'public_enrollment'

urlpatterns = [
    # Short link redirect (e.g. /apply/s/3/ → /apply/<token>/)
    path('s/<int:link_id>/', enrollment_short_redirect, name='short_link'),

    # Entry point – validates token, seeds session, and redirects to shared
    # wizard at members:step1_personal
    path('<str:token>/',
         views_public_enrollment.PublicEnrollmentStartView.as_view(),
         name='start'),
]
