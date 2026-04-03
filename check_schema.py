import os
import sys
import django
from django.apps import apps

def check_schema():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacy_admin.settings')
    django.setup()
    
    # Get the Scheme model
    Scheme = apps.get_model('schemes', 'Scheme')
    
    # Print model fields
    print("\n=== Model Fields ===")
    for field in Scheme._meta.fields:
        print(f"{field.name}: {field.get_internal_type()}")
    
    # Print database columns
    print("\n=== Database Columns ===")
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info('schemes_scheme')")
        columns = cursor.fetchall()
        for column in columns:
            print(f"{column[1]}: {column[2]}")
    
    # Check for any pending migrations
    print("\n=== Pending Migrations ===")
    from django.core.management import call_command
    call_command('showmigrations', 'schemes')

if __name__ == "__main__":
    check_schema()
