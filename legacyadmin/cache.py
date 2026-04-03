import os
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def get_cache_timeout(cache_name):
    """Get the timeout for a specific cache"""
    cache_timeouts = getattr(settings, 'CACHE_TIMEOUTS', {
        'default': 300,             # 5 minutes
        'templates': 3600,          # 1 hour
        'statics': 86400,           # 1 day
        'api_results': 600,         # 10 minutes
        'underwriters': 3600,       # 1 hour
        'plans': 1800,              # 30 minutes
        'members': 600,             # 10 minutes
        'policies': 1200,           # 20 minutes
        'settings': 3600,           # 1 hour
        'reports': 1800,            # 30 minutes
        'user_permissions': 1800,   # 30 minutes
    })
    return cache_timeouts.get(cache_name, cache_timeouts.get('default', 300))


def invalidate_cache_keys_by_prefix(prefix):
    """
    Invalidate all cache keys that start with the given prefix.
    This is useful when we want to clear all caches related to a specific model.
    
    Args:
        prefix: The prefix to match for cache invalidation
    """
    try:
        # For Redis cache backend
        if hasattr(cache, 'keys'):
            keys = cache.keys(f"{prefix}*")
            if keys:
                cache.delete_many(keys)
                logger.info(f"Invalidated {len(keys)} cache entries with prefix '{prefix}'")
        # For other cache backends
        else:
            logger.warning(f"Cache key invalidation by prefix not supported for this cache backend")
    except Exception as e:
        logger.error(f"Error invalidating cache keys with prefix '{prefix}': {str(e)}")


def cache_func_result(prefix, timeout=None, args_as_key=False):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Prefix for the cache key
        timeout: Cache timeout in seconds (or None to use default)
        args_as_key: Whether to include function args in the cache key
        
    Example usage:
        @cache_func_result('underwriters', timeout=3600)
        def get_all_underwriters():
            return Underwriter.objects.all()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate a unique cache key based on function name and arguments
            if args_as_key and (args or kwargs):
                key_parts = [prefix, func.__name__]
                
                # Add args to key
                if args:
                    key_parts.extend([str(arg) for arg in args])
                
                # Add kwargs to key, sorted by key for consistency
                if kwargs:
                    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                
                cache_key = ":".join(key_parts)
            else:
                cache_key = f"{prefix}:{func.__name__}"
            
            # Get cache timeout for this cache
            actual_timeout = timeout if timeout is not None else get_cache_timeout(prefix)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute the function and cache the result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, actual_timeout)
            return result
        return wrapper
    return decorator


def clear_all_caches():
    """Clear all caches - should be used with caution"""
    try:
        cache.clear()
        logger.info("All caches cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing all caches: {str(e)}")


def warm_up_caches():
    """
    Warm up commonly used caches on application startup.
    This helps prevent the "thundering herd" problem when the application
    restarts and multiple requests hit the database simultaneously.
    """
    logger.info("Warming up application caches...")
    
    try:
        # Import here to avoid circular imports
        from django.contrib.auth.models import Group, Permission
        from settings_app.models import Underwriter, Plan
        
        # Cache all groups and permissions
        Group.objects.all()
        Permission.objects.all()
        
        # Cache all underwriters and plans
        Underwriter.objects.all()
        Plan.objects.all()
        
        logger.info("Application caches warmed up successfully")
    except Exception as e:
        logger.error(f"Error warming up caches: {str(e)}")
