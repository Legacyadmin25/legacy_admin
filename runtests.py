#!/usr/bin/env python
"""
Test runner script that configures the environment before running tests.
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.db import connections

def run_tests(*test_args):
    if not test_args:
        test_args = ['members.tests']

    # Configure Django settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'legacyadmin.settings'
    
    # Set test environment variables
    os.environ['TESTING'] = 'True'
    os.environ['SECRET_KEY'] = 'test-secret-key-123'
    os.environ['DEBUG'] = 'True'
    
    # Override database settings for tests
    os.environ['DATABASES'] = '{"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}'
    
    # Initialize Django
    django.setup()
    
    # Create test database
    from django.core.management import call_command
    call_command('migrate', '--noinput')
    
    # Import TestRunner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=False)
    
    # Run tests
    failures = test_runner.run_tests(test_args)
    
    # Close all database connections
    for conn in connections.all():
        conn.close()
    
    sys.exit(bool(failures))

if __name__ == '__main__':
    run_tests(*sys.argv[1:])
