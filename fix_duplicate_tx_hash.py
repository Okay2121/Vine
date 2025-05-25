"""
Fix Duplicate Transaction Hash Issue
This script fixes the UNIQUE constraint error when processing trades
"""
import sqlite3
import os
from datetime import datetime

def fix_duplicate_transaction_issue():
    """Fix the duplicate transaction hash issue"""
    
    # Connect to the database
    db_path = "instance/solana_memecoin_bot.db"
    if not os.path.exists(db_path):
        print("Database file not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for duplicate transaction hashes
        cursor.execute("""
            SELECT tx_hash, COUNT(*) as count 
            FROM "transaction" 
            WHERE tx_hash IS NOT NULL 
            GROUP BY tx_hash 
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        print(f"Found {len(duplicates)} duplicate transaction hashes")
        
        for tx_hash, count in duplicates:
            print(f"Duplicate: {tx_hash} appears {count} times")
            
            # Keep the first occurrence, delete the rest
            cursor.execute("""
                DELETE FROM "transaction" 
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) 
                    FROM "transaction" 
                    WHERE tx_hash = ?
                ) AND tx_hash = ?
            """, (tx_hash, tx_hash))
            
            deleted = cursor.rowcount
            print(f"Deleted {deleted} duplicate entries for {tx_hash}")
        
        # Commit the changes
        conn.commit()
        print("✅ Fixed duplicate transaction hash issues")
        
        # Now check the transaction that's causing the current error
        cursor.execute("SELECT * FROM \"transaction\" WHERE tx_hash = 'def456'")
        existing = cursor.fetchone()
        
        if existing:
            print(f"Found existing transaction with hash 'def456': {existing}")
            # Delete this test transaction so the trade can proceed
            cursor.execute("DELETE FROM \"transaction\" WHERE tx_hash = 'def456'")
            conn.commit()
            print("Deleted the problematic test transaction")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error fixing duplicate transactions: {e}")
        return False

if __name__ == "__main__":
    fix_duplicate_transaction_issue()