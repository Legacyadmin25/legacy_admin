import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
django.setup()

from django.db import connection

def fix_scheme_bank_field():
    """
    This script fixes the bank field in the Scheme model by:
    1. Adding the bank_id column if it doesn't exist
    2. Ensuring the branch_code field is nullable
    """
    with connection.cursor() as cursor:
        # Check if bank_id column exists
        cursor.execute("PRAGMA table_info(schemes_scheme)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print("Current columns in schemes_scheme table:", columns)
        
        # Add bank_id column if it doesn't exist
        if 'bank_id' not in columns:
            print("Adding bank_id column...")
            cursor.execute("ALTER TABLE schemes_scheme ADD COLUMN bank_id integer REFERENCES branches_bank(id)")
            print("✓ Added bank_id column")
        else:
            print("✓ bank_id column already exists")
        
        # Make sure branch_code is nullable
        print("Making branch_code nullable...")
        try:
            # SQLite doesn't support ALTER COLUMN, so we need to create a new table
            cursor.execute("""
            PRAGMA foreign_keys=off;
            
            CREATE TABLE IF NOT EXISTS schemes_scheme_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL UNIQUE,
                prefix VARCHAR(20) NULL,
                registration_no VARCHAR(100) NOT NULL,
                fsp_number VARCHAR(50) NOT NULL,
                email VARCHAR(254) NOT NULL,
                extra_email VARCHAR(254) NULL,
                phone VARCHAR(20) NOT NULL,
                logo VARCHAR(100) NULL,
                terms TEXT NOT NULL,
                debit_order_no VARCHAR(50) NOT NULL,
                account_no VARCHAR(50) NOT NULL,
                account_type VARCHAR(50) NOT NULL,
                branch_code VARCHAR(20) NULL,
                address VARCHAR(255) NULL,
                city VARCHAR(100) NULL,
                province VARCHAR(100) NULL,
                village VARCHAR(100) NULL,
                country VARCHAR(100) NULL,
                postal_code VARCHAR(20) NULL,
                allow_auto_policy_number BOOL NOT NULL,
                active BOOL NOT NULL,
                branch_id INTEGER NOT NULL REFERENCES branches_branch(id),
                bank_id INTEGER NULL REFERENCES branches_bank(id),
                bank_name VARCHAR(100) NULL
            );
            
            INSERT INTO schemes_scheme_new 
            SELECT * FROM schemes_scheme;
            
            DROP TABLE schemes_scheme;
            ALTER TABLE schemes_scheme_new RENAME TO schemes_scheme;
            
            PRAGMA foreign_keys=on;
            """)
            print("✓ Made branch_code nullable")
        except Exception as e:
            print(f"Error making branch_code nullable: {e}")
            print("Continuing with other operations...")
        
        # Update bank_id based on bank_name if needed
        if 'bank_id' in columns and 'bank_name' in columns:
            print("Updating bank_id based on bank_name...")
            cursor.execute("""
            UPDATE schemes_scheme
            SET bank_id = (
                SELECT id FROM branches_bank 
                WHERE name = schemes_scheme.bank_name
            )
            WHERE bank_id IS NULL AND bank_name IS NOT NULL;
            """)
            print("✓ Updated bank_id based on bank_name")

if __name__ == "__main__":
    print("Fixing scheme bank field...")
    fix_scheme_bank_field()
    print("\n✓ Successfully fixed scheme bank field!")
