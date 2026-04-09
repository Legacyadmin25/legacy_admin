import os
from pathlib import Path

# cPanel injects environment variables directly. Locally, `.env` values can be
# provided by the shell or the active process environment.


def env(name, default=None):
    return os.getenv(name, default)


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name, default=0):
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return int(value)


def env_csv(name, default=''):
    value = os.getenv(name, default)
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]

# ─── Base directory ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DEV_FIELD_ENCRYPTION_KEY = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='


def should_use_local_sqlite():
    engine = env('DB_ENGINE', '').strip()
    name = env('DB_NAME', '').strip()
    placeholder_names = {'', 'your_cpanel_db_name', 'legacyadmin'}

    if not engine:
        return True
    if engine == 'django.db.backends.sqlite3':
        return True
    if engine == 'django.db.backends.mysql' and name in placeholder_names:
        return True
    return False

# ─── SECURITY ─────────────────────────────────────────────────────────────────
# Load from environment, with sensible defaults for development
SECRET_KEY = env('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = env_bool('DEBUG', False)
ALLOWED_HOSTS = env_csv('ALLOWED_HOSTS', 'localhost,127.0.0.1')

# ─── HTTPS & SECURITY HEADERS ─────────────────────────────────────────────────
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', False)
SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)

# ─── FIELD ENCRYPTION KEY FOR PII (CRITICAL: CHANGE THIS!) ────────────────────
# Generate a new key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"
# Store in .env as: FIELD_ENCRYPTION_KEY=<generated-key>
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', DEV_FIELD_ENCRYPTION_KEY)
# Note: In production, ensure a proper key is set in .env

# When going to production, in .env set:
# DEBUG=False
# SECURE_SSL_REDIRECT=True
# SESSION_COOKIE_SECURE=True
# CSRF_COOKIE_SECURE=True
# SECURE_HSTS_SECONDS=31536000

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
    'encrypted_model_fields',  # For PII encryption
    
    # Local Apps - Accounts must come first as it defines the custom user model
    'accounts.apps.AccountsConfig',
    
    # Other Local Apps
    'import_data',
    'members',
    'dashboard',
    'users',
    'schemes',
    'settings_app',
    'reports',
    'theme',
    'supplements',
    'sms_templates',
    'payments',
    'claims',
    'branches',
    'members.communications',
    'audit',  # For audit logging
]

# ─── Middleware (WhiteNoise right after SecurityMiddleware) ────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Audit logging middleware - captures request context for audit trail
    'audit.middleware.AuditContextMiddleware',
    # Custom middleware for auto-save functionality
    'members.middleware.AutoSaveSessionMiddleware',
    'members.middleware.AgentDetectionMiddleware',
]

ROOT_URLCONF = 'legacyadmin.urls'

# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # The root templates folder
        ],
        'APP_DIRS': True,  # This ensures Django looks for templates inside each app's 'templates' folder
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'settings_app.context_processors.settings_context',  # Custom context processor
                'accounts.context_processors.user_permissions',     # User permissions context processor
                'django.template.context_processors.media',         # For media files
                'django.template.context_processors.static',        # For static files
            ],
        },
    },
]

WSGI_APPLICATION = 'legacyadmin.wsgi.application'

# ─── Database ────────────────────────────────────────────────────────────────
if should_use_local_sqlite():
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': env('SQLITE_DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': env('DB_ENGINE', 'django.db.backends.mysql'),
            'NAME': env('DB_NAME', 'your_cpanel_db_name'),
            'USER': env('DB_USER', 'your_cpanel_db_user'),
            'PASSWORD': env('DB_PASSWORD', 'your_db_password'),
            'HOST': env('DB_HOST', 'localhost'),
            'PORT': env('DB_PORT', '3306'),
        }
    }
# DB_USER=postgres
# DB_PASSWORD=<secure-password>
# DB_HOST=your-db-host.com
# DB_PORT=5432

# ─── Custom User Model ──────────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

# ─── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True


# ─── Static files ─────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'theme' / 'static',
]
USE_MANIFEST_STATICFILES = env_bool('USE_MANIFEST_STATICFILES', not should_use_local_sqlite())
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if USE_MANIFEST_STATICFILES
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)

# ─── Media files ──────────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── OpenAI API Key for AI Reporting ──────────────────────────────────────────
OPENAI_API_KEY = env('OPENAI_API_KEY', '')

