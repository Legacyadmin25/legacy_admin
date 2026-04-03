import os
import logging
from celery import Celery
from celery.signals import task_failure, worker_ready, worker_shutting_down
from django.conf import settings

logger = logging.getLogger(__name__)

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings_prod')

# Create the Celery app
app = Celery('legacyadmin')

# Load task modules from all registered Django app configs
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Configure Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    'update-exchange-rates-daily': {
        'task': 'members.tasks.update_exchange_rates',
        'schedule': 86400.0,  # Once per day (in seconds)
        'args': (),
    },
    'send-pending-notifications-hourly': {
        'task': 'notifications.tasks.send_pending_notifications',
        'schedule': 3600.0,  # Once per hour (in seconds)
        'args': (),
    },
    'clean-expired-sessions-weekly': {
        'task': 'legacyadmin.tasks.clean_expired_sessions',
        'schedule': 604800.0,  # Once per week (in seconds)
        'args': (),
    },
    'database-backup-daily': {
        'task': 'legacyadmin.tasks.backup_database',
        'schedule': 86400.0,  # Once per day (in seconds)
        'args': (),
    },
    'retry-failed-payments-hourly': {
        'task': 'payments.tasks.retry_failed_payments',
        'schedule': 3600.0,  # Once per hour (in seconds)
        'args': (),
    },
}

# Configure task routes to different queues
app.conf.task_routes = {
    'members.tasks.*': {'queue': 'members'},
    'payments.tasks.*': {'queue': 'payments'},
    'notifications.tasks.*': {'queue': 'notifications'},
    'reports.tasks.*': {'queue': 'reports'},
    'legacyadmin.tasks.*': {'queue': 'default'},
}

# Configure task serialization
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']

# Set timezone
app.conf.enable_utc = True

# Configure task execution settings
app.conf.task_acks_late = True  # Tasks are acknowledged after execution
app.conf.worker_prefetch_multiplier = 1  # Don't prefetch more than one task
app.conf.task_reject_on_worker_lost = True  # Reject tasks when worker connection is lost
app.conf.task_time_limit = 3600  # 1 hour time limit per task
app.conf.task_soft_time_limit = 3000  # Soft limit of 50 minutes (10 min grace period)

# Configure task result backend
app.conf.result_backend = settings.CELERY_RESULT_BACKEND
app.conf.result_expires = 86400  # Results expire after 1 day

# Add task retry settings
app.conf.task_default_retry_delay = 60  # 1 minute delay before retrying
app.conf.task_max_retries = 3  # Maximum of 3 retries

# Configure logging
app.conf.worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
app.conf.worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"


@task_failure.connect
def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo, **kw):
    """
    Log task failures and optionally send alerts.
    """
    logger.error(
        f"Task {task_id} failed: {exception}\nArgs: {args}\nKwargs: {kwargs}\n{einfo}",
        exc_info=True
    )
    
    # If Sentry is configured, ensure the error is captured with task context
    try:
        import sentry_sdk
        sentry_sdk.set_context("task", {
            "id": task_id,
            "args": args,
            "kwargs": kwargs,
        })
        sentry_sdk.capture_exception(exception)
    except ImportError:
        pass


@worker_ready.connect
def worker_ready_handler(**kwargs):
    """
    Handler called when a worker is ready to receive tasks.
    """
    logger.info("Celery worker is ready to receive tasks")
    
    # Warm up caches on worker startup
    try:
        from legacyadmin.cache import warm_up_caches
        warm_up_caches()
    except Exception as e:
        logger.error(f"Error warming up caches: {e}")


@worker_shutting_down.connect
def worker_shutting_down_handler(**kwargs):
    """
    Handler called when a worker is shutting down.
    Perform cleanup tasks here.
    """
    logger.info("Celery worker is shutting down")


@app.task(bind=True)
def debug_task(self):
    """
    Task for debugging Celery configuration.
    """
    logger.info(f'Request: {self.request!r}')
    return "Debug task completed successfully"
