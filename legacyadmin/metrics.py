import time
from django.http import HttpResponse
from django.db import connection
from django.conf import settings
from prometheus_client import (
    generate_latest, CONTENT_TYPE_LATEST,
    Counter, Histogram, Gauge, Summary
)

# Define Prometheus metrics
REQUESTS = Counter(
    'legacyadmin_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUESTS_LATENCY = Histogram(
    'legacyadmin_http_request_latency_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

DB_QUERY_LATENCY = Histogram(
    'legacyadmin_db_query_latency_seconds',
    'Database query latency in seconds',
    ['query_type']
)

ACTIVE_USERS = Gauge(
    'legacyadmin_active_users',
    'Number of active users in the system'
)

POLICIES_CREATED = Counter(
    'legacyadmin_policies_created_total',
    'Total number of policies created'
)

POLICIES_BY_STATUS = Gauge(
    'legacyadmin_policies_by_status',
    'Number of policies by status',
    ['status']
)

CELERY_TASKS_EXECUTED = Counter(
    'legacyadmin_celery_tasks_executed_total',
    'Total number of Celery tasks executed',
    ['task_name', 'status']
)

CELERY_TASK_LATENCY = Histogram(
    'legacyadmin_celery_task_latency_seconds',
    'Celery task latency in seconds',
    ['task_name']
)


def metrics_view(request):
    """
    Expose Prometheus metrics.
    """
    # Update active users metric (example of how you'd update a gauge)
    try:
        from django.contrib.auth.models import User
        from django.utils import timezone
        from datetime import timedelta
        
        # Count users active in the last 24 hours (based on last_login)
        cutoff = timezone.now() - timedelta(hours=24)
        active_count = User.objects.filter(last_login__gte=cutoff).count()
        ACTIVE_USERS.set(active_count)
        
        # Count policies by status (example)
        from schemes.models import Policy
        for status_choice in Policy.STATUS_CHOICES:
            status_code = status_choice[0]
            count = Policy.objects.filter(status=status_code).count()
            POLICIES_BY_STATUS.labels(status=status_code).set(count)
            
    except Exception as e:
        # Don't let errors in gathering metrics break the endpoint
        pass
    
    # Generate and return latest metrics
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


class PrometheusMiddleware:
    """
    Middleware to capture request metrics for Prometheus.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization

    def __call__(self, request):
        # Code to be executed for each request before the view is called
        start_time = time.time()
        
        # Process the request
        response = self.get_response(request)
        
        # Skip metrics for the metrics endpoint itself to avoid recursion
        if not request.path.startswith('/metrics'):
            # Record request latency
            latency = time.time() - start_time
            REQUESTS_LATENCY.labels(
                method=request.method,
                endpoint=request.resolver_match.view_name if getattr(request, 'resolver_match', None) else 'unknown'
            ).observe(latency)
            
            # Count the request
            REQUESTS.labels(
                method=request.method,
                endpoint=request.resolver_match.view_name if getattr(request, 'resolver_match', None) else 'unknown',
                status=response.status_code
            ).inc()
        
        return response
