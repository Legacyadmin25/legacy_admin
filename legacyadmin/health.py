import logging
import time
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.conf import settings
from redis.exceptions import RedisError
import redis

logger = logging.getLogger(__name__)


@never_cache
def health_check(request):
    """
    Health check endpoint for monitoring and liveness probes.
    Checks database connectivity, Redis connectivity, and overall application health.
    Returns:
        JsonResponse: Health status with components status and overall health
    """
    start_time = time.time()
    
    # Initialize health status dictionary
    health_status = {
        "status": "ok",
        "components": {
            "database": {"status": "ok"},
            "redis": {"status": "ok"},
            "application": {"status": "ok"},
        },
        "version": getattr(settings, "VERSION", "unknown"),
        "environment": getattr(settings, "ENVIRONMENT", "unknown"),
    }
    
    # Check database connectivity
    try:
        db_conn = connections['default']
        db_conn.cursor()
    except OperationalError as e:
        health_status["components"]["database"] = {
            "status": "error",
            "message": str(e)
        }
        health_status["status"] = "error"
        logger.error(f"Health check failed: Database error - {str(e)}")
    
    # Check Redis connectivity if used
    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
        except RedisError as e:
            health_status["components"]["redis"] = {
                "status": "error",
                "message": str(e)
            }
            health_status["status"] = "error"
            logger.error(f"Health check failed: Redis error - {str(e)}")
    
    # Add response time
    health_status["response_time_ms"] = int((time.time() - start_time) * 1000)
    
    # Determine overall status code
    status_code = 200 if health_status["status"] == "ok" else 503
    
    return JsonResponse(health_status, status=status_code)


@never_cache
def readiness_probe(request):
    """
    Readiness probe for Kubernetes and other orchestration systems.
    Checks if the application is ready to serve traffic.
    """
    return JsonResponse({"status": "ready"}, status=200)


@never_cache
def liveness_probe(request):
    """
    Liveness probe for Kubernetes and other orchestration systems.
    Checks if the application is alive and should continue running.
    """
    return JsonResponse({"status": "alive"}, status=200)
