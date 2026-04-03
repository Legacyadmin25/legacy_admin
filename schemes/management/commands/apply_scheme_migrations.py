from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Applies scheme migrations for the bank field changes'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Add bank_id column if it doesn't exist
            cursor.execute("""
                PRAGMA table_info(schemes_scheme);
            """)
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'bank_id' not in columns:
                self.stdout.write('Adding bank_id column to schemes_scheme table...')
                cursor.execute("""
                    ALTER TABLE schemes_scheme ADD COLUMN bank_id INTEGER REFERENCES branches_bank(id) NULL;
                """)
                self.stdout.write(self.style.SUCCESS('Added bank_id column'))
            
            # Make branch_code nullable
            self.stdout.write('Updating branch_code to be nullable...')
            cursor.execute("""
                PRAGMA foreign_keys=off;
                BEGIN TRANSACTION;
                CREATE TABLE schemes_scheme_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    prefix VARCHAR(20) NULL,
                    registration_no VARCHAR(100) NOT NULL,
                    fsp_number VARCHAR(50) NOT NULL,
                    email VARCHAR(254) NOT NULL,
                    extra_email VARCHAR(254) NULL,
                    phone VARCHAR(20) NOT NULL,
                    logo VARCHAR(100) NULL,
                    terms TEXT NOT NULL,
                    debit_order_no VARCHAR(50) NOT NULL,
                    bank_id INTEGER NULL REFERENCES branches_bank(id),
                    branch_code VARCHAR(20) NULL,
                    account_no VARCHAR(50) NOT NULL,
                    account_type VARCHAR(50) NOT NULL,
                    address VARCHAR(255) NULL,
                    city VARCHAR(100) NULL,
                    province VARCHAR(100) NULL,
                    village VARCHAR(100) NULL,
                    country VARCHAR(100) NULL,
                    postal_code VARCHAR(20) NULL,
                    allow_auto_policy_number BOOLEAN NOT NULL,
                    active BOOLEAN NOT NULL,
                    branch_id INTEGER NOT NULL REFERENCES branches_branch(id),
                    FOREIGN KEY(branch_id) REFERENCES branches_branch(id) DEFERRABLE INITIALLY DEFERRED,
                    FOREIGN KEY(bank_id) REFERENCES branches_bank(id) DEFERRABLE INITIALLY DEFERRED
                );
                
                INSERT INTO schemes_scheme_new SELECT * FROM schemes_scheme;
                DROP TABLE schemes_scheme;
                ALTER TABLE schemes_scheme_new RENAME TO schemes_scheme;
                
                -- Recreate indexes
                CREATE INDEX schemes_scheme_branch_id_1234abcd ON schemes_scheme (branch_id);
                CREATE INDEX schemes_scheme_bank_id_5678efgh ON schemes_scheme (bank_id);
                
                COMMIT;
                PRAGMA foreign_keys=on;
            """)
            self.stdout.write(self.style.SUCCESS('Updated database schema'))
            
            # If we have any schemes, try to migrate the bank data
            cursor.execute("SELECT COUNT(*) FROM schemes_scheme")
            if cursor.fetchone()[0] > 0:
                self.stdout.write('Migrating existing bank data...')
                cursor.execute("""
                    UPDATE schemes_scheme 
                    SET bank_id = (
                        SELECT id FROM branches_bank 
                        WHERE name = schemes_scheme.bank_name 
                        LIMIT 1
                    )
                    WHERE bank_id IS NULL AND bank_name IS NOT NULL;
                """)
                self.stdout.write(self.style.SUCCESS('Migrated bank data'))
            
            # Drop the bank_name column if it exists
            cursor.execute("PRAGMA table_info(schemes_scheme);")
            columns = [col[1] for col in cursor.fetchall()]
            if 'bank_name' in columns:
                self.stdout.write('Dropping bank_name column...')
                cursor.execute("""
                    PRAGMA foreign_keys=off;
                    BEGIN TRANSACTION;
                    CREATE TABLE schemes_scheme_new AS SELECT id, name, prefix, registration_no, 
                        fsp_number, email, extra_email, phone, logo, terms, debit_order_no,
                        bank_id, branch_code, account_no, account_type, address, city, province,
                        village, country, postal_code, allow_auto_policy_number, active, branch_id
                    FROM schemes_scheme;
                    DROP TABLE schemes_scheme;
                    ALTER TABLE schemes_scheme_new RENAME TO schemes_scheme;
                    
                    -- Recreate indexes
                    CREATE INDEX schemes_scheme_branch_id_1234abcd ON schemes_scheme (branch_id);
                    CREATE INDEX schemes_scheme_bank_id_5678efgh ON schemes_scheme (bank_id);
                    
                    COMMIT;
                    PRAGMA foreign_keys=on;
                """)
                self.stdout.write(self.style.SUCCESS('Dropped bank_name column'))
        
        self.stdout.write(self.style.SUCCESS('Successfully applied all migrations'))
