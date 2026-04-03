import sqlite3
import os

def check_database():
    # Path to the SQLite database
    db_path = os.path.join(os.getcwd(), 'db.sqlite3')
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schemes_scheme';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("Table 'schemes_scheme' does not exist in the database.")
            return
        
        # Get column info
        cursor.execute("PRAGMA table_info('schemes_scheme');")
        columns = cursor.fetchall()
        
        print("\n=== Columns in schemes_scheme ===")
        for col in columns:
            print(f"Column {col[1]}: Type={col[2]}, Nullable={'YES' if not col[3] else 'NO'}, Default={col[4]}")
        
        # Check for bank_name column
        bank_name_col = [col for col in columns if col[1] == 'bank_name']
        if bank_name_col:
            print("\nWARNING: 'bank_name' column still exists in the database.")
        else:
            print("\n'bank_name' column has been removed from the database.")
        
        # Check for foreign key to bank
        cursor.execute("PRAGMA foreign_key_list('schemes_scheme');")
        fks = cursor.fetchall()
        
        print("\n=== Foreign Keys ===")
        if fks:
            for fk in fks:
                print(f"FK: {fk[3]} -> {fk[2]}.{fk[4]}")
        else:
            print("No foreign key constraints found.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_database()
