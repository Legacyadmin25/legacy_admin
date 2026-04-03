from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Inspect the Scheme model and database schema'

    def handle(self, *args, **options):
        # Print model fields
        from schemes.models import Scheme
        
        self.stdout.write("=== Model Fields ===")
        for field in Scheme._meta.fields:
            self.stdout.write(f"{field.name}: {field.get_internal_type()}")
        
        # Print database columns
        self.stdout.write("\n=== Database Columns ===")
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info('schemes_scheme')")
            columns = cursor.fetchall()
            for column in columns:
                self.stdout.write(f"{column[1]}: {column[2]}")
        
        # Check for any pending migrations
        self.stdout.write("\n=== Pending Migrations ===")
        from django.core.management import call_command
        call_command('showmigrations', 'schemes')
