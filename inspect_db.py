import sqlite3
import os
from django.conf import settings

def inspect_database():
    # Get the database path
    db_path = settings.DATABASES['default']['NAME']
    print(f"Inspecting database at: {db_path}")
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTables in database:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Get the schema for schemes_scheme table
    print("\nSchema for schemes_scheme table:")
    cursor.execute("PRAGMA table_info('schemes_scheme');")
    columns = cursor.fetchall()
    for column in columns:
        print(f"- {column[1]} ({column[2]}) - {'NOT NULL' if column[3] else 'NULLABLE'}")
    
    # Check for any foreign key constraints
    print("\nForeign keys in schemes_scheme:")
    cursor.execute("PRAGMA foreign_key_list('schemes_scheme');")
    fks = cursor.fetchall()
    if fks:
        for fk in fks:
            print(f"- {fk[3]} -> {fk[2]}.{fk[4]}")
    else:
        print("No foreign key constraints found")
    
    # Check for any indexes
    print("\nIndexes on schemes_scheme:")
    cursor.execute("PRAGMA index_list('schemes_scheme');")
    indexes = cursor.fetchall()
    if indexes:
        for index in indexes:
            index_name = index[1]
            cursor.execute(f"PRAGMA index_info('{index_name}');")
            cols = cursor.fetchall()
            col_names = [col[2] for col in cols]
            print(f"- {index_name}: {', '.join(col_names)}")
    else:
        print("No indexes found")
    
    conn.close()

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacy_admin.settings')
    import django
    django.setup()
    inspect_database()
