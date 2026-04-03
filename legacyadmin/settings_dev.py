import os
from pathlib import Path
import environ

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost'])
)

# Import base settings
from .settings_base import *

# Set debug to True in development
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# ─── Development-specific settings ───────────────────────────────────────────
# Use console email backend in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Turn off security features in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# Use local file storage for static and media files in development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# ─── Logging Configuration ────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'debug.log',
            'formatter': 'verbose'
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
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Make sure logs directory exists
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# ─── Django Debug Toolbar ─────────────────────────────────────────────────────
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']

# ─── CORS settings (more permissive in dev) ──────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
