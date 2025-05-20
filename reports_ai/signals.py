from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import ReportQuery, ReportExecutionLog, SavedReport
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=ReportQuery)
def log_report_query_save(sender, instance, created, **kwargs):
    """Log when a report query is saved"""
    if created:
        logger.info(f"New report query created by {instance.user.email}: {instance.original_query}")
    else:
        logger.debug(f"Report query updated: {instance.id} by {instance.user.email}")


@receiver(post_save, sender=ReportExecutionLog)
def log_report_execution(sender, instance, created, **kwargs):
    """Log when a report is executed"""
    if created:
        logger.info(
            f"Report execution started: {instance.report_query.id} - "
            f"Status: {instance.status}, User: {instance.report_query.user.email}"
        )


@receiver(post_save, sender=SavedReport)
def log_saved_report(sender, instance, created, **kwargs):
    """Log when a report is saved"""
    if created:
        logger.info(
            f"Report saved: {instance.name} by {instance.user.email}, "
            f"Query ID: {instance.report_query.id}"
        )


@receiver(post_delete, sender=SavedReport)
def log_deleted_report(sender, instance, **kwargs):
    """Log when a saved report is deleted"""
    logger.info(f"Report deleted: {instance.name} by {instance.user.email}")


@receiver(pre_save, sender=ReportExecutionLog)
def calculate_execution_time(sender, instance, **kwargs):
    """Calculate execution time for report runs"""
    if instance.pk:
        # If the instance already exists, get the previous version
        old_instance = ReportExecutionLog.objects.get(pk=instance.pk)
        if old_instance.status == 'pending' and instance.status in ['success', 'error']:
            # If status changed from pending to success/error, calculate execution time
            instance.execution_time = (timezone.now() - instance.executed_at).total_seconds()
            
            # Log completion
            if instance.status == 'success':
                logger.info(
                    f"Report execution completed in {instance.execution_time:.2f}s: "
                    f"{instance.report_query.id}, Records: {instance.record_count}"
                )
            else:
                logger.error(
                    f"Report execution failed after {instance.execution_time:.2f}s: "
                    f"{instance.report_query.id}, Error: {instance.error_message}"
                )


def connect_signals():
    """Connect all signals"""
    # Signals are connected using the @receiver decorator
    pass
