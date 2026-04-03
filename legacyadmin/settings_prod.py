import os
from pathlib import Path
import environ

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['legacyadmin.example.com'])
)

# Import base settings
from .settings_base import *

# Production environment has debugging disabled
DEBUG = False  # Force this to be False in production, regardless of env var
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# ─── Storage settings ─────────────────────────────────────────────────────────
# Use S3 for static and media files in production
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN', default=f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com')
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=2592000',  # 30 days cache
}
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False

STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# ─── Security settings (very strict for production) ───────────────────────────
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# ─── Content Security Policy ───────────────────────────────────────────────────
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "https:", "http:")
CSP_FONT_SRC = ("'self'", "https://cdn.jsdelivr.net")
CSP_CONNECT_SRC = ("'self'",)

# ─── Sentry Error Reporting ───────────────────────────────────────────────────
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ],
    traces_sample_rate=0.1,  # 10% of transactions will be traced
    send_default_pii=False,
    environment="production",
)

# ─── Logging Configuration ────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s", "path": "%(pathname)s", "lineno": %(lineno)d}',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/legacyadmin/application.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'legacyadmin': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# ─── CORS settings ──────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'https://legacyadmin.example.com',
    'https://api.legacyadmin.example.com',
]

# ─── Cache settings ──────────────────────────────────────────────────────────
# Use Redis for caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'legacyadmin_prod'
    }
}

# Use cache for sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ─── Admin settings ──────────────────────────────────────────────────────────
ADMIN_URL = env('ADMIN_URL', default='admin/')  # Customize admin URL for security

# ─── Email settings (must use production values) ───────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@legacyadmin.example.com')
SERVER_EMAIL = env('SERVER_EMAIL', default='server@legacyadmin.example.com')
