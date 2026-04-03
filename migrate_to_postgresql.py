#!/usr/bin/env python
"""
PostgreSQL Migration Script
Automates the migration from SQLite to PostgreSQL
"""

import os
import sys
import django
import json
import psycopg2
from pathlib import Path
from django.core.management import call_command

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
django.setup()

from django.conf import settings
from django.db import connections


def get_env_value(key, default=None):
    """Get environment variable using python-decouple config"""
    from decouple import config
    return config(key, default=default, cast=str)


def check_current_db():
    """Check current database configuration"""
    db_config = settings.DATABASES['default']
    engine = db_config['ENGINE']
    
    if 'sqlite' in engine:
        return 'sqlite', db_config['NAME']
    elif 'postgresql' in engine:
        return 'postgresql', {
            'NAME': db_config['NAME'],
            'USER': db_config['USER'],
            'PASSWORD': db_config['PASSWORD'],
            'HOST': db_config['HOST'],
            'PORT': db_config['PORT']
        }
    else:
        return 'unknown', None


def dump_sqlite_data(output_file='fixtures/full_dump.json'):
    """Export all data from SQLite as JSON"""
    print(f"📋 Dumping SQLite data to {output_file}...")
    
    # Create fixtures directory if it doesn't exist
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        call_command('dumpdata', '--indent=2', stdout=open(output_file, 'w'))
        print(f"✅ Successfully dumped {output_file}")
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        print(f"   Total records: {len(data)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to dump data: {e}")
        return False


def test_postgresql_connection(host, port, user, password, database):
    """Test if we can connect to PostgreSQL"""
    print(f"\n🔌 Testing PostgreSQL connection to {host}:{port}...")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        conn.close()
        print("✅ Successfully connected to PostgreSQL!")
        return True
    except psycopg2.OperationalError as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        return False


def create_postgresql_database(host, port, user, password, database):
    """Create PostgreSQL database if it doesn't exist"""
    print(f"\n🗄️  Creating PostgreSQL database '{database}'...")
    
    try:
        # Connect to postgres default database
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (database,))
        if cursor.fetchone():
            print(f"ℹ️  Database '{database}' already exists")
        else:
            cursor.execute(f"CREATE DATABASE {database}")
            print(f"✅ Created database '{database}'")
        
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error as e:
        print(f"❌ Failed to create database: {e}")
        return False


def apply_migrations():
    """Apply Django migrations"""
    print("\n🔄 Applying Django migrations...")
    
    try:
        call_command('migrate', verbosity=2, skip_checks=True)
        print("✅ Successfully applied migrations")
        return True
    except Exception as e:
        print(f"❌ Failed to apply migrations: {e}")
        return False


def load_data_from_fixture(input_file='fixtures/full_dump.json'):
    """Load data from JSON fixture into PostgreSQL"""
    print(f"\n📥 Loading data from {input_file}...")
    
    if not os.path.exists(input_file):
        print(f"❌ Fixture file not found: {input_file}")
        return False
    
    try:
        call_command('loaddata', input_file, verbosity=2)
        print(f"✅ Successfully loaded data from {input_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return False


def verify_migration():
    """Verify the migration by checking record counts"""
    print("\n📊 Verifying migration...")
    
    try:
        from members.models import Member, Policy
        from payments.models import Payment, PaymentReceipt
        from claims.models import Claim
        from accounts.models import User
        from branches.models import Branch
        from schemes.models import Scheme
        
        stats = {
            'Users': User.objects.count(),
            'Members': Member.objects.count(),
            'Policies': Policy.objects.count(),
            'Payments': Payment.objects.count(),
            'Payment Receipts': PaymentReceipt.objects.count(),
            'Claims': Claim.objects.count(),
            'Branches': Branch.objects.count(),
            'Schemes': Scheme.objects.count(),
        }
        
        print("\n📈 Data in PostgreSQL:")
        for model, count in stats.items():
            print(f"   {model}: {count}")
        
        total = sum(stats.values())
        print(f"\n   Total Records: {total}")
        
        if total > 0:
            print("✅ Migration appears successful!")
            return True
        else:
            print("⚠️  Warning: No data found in PostgreSQL. Migration may have failed.")
            return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    """Main migration workflow"""
    print("=" * 70)
    print("PostgreSQL Migration Script")
    print("=" * 70)
    
    # Step 1: Check current database
    print("\n📍 Current Configuration:")
    current_type, current_config = check_current_db()
    print(f"   Database: {current_type}")
    
    if current_type == 'postgresql':
        print("⚠️  Already using PostgreSQL! Skipping migration.")
        return
    
    # Step 2: Get PostgreSQL configuration from environment
    print("\n⚙️  Reading PostgreSQL configuration from .env...")
    
    pg_host = get_env_value('DB_HOST', 'localhost')
    pg_port = get_env_value('DB_PORT', '5432')
    pg_user = get_env_value('DB_USER', 'postgres')
    pg_password = get_env_value('DB_PASSWORD', '')
    pg_database = get_env_value('DB_NAME', 'legacyadmin')
    
    if not pg_password:
        print("❌ DB_PASSWORD not set in .env file!")
        print("   Please add DB_PASSWORD=your_password to .env")
        return
    
    print(f"   Host: {pg_host}")
    print(f"   Port: {pg_port}")
    print(f"   User: {pg_user}")
    print(f"   Database: {pg_database}")
    
    # Step 3: Test PostgreSQL connection
    if not test_postgresql_connection(pg_host, pg_port, pg_user, pg_password, pg_database):
        print("\n❌ Cannot connect to PostgreSQL. Steps to fix:")
        print("   1. Ensure PostgreSQL is installed and running")
        print("   2. Verify credentials in .env are correct")
        print("   3. Check that DB_HOST and DB_PORT are accessible")
        return
    
    # Step 4: Create database if needed
    if not create_postgresql_database(pg_host, pg_port, pg_user, pg_password, pg_database):
        return
    
    # Step 5: Dump SQLite data
    if not dump_sqlite_data():
        return
    
    # Step 6: Apply migrations
    if not apply_migrations():
        return
    
    # Step 7: Load data
    if not load_data_from_fixture():
        print("\n⚠️  Data loading failed. You may need to debug or reload from backup.")
        return
    
    # Step 8: Verify
    verify_migration()
    
    print("\n" + "=" * 70)
    print("✅ Migration Complete!")
    print("=" * 70)
    print("\n✨ Your application is now using PostgreSQL!")
    print("   Next steps:")
    print("   1. Test the application thoroughly")
    print("   2. Set up automated backups with pg_dump")
    print("   3. Monitor database performance")
    print("   4. Keep db.sqlite3.backup as a safety backup")


if __name__ == '__main__':
    main()
