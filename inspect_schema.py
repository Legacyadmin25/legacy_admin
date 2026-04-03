import sqlite3
import os

def inspect_schema():
    db_path = os.path.join(os.getcwd(), 'db.sqlite3')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if schemes_scheme table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schemes_scheme';")
        if not cursor.fetchone():
            print("schemes_scheme table does not exist")
            return
        
        # Get table schema
        print("\n=== schemes_scheme table schema ===")
        cursor.execute("PRAGMA table_info('schemes_scheme')")
        columns = cursor.fetchall()
        for col in columns:
            print(f"{col[1]}: {col[2]} {'NOT NULL' if col[3] else 'NULL'} {'PRIMARY KEY' if col[5] else ''}")
        
        # Check for bank_name column
        bank_name_col = [col for col in columns if col[1] == 'bank_name']
        print("\nbank_name column exists:", bool(bank_name_col))
        
        # Check for bank_id column
        bank_id_col = [col for col in columns if col[1] == 'bank_id']
        print("bank_id column exists:", bool(bank_id_col))
        
        # Check applied migrations
        print("\n=== Applied migrations ===")
        cursor.execute("SELECT app, name, applied FROM django_migrations WHERE app='schemes' ORDER BY applied")
        for row in cursor.fetchall():
            print(f"{row[0]}: {row[1]} ({row[2]})")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    inspect_schema()
