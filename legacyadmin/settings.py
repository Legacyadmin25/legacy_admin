import os
from pathlib import Path
from decouple import config, Csv

# Load environment variables from .env file
load_dotenv = lambda: None  # Decouple handles this automatically

# ─── Base directory ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECURITY ─────────────────────────────────────────────────────────────────
# Load from environment, with sensible defaults for development
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')
DEBUG = config('DEBUG', default='False', cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ─── HTTPS & SECURITY HEADERS ─────────────────────────────────────────────────
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default='False', cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default='False', cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default='False', cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default='0', cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default='False', cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default='False', cast=bool)

# ─── FIELD ENCRYPTION KEY FOR PII (CRITICAL: CHANGE THIS!) ────────────────────
# Generate a new key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"
# Store in .env as: FIELD_ENCRYPTION_KEY=<generated-key>
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='dev-key-only-change-in-production')
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
    'reports_ai',  # For AI Reporting
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
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': BASE_DIR / 'db.sqlite3' if config('DB_ENGINE', default='django.db.backends.sqlite3') == 'django.db.backends.sqlite3' else config('DB_NAME', default='legacyadmin'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}

# For production with PostgreSQL, set in .env:
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=legacyadmin
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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─── Media files ──────────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── OpenAI API Key for AI Reporting ──────────────────────────────────────────
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# ─── Custom settings ──────────────────────────────────────────────────────────
EASYPAY_URL             = config('EASYPAY_URL', default="https://www.easypay.co.za/api/v1/payment/create")
EASYPAY_API_KEY         = config('EASYPAY_API_KEY', default='')
EASY_PAY_RECEIVER_ID    = config('EASY_PAY_RECEIVER_ID', default="5047")
EASY_PAY_ACCOUNT_LENGTH = config('EASY_PAY_ACCOUNT_LENGTH', default='12', cast=int)
EASY_PAY_OUTPUT_DIR     = config('EASY_PAY_OUTPUT_DIR', default="/tmp/")
EASYPAY_API_VERSION     = config('EASYPAY_API_VERSION', default="1.0")
EASYPAY_PROCESS         = config('EASYPAY_PROCESS', default="Legacy Admin")

# ─── SMS Configuration ────────────────────────────────────────────────────────
SMS_API_KEY    = config('SMS_API_KEY', default='')
SMS_API_SECRET = config('SMS_API_SECRET', default='')
BULKSMS_USERNAME = config('BULKSMS_USERNAME', default='')
BULKSMS_PASSWORD = config('BULKSMS_PASSWORD', default='')

# ─── Stripe (for future use) ──────────────────────────────────────────────────
STRIPE_TEST_PUBLIC_KEY = config('STRIPE_TEST_PUBLIC_KEY', default='')
STRIPE_TEST_SECRET_KEY = config('STRIPE_TEST_SECRET_KEY', default='')

# ─── Twilio (for WhatsApp) ────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')
STRIPE_TEST_SECRET_KEY = 'your-secret-key'

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
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'noreply@example.com'

# ─── OpenAI API Configuration ───────────────────────────────────────────────
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Set a default model if not specified in environment
DEFAULT_OPENAI_MODEL = os.getenv('DEFAULT_OPENAI_MODEL', 'gpt-3.5-turbo')

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

