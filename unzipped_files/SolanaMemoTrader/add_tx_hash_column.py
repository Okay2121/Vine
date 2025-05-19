"""
Script to add tx_hash column to Transaction table using direct PostgreSQL commands
"""

from app import app, db
from sqlalchemy import text
import os

def add_tx_hash_column():
    """
    Add tx_hash column to the Transaction table using raw SQL
    """
    try:
        print("Starting migration: Adding tx_hash column to Transaction table...")
        with app.app_context():
            # Use raw SQL to check if the column exists and add it if it doesn't
            with db.engine.connect() as conn:
                # Check if column exists
                result = conn.execute(text(
                    """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='transaction' 
                    AND column_name='tx_hash'
                    """
                ))
                
                if result.fetchone() is None:
                    # Add the column
                    conn.execute(text(
                        """
                        ALTER TABLE "transaction" 
                        ADD COLUMN tx_hash VARCHAR(128)
                        """
                    ))
                    conn.commit()
                    print("Migration successful: Added tx_hash column to Transaction table.")
                else:
                    print("Column 'tx_hash' already exists in the Transaction table. No migration needed.")
            
        print("Transaction migration complete.")
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    add_tx_hash_column()