"""
Fix Transaction Table Primary Key Sequence
==========================================
Fixes the duplicate key constraint error by resetting the sequence.
"""

import logging
from app import app, db
from sqlalchemy import text

logger = logging.getLogger(__name__)

def fix_transaction_sequence():
    """Fix the transaction table primary key sequence"""
    
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Get the current max ID in transaction table
                result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM transaction"))
                max_id = result.fetchone()[0]
                
                print(f"Current max transaction ID: {max_id}")
                
                # Get the sequence name
                result = conn.execute(text("""
                    SELECT pg_get_serial_sequence('transaction', 'id')
                """))
                sequence_name = result.fetchone()[0]
                
                if sequence_name:
                    print(f"Found sequence: {sequence_name}")
                    
                    # Reset sequence to max_id + 1
                    new_sequence_value = max_id + 1
                    conn.execute(text(f"SELECT setval('{sequence_name}', {new_sequence_value})"))
                    conn.commit()
                    
                    print(f"Reset sequence to: {new_sequence_value}")
                    
                    # Verify the fix
                    result = conn.execute(text(f"SELECT nextval('{sequence_name}')"))
                    next_val = result.fetchone()[0]
                    print(f"Next sequence value will be: {next_val}")
                    
                    return True
                else:
                    print("No sequence found for transaction.id")
                    return False
                    
        except Exception as e:
            print(f"Error fixing sequence: {e}")
            return False

def test_transaction_insert():
    """Test if transaction insert works after fix"""
    
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Try a test insert
                result = conn.execute(text("""
                    INSERT INTO transaction (user_id, transaction_type, amount, timestamp, status, notes)
                    VALUES (1, 'test', 0.01, NOW(), 'completed', 'sequence_test')
                    RETURNING id
                """))
                
                new_id = result.fetchone()[0]
                print(f"Test insert successful with ID: {new_id}")
                
                # Clean up test record
                conn.execute(text("DELETE FROM transaction WHERE notes = 'sequence_test'"))
                conn.commit()
                
                return True
                
        except Exception as e:
            print(f"Test insert failed: {e}")
            return False

if __name__ == "__main__":
    print("Fixing transaction table sequence...")
    
    if fix_transaction_sequence():
        print("Sequence fix completed successfully")
        
        if test_transaction_insert():
            print("Transaction insert test passed")
        else:
            print("Transaction insert test failed")
    else:
        print("Sequence fix failed")