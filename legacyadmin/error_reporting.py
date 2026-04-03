import logging
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def configure_sentry(dsn=None, environment=None, traces_sample_rate=0.1):
    """
    Configure Sentry error reporting with appropriate integrations and settings.
    
    Args:
        dsn: Sentry DSN URL (defaults to SENTRY_DSN environment variable)
        environment: Environment name (dev, staging, prod)
        traces_sample_rate: Performance tracing sample rate (0.0 to 1.0)
    """
    # Get DSN from environment if not provided
    dsn = dsn or os.environ.get('SENTRY_DSN')
    
    # Skip if no DSN provided
    if not dsn:
        logger.warning("Sentry DSN not provided, error reporting disabled")
        return
    
    # Get environment from environment variable if not provided
    environment = environment or os.environ.get('ENVIRONMENT', 'unknown')
    
    # Configure Sentry with all available integrations
    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            ),
        ],
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,  # Don't include personally identifiable information
        
        # Set max breadcrumbs for better debugging context
        max_breadcrumbs=50,
        
        # Configure HTTP proxy if needed (for environments behind firewalls)
        http_proxy=os.environ.get('HTTP_PROXY'),
        https_proxy=os.environ.get('HTTPS_PROXY'),
        
        # Enable performance monitoring
        enable_tracing=True,
        
        # Set release ID based on git commit or version
        release=os.environ.get('RELEASE_ID', 'local'),
        
        # Sanitize sensitive data from request bodies
        before_send=before_send,
        
        # Add server-name to identify specific instances
        server_name=os.environ.get('HOSTNAME', 'unknown'),
    )
    
    logger.info(f"Sentry initialized for environment: {environment}")


def before_send(event, hint):
    """
    Process and sanitize event data before sending to Sentry.
    Remove sensitive data such as passwords, tokens, etc.
    
    Args:
        event: The event to be sent to Sentry
        hint: Additional information about the event
    
    Returns:
        The processed event or None to skip sending
    """
    # Skip certain errors if needed
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, (
            # Don't report these exceptions
            KeyboardInterrupt,
            SystemExit,
        )):
            return None
    
    # Sanitize sensitive data from request bodies
    if 'request' in event and 'data' in event['request']:
        sanitize_request_data(event['request']['data'])
    
    return event


def sanitize_request_data(data):
    """
    Sanitize sensitive fields in request data.
    
    Args:
        data: The request data to sanitize
    """
    if not isinstance(data, dict):
        return
    
    # List of fields to sanitize
    sensitive_fields = {
        'password', 'password1', 'password2', 'new_password', 'old_password',
        'token', 'access_token', 'refresh_token', 'auth_token', 'api_key',
        'secret', 'credit_card', 'card_number', 'cvv', 'ssn', 'id_number',
        'passport_number', 'secret_key', 'private_key', 'authorization',
    }
    
    # Replace sensitive data with [REDACTED]
    for key in list(data.keys()):
        if key.lower() in sensitive_fields:
            data[key] = '[REDACTED]'
        elif isinstance(data[key], dict):
            sanitize_request_data(data[key])


def capture_exception(exception, context=None, level='error', tags=None, user=None):
    """
    Capture an exception with additional context.
    
    Args:
        exception: The exception to capture
        context: Additional context data
        level: Severity level ('error', 'warning', 'info', etc.)
        tags: Additional tags for categorizing the error
        user: User information
    """
    if not sentry_sdk.Hub.current.client:
        logger.warning("Sentry not initialized, exception not captured")
        return
    
    with sentry_sdk.push_scope() as scope:
        # Set the level
        scope.level = level
        
        # Add custom tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        # Add user information
        if user:
            scope.set_user(user)
        
        # Add additional context
        if context:
            scope.set_context("additional_data", context)
        
        # Capture the exception
        sentry_sdk.capture_exception(exception)
