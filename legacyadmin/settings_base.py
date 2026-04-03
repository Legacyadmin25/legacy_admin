import os
from pathlib import Path
import environ

# Initialize environment variables
env = environ.Env()

# ─── Base directory ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Installed apps ──────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django Core Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third-Party Apps
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    'import_export',
    'django_filters',
    'storages',
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
    
    # Local Apps
    'schemes',
    'members',
    'settings_app',
    'supplements',
    'sms_templates',
]

# ─── Middleware ──────────────────────────────────────────────────────────────
MIDDLEWARE = [
    # Security middlewares first
    'legacyadmin.security_middleware.SecurityMiddleware',  # Custom security middleware
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    
    # Session and authentication
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # Messages and other standard middlewares
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Monitoring and logging middlewares
    'legacyadmin.metrics.PrometheusMiddleware',
    'legacyadmin.security_middleware.AuditLogMiddleware',  # Audit logging
]

ROOT_URLCONF = 'legacyadmin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'legacyadmin.wsgi.application'

# ─── Database ───────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': env.int('DB_CONN_MAX_AGE', default=60),
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# ─── Password validation ───────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# ─── Static files ──────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ─── Media files ───────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Default primary key field type ───────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Login/Logout URLS ──────────────────────────────────────────────────────
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ─── Crispy Forms ───────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ─── Email settings ─────────────────────────────────────────────────────────
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# ─── Celery settings ─────────────────────────────────────────────────────────
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ─── Cache settings ──────────────────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ─── REST Framework settings ───────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ─── CORS settings ──────────────────────────────────────────────────────────
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# ─── Twilio settings ────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER', default='')

# ─── OpenAI settings ────────────────────────────────────────────────────────
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')

# ─── Security settings ──────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', default=True)
SECURE_BROWSER_XSS_FILTER = env.bool('SECURE_BROWSER_XSS_FILTER', default=True)
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', default='DENY')
