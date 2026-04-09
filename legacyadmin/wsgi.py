"""
WSGI config for legacyadmin project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application


# Shared hosting has low process/thread limits; keep BLAS backends single-threaded.
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')

os.environ.setdefault(
	'DJANGO_SETTINGS_MODULE',
	os.getenv('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings'),
)

application = get_wsgi_application()
