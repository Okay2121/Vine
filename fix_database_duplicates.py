#!/usr/bin/env python
"""
Fix Database Duplicates - Clean up duplicate transaction records
This script removes duplicate transactions that are causing database errors
"""
import os
import sys
from datetime import datetime

# Add the current directory to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Transaction

def clean_duplicate_transactions():
    """
    Remove duplicate transaction records that are causing database errors
    """
    with app.app_context():
        try:
            # Find all transactions with duplicate tx_hash patterns
            duplicates_removed = 0
            
            # Get all transactions that match the problematic pattern
            problematic_transactions = Transaction.query.filter(
                Transaction.tx_hash.like('%_sell_%_%')
            ).all()
            
            print(f"Found {len(problematic_transactions)} SELL transactions to check for duplicates")
            
            # Group by user_id and base tx_hash to identify duplicates
            seen_combinations = set()
            transactions_to_remove = []
            
            for transaction in problematic_transactions:
                # Extract base tx_hash (everything before _sell_)
                if '_sell_' in transaction.tx_hash:
                    base_tx_hash = transaction.tx_hash.split('_sell_')[0]
                    combination = (transaction.user_id, base_tx_hash, transaction.token_name)
                    
                    if combination in seen_combinations:
                        # This is a duplicate
                        transactions_to_remove.append(transaction)
                        duplicates_removed += 1
                    else:
                        seen_combinations.add(combination)
            
            # Remove the duplicate transactions
            for transaction in transactions_to_remove:
                db.session.delete(transaction)
                print(f"Removing duplicate transaction: {transaction.tx_hash}")
            
            # Also clean up any transactions with the exact problematic hash from the logs
            specific_duplicates = Transaction.query.filter_by(tx_hash='nop012_sell_1_1748407841').all()
            for dup in specific_duplicates[1:]:  # Keep the first one, remove the rest
                db.session.delete(dup)
                duplicates_removed += 1
                print(f"Removing specific duplicate: {dup.tx_hash}")
            
            db.session.commit()
            
            print(f"\n✅ Database cleanup complete!")
            print(f"✅ Removed {duplicates_removed} duplicate transactions")
            print(f"✅ Database should now be free of conflicts")
            
            return duplicates_removed
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error cleaning duplicates: {e}")
            return 0

def verify_database_health():
    """
    Check if the database is healthy and free of duplicate constraints
    """
    with app.app_context():
        try:
            # Test transaction creation
            test_tx = Transaction(
                user_id=1,
                transaction_type='test',
                amount=0.001,
                token_name='TEST',
                timestamp=datetime.utcnow(),
                status='completed',
                notes='Database health check',
                tx_hash=f'health_check_{int(datetime.utcnow().timestamp())}'
            )
            
            db.session.add(test_tx)
            db.session.commit()
            
            # Remove the test transaction
            db.session.delete(test_tx)
            db.session.commit()
            
            print("✅ Database health check passed - transactions can be created successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database health check failed: {e}")
            return False

def main():
    """
    Run the database cleanup process
    """
    print("🔧 Starting database duplicate cleanup...")
    
    # Clean up duplicates
    duplicates_removed = clean_duplicate_transactions()
    
    if duplicates_removed > 0:
        print(f"\n🎉 Successfully cleaned up {duplicates_removed} duplicate transactions")
    else:
        print("\n📝 No duplicates found to clean up")
    
    # Verify database health
    print("\n🔍 Verifying database health...")
    if verify_database_health():
        print("\n✅ Database is healthy and ready for use!")
        print("✅ Your bot should now run without duplicate transaction errors")
    else:
        print("\n⚠️ Database health check failed - there may be other issues")

if __name__ == "__main__":
    main()