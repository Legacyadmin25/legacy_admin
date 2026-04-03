import re
import logging
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enhance security for the Legacy Admin application.
    Implements various security measures including:
    - Rate limiting for login attempts
    - IP blacklisting
    - Additional security headers
    - Suspicious request detection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Initialize lists of patterns to block
        self.sql_injection_patterns = [
            r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
            r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
            r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
            r"exec(\s|\+)+(s|x)p\w+",
        ]
        
        self.xss_patterns = [
            r"<[^\w<>]*(?:[^<>\"'\s]*:)?[^\w<>]*(?:\W*s\W*c\W*r\W*i\W*p\W*t|\W*f\W*o\W*r\W*m|\W*s\W*t\W*y\W*l\W*e|\W*o\W*b\W*j\W*e\W*c\W*t|\W*a\W*p\W*p\W*l\W*e\W*t|\W*e\W*m\W*b\W*e\W*d|\W*i\W*f\W*r\W*a\W*m\W*e|\W*f\W*r\W*a\W*m\W*e|\W*l\W*a\W*y\W*e\W*r|\W*i\W*l\W*a\W*y\W*e\W*r|\W*l\W*i\W*n\W*k|\W*m\W*e\W*t\W*a|\W*i\W*m\W*a\W*g\W*e|\W*v\W*i\W*d\W*e\W*o|\W*a\W*u\W*d\W*i\W*o|\W*b\W*i\W*n\W*d\W*i\W*n\W*g\W*s|\W*s\W*e\W*t|\W*i\W*s\W*i\W*n\W*d\W*e\W*x|\W*a\W*n\W*i\W*m\W*a\W*t\W*e)[^\w<>]*(?:\W*o\W*n\W*[a-z]{3,}|\W*f\W*o\W*r\W*[a-z]{3,}|\W*s\W*t\W*y\W*l\W*e|\W*t\W*y\W*p\W*e|\W*h\W*r\W*e\W*f|\W*s\W*r\W*c)=[^<>]*(?:\W*a\W*l\W*e\W*r\W*t|\W*p\W*r\W*o\W*m\W*p\W*t|\W*c\W*o\W*n\W*f\W*i\W*r\W*m|\W*e\W*v\W*a\W*l|\W*d\W*o\W*c\W*u\W*m\W*e\W*n\W*t|\W*t\W*h\W*i\W*s|\W*w\W*i\W*n\W*d\W*o\W*w|\W*t\W*o\W*p|\W*p\W*a\W*r\W*e\W*n\W*t|\W*o\W*p\W*e\W*n\W*e\W*r|\W*s\W*e\W*l\W*f)",
            r"j\W*a\W*v\W*a\W*s\W*c\W*r\W*i\W*p\W*t\W*:",
            r"e\W*x\W*p\W*r\W*e\W*s\W*s\W*i\W*o\W*n\W*\(",
        ]
        
        # Compile patterns
        self.sql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_injection_patterns]
        self.xss_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.xss_patterns]
        
        # Get IP whitelist from settings if available
        self.admin_ip_whitelist = getattr(settings, 'ADMIN_IP_WHITELIST', [])
        
        # Rate limiting settings
        self.max_login_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        self.login_lockout_period = getattr(settings, 'LOGIN_LOCKOUT_PERIOD', 300)  # seconds
        
        # Admin URL pattern
        self.admin_url_pattern = re.compile(r'^/admin/')
        
        logger.info("Security middleware initialized")
    
    def process_request(self, request):
        """
        Process the request before the view is called.
        Check for malicious patterns, rate limiting, etc.
        """
        # Get client IP
        ip_address = self._get_client_ip(request)
        
        # Check IP blacklist
        if self._is_ip_blacklisted(ip_address):
            logger.warning(f"Blocked request from blacklisted IP: {ip_address}")
            return HttpResponseForbidden("Access denied")
        
        # Check if this is an admin URL and if IP is allowed
        if self._is_admin_url(request.path) and not self._is_ip_allowed_for_admin(ip_address):
            logger.warning(f"Unauthorized admin access attempt from IP: {ip_address}")
            return HttpResponseForbidden("Admin access denied from this IP")
        
        # Check for rate limiting on login attempts
        if self._is_login_url(request) and request.method == 'POST':
            if self._is_login_rate_limited(ip_address):
                logger.warning(f"Login rate limited for IP: {ip_address}")
                return HttpResponseForbidden("Too many login attempts. Please try again later.")
        
        # Check for suspicious request patterns
        if self._is_suspicious_request(request):
            logger.warning(f"Blocked suspicious request from IP: {ip_address}, path: {request.path}")
            return HttpResponseForbidden("Request blocked for security reasons")
        
        # Allow the request to continue
        return None
    
    def process_response(self, request, response):
        """
        Process the response after the view is called.
        Set security headers if they're not already set.
        """
        # Set security headers if not already set
        if not response.has_header('X-Content-Type-Options'):
            response['X-Content-Type-Options'] = 'nosniff'
        
        if not response.has_header('X-Frame-Options'):
            response['X-Frame-Options'] = getattr(settings, 'X_FRAME_OPTIONS', 'DENY')
        
        if not response.has_header('X-XSS-Protection'):
            response['X-XSS-Protection'] = '1; mode=block'
        
        if not response.has_header('Referrer-Policy'):
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add Content-Security-Policy header if not already set
        if not response.has_header('Content-Security-Policy') and hasattr(settings, 'CSP_DEFAULT_SRC'):
            csp_policies = []
            csp_settings = {k: v for k, v in settings.__dict__.items() if k.startswith('CSP_')}
            
            for key, value in csp_settings.items():
                if isinstance(value, (list, tuple)):
                    directive = key[4:].lower().replace('_', '-')
                    policy_value = ' '.join(value)
                    csp_policies.append(f"{directive} {policy_value}")
            
            if csp_policies:
                response['Content-Security-Policy'] = '; '.join(csp_policies)
        
        # Check if this was a failed login attempt and update rate limiting
        if self._is_login_url(request) and request.method == 'POST' and hasattr(request, 'user') and not request.user.is_authenticated:
            ip_address = self._get_client_ip(request)
            self._record_failed_login(ip_address)
        
        return response
    
    def _get_client_ip(self, request):
        """
        Get the client's real IP address, handling proxy servers.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the list (client's real IP)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _is_ip_blacklisted(self, ip):
        """
        Check if an IP is blacklisted.
        """
        # Check the cache for blacklisted IPs
        return cache.get(f'blacklist_ip_{ip}', False)
    
    def _is_admin_url(self, path):
        """
        Check if the requested path is for admin.
        """
        return bool(self.admin_url_pattern.match(path))
    
    def _is_ip_allowed_for_admin(self, ip):
        """
        Check if an IP is allowed to access admin.
        """
        # If no whitelist is defined, allow all IPs
        if not self.admin_ip_whitelist:
            return True
        
        # Check if the IP is in the whitelist
        return ip in self.admin_ip_whitelist
    
    def _is_login_url(self, request):
        """
        Check if this is a login request.
        """
        return request.path == '/accounts/login/' or request.path == '/admin/login/'
    
    def _is_login_rate_limited(self, ip):
        """
        Check if login attempts for this IP should be rate limited.
        """
        key = f'login_attempts_{ip}'
        attempts = cache.get(key, 0)
        return attempts >= self.max_login_attempts
    
    def _record_failed_login(self, ip):
        """
        Record a failed login attempt for rate limiting.
        """
        key = f'login_attempts_{ip}'
        attempts = cache.get(key, 0)
        attempts += 1
        
        # If this exceeds the threshold, set the timeout longer
        if attempts >= self.max_login_attempts:
            cache.set(key, attempts, self.login_lockout_period)
            logger.warning(f"IP {ip} has been rate limited for login attempts")
        else:
            cache.set(key, attempts, 60)  # 1 minute for regular tracking
    
    def _is_suspicious_request(self, request):
        """
        Check for suspicious patterns in the request.
        """
        # Check query parameters for SQL injection or XSS
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            for pattern in self.sql_patterns:
                if pattern.search(query_string):
                    logger.warning(f"SQL injection attempt detected in query string: {query_string}")
                    return True
            
            for pattern in self.xss_patterns:
                if pattern.search(query_string):
                    logger.warning(f"XSS attempt detected in query string: {query_string}")
                    return True
        
        # Check POST data for SQL injection or XSS
        if request.method == 'POST':
            post_data = request.POST.dict()
            for key, value in post_data.items():
                if key in ('password', 'password1', 'password2'):
                    continue  # Skip password fields
                
                if isinstance(value, str):
                    for pattern in self.sql_patterns:
                        if pattern.search(value):
                            logger.warning(f"SQL injection attempt detected in POST data: {key}")
                            return True
                    
                    for pattern in self.xss_patterns:
                        if pattern.search(value):
                            logger.warning(f"XSS attempt detected in POST data: {key}")
                            return True
        
        # Check for suspicious user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if not user_agent or 'sqlmap' in user_agent.lower() or 'nikto' in user_agent.lower():
            logger.warning(f"Suspicious user agent detected: {user_agent}")
            return True
        
        return False


# Helper function to register an IP to be blacklisted
def blacklist_ip(ip_address, duration=3600):
    """
    Blacklist an IP address for a specified duration.
    
    Args:
        ip_address: The IP address to blacklist
        duration: The duration in seconds to blacklist the IP (default: 1 hour)
    """
    cache.set(f'blacklist_ip_{ip_address}', True, duration)
    logger.warning(f"IP {ip_address} has been blacklisted for {duration} seconds")


# Helper function to remove an IP from the blacklist
def remove_from_blacklist(ip_address):
    """
    Remove an IP address from the blacklist.
    
    Args:
        ip_address: The IP address to remove from the blacklist
    """
    cache.delete(f'blacklist_ip_{ip_address}')
    logger.info(f"IP {ip_address} has been removed from the blacklist")


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to audit all data modifications for compliance purposes.
    Logs create, update, and delete operations.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("Audit log middleware initialized")
    
    def process_response(self, request, response):
        # Only log if we have a logged-in user
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                # Extract user information
                user_info = {
                    'username': request.user.username,
                    'id': request.user.id,
                    'email': request.user.email,
                }
                
                # Log the action
                log_data = {
                    'user': user_info,
                    'ip': self._get_client_ip(request),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'timestamp': timezone.now().isoformat(),
                }
                
                # Include query parameters if present
                if request.GET:
                    log_data['query_params'] = dict(request.GET)
                
                # Include POST data for auditing, excluding sensitive fields
                if request.method == 'POST':
                    safe_post_data = {}
                    for key, value in request.POST.items():
                        if key not in ('password', 'password1', 'password2', 'token', 'api_key', 'secret'):
                            safe_post_data[key] = value
                    
                    if safe_post_data:
                        log_data['post_data'] = safe_post_data
                
                # Log the audit entry
                logger.info(f"AUDIT: {log_data}")
        
        return response
    
    def _get_client_ip(self, request):
        """
        Get the client's real IP address, handling proxy servers.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the list (client's real IP)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
