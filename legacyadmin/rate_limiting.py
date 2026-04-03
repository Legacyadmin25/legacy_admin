import time
import logging
import functools
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when a rate limit is exceeded"""
    pass


def get_client_ip(request):
    """Get the client's real IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the list (client's real IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class RateLimit:
    """
    Rate limiting implementation based on Redis.
    Uses a sliding window algorithm for more accurate rate limiting.
    """
    
    def __init__(self, key_prefix, limit, period, block_time=None):
        """
        Initialize a new rate limit.
        
        Args:
            key_prefix: Prefix for the Redis key
            limit: Maximum number of requests allowed in the period
            period: Time period in seconds
            block_time: Time to block requests after limit is exceeded (in seconds)
        """
        self.key_prefix = key_prefix
        self.limit = limit
        self.period = period
        self.block_time = block_time or period * 2  # Default block time is twice the period
    
    def _get_cache_key(self, identifier):
        """Get the cache key for this rate limit and identifier"""
        return f"ratelimit:{self.key_prefix}:{identifier}"
    
    def _get_block_key(self, identifier):
        """Get the block cache key for this rate limit and identifier"""
        return f"ratelimit:block:{self.key_prefix}:{identifier}"
    
    def is_blocked(self, identifier):
        """Check if the identifier is currently blocked"""
        return bool(cache.get(self._get_block_key(identifier)))
    
    def increment(self, identifier):
        """
        Increment the rate limit counter for the identifier.
        
        Args:
            identifier: The identifier (e.g., IP address, user ID)
            
        Returns:
            Tuple of (current_count, is_allowed)
        """
        now = time.time()
        window_key = self._get_cache_key(identifier)
        block_key = self._get_block_key(identifier)
        
        # Check if currently blocked
        if cache.get(block_key):
            return self.limit + 1, False
        
        pipe = cache.client.pipeline()
        
        # Clean up old requests from the window
        pipe.zremrangebyscore(window_key, 0, now - self.period)
        
        # Add current request to the window
        pipe.zadd(window_key, {str(now): now})
        
        # Get the number of requests in the current window
        pipe.zcard(window_key)
        
        # Set the expiration on the window
        pipe.expire(window_key, self.period)
        
        # Execute the pipeline
        _, _, current, _ = pipe.execute()
        
        # Check if the limit is exceeded and block if necessary
        is_allowed = current <= self.limit
        if not is_allowed:
            # Block the identifier for block_time seconds
            cache.set(block_key, 1, self.block_time)
            logger.warning(
                f"Rate limit exceeded for {identifier} on {self.key_prefix}. "
                f"Blocked for {self.block_time} seconds."
            )
        
        return current, is_allowed


def rate_limit_decorator(key_prefix, limit, period, block_time=None, get_identifier=None):
    """
    Decorator to apply rate limiting to a view function.
    
    Args:
        key_prefix: Prefix for the rate limit key
        limit: Maximum number of requests allowed in the period
        period: Time period in seconds
        block_time: Time to block requests after limit is exceeded (in seconds)
        get_identifier: Function to extract the identifier from the request
                        (defaults to client IP address)
    
    Example usage:
        @rate_limit_decorator('api_login', limit=5, period=60)
        def login_view(request):
            # This view is rate limited to 5 requests per minute per IP
            ...
    """
    rate_limiter = RateLimit(key_prefix, limit, period, block_time)
    
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get the identifier (default to client IP)
            identifier = get_identifier(request) if get_identifier else get_client_ip(request)
            
            # Skip rate limiting for staff/admin users if configured
            if getattr(settings, 'RATE_LIMIT_EXCLUDE_STAFF', False) and request.user.is_staff:
                return view_func(request, *args, **kwargs)
            
            # Check if blocked
            if rate_limiter.is_blocked(identifier):
                message = _("Too many requests. Please try again later.")
                
                # Return an appropriate response based on request type
                if request.headers.get('Accept', '').startswith('application/json'):
                    return JsonResponse({
                        'error': 'rate_limit_exceeded',
                        'message': message
                    }, status=429)
                return HttpResponse(message, status=429)
            
            # Increment the rate limit counter
            current, is_allowed = rate_limiter.increment(identifier)
            
            # Set rate limit headers on the response
            response = view_func(request, *args, **kwargs)
            response['X-RateLimit-Limit'] = str(limit)
            response['X-RateLimit-Remaining'] = str(max(0, limit - current))
            response['X-RateLimit-Reset'] = str(int(time.time() + period))
            
            # If not allowed, modify the response
            if not is_allowed:
                message = _("Too many requests. Please try again later.")
                
                # Return an appropriate response based on request type
                if request.headers.get('Accept', '').startswith('application/json'):
                    return JsonResponse({
                        'error': 'rate_limit_exceeded',
                        'message': message
                    }, status=429)
                return HttpResponse(message, status=429)
            
            return response
        return wrapped_view
    return decorator


# Default rate limiters for common endpoints
def api_rate_limit(view_func):
    """Rate limit for API endpoints: 60 requests per minute per IP"""
    return rate_limit_decorator('api', 60, 60)(view_func)


def login_rate_limit(view_func):
    """Rate limit for login: 5 attempts per minute per IP, block for 15 minutes on exceeding"""
    return rate_limit_decorator('login', 5, 60, 900)(view_func)


def registration_rate_limit(view_func):
    """Rate limit for registration: 3 attempts per hour per IP"""
    return rate_limit_decorator('registration', 3, 3600)(view_func)


def password_reset_rate_limit(view_func):
    """Rate limit for password reset: 3 attempts per hour per IP"""
    return rate_limit_decorator('password_reset', 3, 3600)(view_func)
