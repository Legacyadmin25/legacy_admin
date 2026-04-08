import os
import sys


APP_ROOT = os.path.dirname(os.path.abspath(__file__))

if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    os.getenv('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings'),
)

from legacyadmin.wsgi import application