# ─── Custom settings ──────────────────────────────────────────────────────────
EASYPAY_URL = env('EASYPAY_URL', 'https://www.easypay.co.za/api/v1/payment/create')
EASYPAY_API_KEY = env('EASYPAY_API_KEY', '')
EASY_PAY_RECEIVER_ID = env('EASY_PAY_RECEIVER_ID', '5047')
EASY_PAY_ACCOUNT_LENGTH = env_int('EASY_PAY_ACCOUNT_LENGTH', 12)
EASY_PAY_OUTPUT_DIR = env('EASY_PAY_OUTPUT_DIR', '/tmp/')
EASYPAY_API_VERSION = env('EASYPAY_API_VERSION', '1.0')
EASYPAY_PROCESS = env('EASYPAY_PROCESS', 'Legacy Admin')

# ─── SMS Configuration ────────────────────────────────────────────────────────
SMS_API_KEY = env('SMS_API_KEY', '')
SMS_API_SECRET = env('SMS_API_SECRET', '')
BULKSMS_API_TOKEN = env('BULKSMS_API_TOKEN', '')
BULKSMS_USERNAME = env('BULKSMS_USERNAME', '')
BULKSMS_PASSWORD = env('BULKSMS_PASSWORD', '')

# ─── Stripe (for future use) ──────────────────────────────────────────────────
STRIPE_TEST_PUBLIC_KEY = env('STRIPE_TEST_PUBLIC_KEY', '')
STRIPE_TEST_SECRET_KEY = env('STRIPE_TEST_SECRET_KEY', '')

# ─── Twilio (for WhatsApp) ────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER', '')

# Django Admin Interface Customization (For branding)
DJANGO_ADMIN_INTERFACE = {
    'CUSTOM_LOGO': 'path/to/your/logo.png',
    'THEME_COLOR': 'blue',  # Set theme colors here
}

# Django Payments Configuration
PAYMENT_HOST = 'https://www.example.com/payment'

# Django CMS or Wagtail (Pick one)
# 'wagtail' for modern CMS or 'django-cms' for a more traditional CMS
CMS_INSTALLED_APPS = [
    'wagtail',  # Or 'django-cms'
]

# ─── Default primary key field type ───────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Ensure the accounts app is first in INSTALLED_APPS
if 'accounts.apps.AccountsConfig' in INSTALLED_APPS:
    INSTALLED_APPS.remove('accounts.apps.AccountsConfig')
INSTALLED_APPS.insert(0, 'accounts.apps.AccountsConfig')


# ─── Session Settings ───────────────────────────────────────────────────────
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True

# ─── Crispy Forms ───────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ─── Email settings for PDF attachments and notifications
EMAIL_BACKEND = env('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', 'localhost')
EMAIL_PORT = env_int('EMAIL_PORT', 587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'noreply@legacyadmin.co.za')
SITE_URL = env('SITE_URL', 'http://localhost:8000')

# Optional short-link integration for enrollment links
SHORT_LINK_TIMEOUT = env_int('SHORT_LINK_TIMEOUT', 10)
BITLY_ACCESS_TOKEN = env('BITLY_ACCESS_TOKEN', '')
TINYURL_API_TOKEN = env('TINYURL_API_TOKEN', '')
REDIS_URL = env('REDIS_URL', '')

# ─── OpenAI API Configuration ───────────────────────────────────────────────
OPENAI_API_KEY = env('OPENAI_API_KEY', '')

# Set a default model if not specified in environment
DEFAULT_OPENAI_MODEL = env('DEFAULT_OPENAI_MODEL', 'gpt-4o')

# Visible marker to confirm which deployment/build is serving the UI
DEPLOYMENT_MARKER = env('DEPLOYMENT_MARKER', 'workspace-reporthub-20260409')

# ─── Authentication redirects ─────────────────────────────────────────────────
# Always use literal URL paths for login/logout so Django never tries to reverse() them:
LOGIN_URL           = '/accounts/login/'
LOGIN_REDIRECT_URL  = '/'                # after a successful login
LOGOUT_REDIRECT_URL = '/accounts/login/'  # after logging out

# ─── Audit Logging Configuration ──────────────────────────────────────────────
# List of models to exclude from automatic audit logging
AUDIT_EXCLUDED_MODELS = [
    'audit.AuditLog',           # Don't log audit logs themselves (avoid recursion)
    'audit.DataAccess',         # Don't log data access logs
    'admin.LogEntry',           # Don't log Django admin actions
    'sessions.Session',         # Don't log session changes
]

# List of sensitive models that should have all actions logged
AUDIT_SENSITIVE_MODELS = [
    'auth.User',                # Track all user changes (passwords, permissions)
    'members.Member',           # Track member information changes
    'members.Policy',           # Track policy status and premium changes
    'claims.Claim',             # Track claim creation, status changes, approval
    'payments.Payment',         # Track payment creation and status changes
]

# Audit log retention (days) - old logs beyond this period can be archived
AUDIT_LOG_RETENTION_DAYS = 365  # Keep 1 year of audit logs

