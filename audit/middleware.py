"""
Audit middleware for capturing request context (user, IP, user agent).
Stores request information in thread-local storage for use by audit signals.
"""
import threading
from django.utils.deprecation import MiddlewareMixin

# Thread-local storage for request context
_thread_local = threading.local()


def get_request_context():
    """Get the current request context from thread-local storage"""
    return getattr(_thread_local, 'request', None)


def set_request_context(request):
    """Store request context in thread-local storage"""
    _thread_local.request = request


def clear_request_context():
    """Clear request context from thread-local storage"""
    if hasattr(_thread_local, 'request'):
        del _thread_local.request


class AuditContextMiddleware(MiddlewareMixin):
    """
    Middleware to capture and store request context for audit logging.
    Makes request object available to signals and models without passing it everywhere.
    """
    
    def process_request(self, request):
        """Store request in thread-local storage at the start of request processing"""
        set_request_context(request)
        return None
    
    def process_response(self, request, response):
        """Clear request from thread-local storage at the end of request processing"""
        clear_request_context()
        return response
    
    def process_exception(self, request, exception):
        """Clear request from thread-local storage even if exception occurs"""
        clear_request_context()
        return None
