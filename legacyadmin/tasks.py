import os
import logging
import subprocess
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from django.contrib.sessions.models import Session
from celery import shared_task
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(
    name="legacyadmin.tasks.backup_database",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True
)
def backup_database(self):
    """
    Create a backup of the database and upload it to S3.
    Uses the backup_database.sh script from the scripts directory.
    """
    try:
        logger.info("Starting database backup task")
        
        # Path to the backup script
        script_path = os.path.join(settings.BASE_DIR, 'scripts', 'backup_database.sh')
        
        # Make sure the script is executable
        os.chmod(script_path, 0o755)
        
        # Run the backup script
        result = subprocess.run(
            [script_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"Database backup completed successfully: {result.stdout}")
        return {"status": "success", "message": "Database backup completed successfully"}
    except subprocess.CalledProcessError as e:
        logger.error(f"Database backup failed: {e.stderr}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Unexpected error during database backup: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name="legacyadmin.tasks.clean_expired_sessions",
    bind=True
)
def clean_expired_sessions(self):
    """
    Clean up expired sessions from the database.
    """
    try:
        logger.info("Starting session cleanup task")
        
        # Delete expired sessions
        count, _ = Session.objects.filter(expire_date__lt=timezone.now()).delete()
        
        logger.info(f"Deleted {count} expired sessions")
        return {"status": "success", "count": count}
    except Exception as e:
        logger.error(f"Error cleaning expired sessions: {str(e)}")
        raise


@shared_task(
    name="legacyadmin.tasks.clear_old_audit_logs",
    bind=True
)
def clear_old_audit_logs(self, days=90):
    """
    Clear audit logs older than the specified number of days.
    
    Args:
        days: Number of days to keep logs for (default: 90)
    """
    try:
        logger.info(f"Starting audit log cleanup task (keeping {days} days)")
        
        # Import here to avoid circular imports
        from audit.models import AuditLog
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Delete old logs
        count, _ = AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()
        
        logger.info(f"Deleted {count} old audit logs")
        return {"status": "success", "count": count}
    except Exception as e:
        logger.error(f"Error clearing old audit logs: {str(e)}")
        raise


@shared_task(
    name="legacyadmin.tasks.generate_sitemap",
    bind=True
)
def generate_sitemap(self):
    """
    Generate the sitemap.xml file for SEO.
    """
    try:
        logger.info("Starting sitemap generation task")
        
        # Use Django's built-in sitemap generation command
        call_command('ping_google')
        
        logger.info("Sitemap generated successfully")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error generating sitemap: {str(e)}")
        raise


@shared_task(
    name="legacyadmin.tasks.rebuild_search_index",
    bind=True
)
def rebuild_search_index(self):
    """
    Rebuild the search index for improved search performance.
    """
    try:
        logger.info("Starting search index rebuild task")
        
        # Rebuild the search index
        call_command('rebuild_index', '--noinput')
        
        logger.info("Search index rebuilt successfully")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error rebuilding search index: {str(e)}")
        raise


@shared_task(
    name="legacyadmin.tasks.check_system_health",
    bind=True
)
def check_system_health(self):
    """
    Perform system health checks and report issues.
    """
    try:
        logger.info("Starting system health check task")
        
        # Run Django health checks
        call_command('check', '--deploy')
        
        # Check database connection
        from django.db import connections
        for conn_name in connections:
            conn = connections[conn_name]
            conn.ensure_connection()
            if not conn.is_usable():
                raise Exception(f"Database connection {conn_name} is not usable")
        
        # Check cache connection
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise Exception("Cache is not working properly")
        
        # Check for low disk space (if on Linux/Unix)
        if os.name != 'nt':  # Skip on Windows
            df = subprocess.run(
                ['df', '-h', '.'], 
                capture_output=True, 
                text=True,
                check=True
            )
            logger.info(f"Disk space: {df.stdout}")
        
        logger.info("System health check completed successfully")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        
        # Attempt to send an alert
        try:
            # Import here to avoid circular imports
            from notifications.tasks import send_admin_alert
            send_admin_alert.delay(
                subject="System Health Check Failed",
                message=f"The system health check failed: {str(e)}"
            )
        except ImportError:
            logger.error("Could not import send_admin_alert task")
        
        raise
