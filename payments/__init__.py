"""
Payments application for managing payment processing and tracking.

This app handles payment processing, receipt generation, and payment history.
"""

# This will make sure the app is imported when Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
