"""
Fix Database Columns - Add missing admin_id column to trading_position table
"""
import sqlite3
import os

def fix_database_columns():
    """Add missing columns to the trading_position table"""
    
    # Determine database path
    if os.environ.get("DATABASE_URL"):
        print("Using PostgreSQL database")
        # For PostgreSQL, we'd use psycopg2, but error suggests SQLite
        return False
    else:
        db_path = "instance/solana_memecoin_bot.db"
        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
            return False
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(trading_position)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {columns}")
        
        # Add missing columns if they don't exist
        columns_to_add = [
            ("admin_id", "TEXT"),
            ("exit_price", "REAL")
        ]
        
        for column_name, column_type in columns_to_add:
            if column_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE trading_position ADD COLUMN {column_name} {column_type}")
                    print(f"✓ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"Column {column_name} already exists")
                    else:
                        print(f"Error adding {column_name}: {e}")
            else:
                print(f"Column {column_name} already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(trading_position)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns: {updated_columns}")
        
        conn.close()
        print("✓ Database columns updated successfully!")
        return True
        
    except Exception as e:
        print(f"Error updating database: {e}")
        return False

if __name__ == "__main__":
    fix_database_columns()