from django.utils import timezone
from django.conf import settings
import logging
from datetime import timedelta

from members.models_incomplete import IncompleteApplication

logger = logging.getLogger(__name__)

def cleanup_stale_applications(days_threshold=30, mark_as_abandoned=True):
    """
    Cleanup stale incomplete applications.
    
    Args:
        days_threshold (int): Number of days of inactivity to consider an application stale
        mark_as_abandoned (bool): If True, mark applications as abandoned; if False, delete them
    
    Returns:
        int: Number of applications processed
    """
    cutoff_date = timezone.now() - timedelta(days=days_threshold)
    stale_applications = IncompleteApplication.objects.filter(
        last_activity__lt=cutoff_date,
        status__in=['draft', 'in_progress']
    )
    
    count = stale_applications.count()
    
    if mark_as_abandoned:
        # Mark as abandoned instead of deleting
        stale_applications.update(status='abandoned')
        logger.info(f"Marked {count} stale applications as abandoned (inactive for {days_threshold} days)")
    else:
        # Delete the applications
        stale_applications.delete()
        logger.info(f"Deleted {count} stale applications (inactive for {days_threshold} days)")
    
    return count


def auto_cleanup_stale_applications():
    """
    Automatically clean up stale applications based on settings.
    This function can be called by a scheduled task or management command.
    """
    # Get settings from Django settings or use defaults
    days_threshold = getattr(settings, 'AUTOSAVE_STALE_DAYS', 30)
    mark_as_abandoned = getattr(settings, 'AUTOSAVE_MARK_ABANDONED', True)
    
    return cleanup_stale_applications(
        days_threshold=days_threshold,
        mark_as_abandoned=mark_as_abandoned
    )
