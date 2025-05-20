import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── Base directory ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECURITY ─────────────────────────────────────────────────────────────────
SECRET_KEY = 'django-insecure-=$7w@h(o6j9$m645o06z)w0@i#0g(q4e9+x)4_m$v49j6$m*m'
DEBUG = True
ALLOWED_HOSTS = ['*']

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
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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

# ─── OpenAI API Key for AI Reporting ─────
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# ─── Authentication redirects ─────────────────────────────────────────────────
LOGIN_URL           = 'login'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_REDIRECT_URL  = '/'    # after successful login, go to /

# ─── Custom settings ──────────────────────────────────────────────────────────
EASYPAY_URL             = "https://www.easypay.co.za/api/v1/payment/create"
EASYPAY_API_KEY         = "your-easypay-api-key"
EASY_PAY_RECEIVER_ID    = "5047"
EASY_PAY_ACCOUNT_LENGTH = 12
EASY_PAY_OUTPUT_DIR     = "/path/to/output/"
EASYPAY_API_VERSION     = "1.0"
EASYPAY_PROCESS         = "Legacy Admin"

SMS_API_KEY    = "your-sms-api-key"
SMS_API_SECRET = "your-sms-api-secret"

STRIPE_TEST_PUBLIC_KEY = 'your-public-key'
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

# ─── Authentication Backends ────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'accounts.backends.RoleBasedModelBackend',
]

# Ensure the accounts app is first in INSTALLED_APPS
if 'accounts.apps.AccountsConfig' in INSTALLED_APPS:
    INSTALLED_APPS.remove('accounts.apps.AccountsConfig')
INSTALLED_APPS.insert(0, 'accounts.apps.AccountsConfig')

# ─── Login/Logout URLs ──────────────────────────────────────────────────────
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:profile'
LOGOUT_REDIRECT_URL = 'accounts:login'

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
