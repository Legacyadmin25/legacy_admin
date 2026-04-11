"""
WSGI config for legacyadmin project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# Load .env for local dev; cPanel injects variables natively so this is a no-op on the server.
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent / '.env'
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except ImportError:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')

application = get_wsgi_application()
