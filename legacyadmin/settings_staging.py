import os
from pathlib import Path
import environ

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['staging.legacyadmin.example.com'])
)

# Import base settings
from .settings_base import *

# Staging environment is close to production but allows some debugging
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# ─── Storage settings ─────────────────────────────────────────────────────────
# Use S3 for static and media files in staging
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN', default=f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com')
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False

STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# ─── Security settings (moderately strict for staging) ───────────────────────
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=3600)  # 1 hour
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)

# ─── Sentry Error Reporting ───────────────────────────────────────────────────
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN', default=''),
    integrations=[DjangoIntegration(), CeleryIntegration()],
    traces_sample_rate=0.5,  # 50% of transactions will be traced
    send_default_pii=False,
    environment="staging",
)

# ─── Logging Configuration ────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s"}',
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
            'level': 'INFO',
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
    'https://staging.legacyadmin.example.com',
    'https://staging-api.legacyadmin.example.com',
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
        },
        'KEY_PREFIX': 'legacyadmin_staging'
    }
}
