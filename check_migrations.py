import os
import django
from django.db import connection

def check_migrations():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacy_admin.settings')
    django.setup()
    
    # Check applied migrations
    print("\n=== Applied Migrations ===")
    with connection.cursor() as cursor:
        cursor.execute("SELECT name, applied FROM django_migrations WHERE app = 'schemes' ORDER BY applied")
        for row in cursor.fetchall():
            print(f"{row[1]}: {row[0]}")
    
    # Check model state
    from django.apps import apps
    Scheme = apps.get_model('schemes', 'Scheme')
    
    print("\n=== Model Fields ===")
    for field in Scheme._meta.fields:
        print(f"{field.name}: {field.get_internal_type()}")
    
    # Check database columns
    print("\n=== Database Columns ===")
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info('schemes_scheme')")
        columns = cursor.fetchall()
        for col in columns:
            print(f"{col[1]}: {col[2]}")

if __name__ == "__main__":
    check_migrations()
