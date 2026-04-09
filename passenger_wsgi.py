import os
import sys


APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Shared hosting has low process/thread limits; keep BLAS backends single-threaded.
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')

if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    os.getenv('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings'),
)

from legacyadmin.wsgi import application
