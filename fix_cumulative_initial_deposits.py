#!/usr/bin/env python
"""
Fix Cumulative Initial Deposits for Existing Users
==================================================
This script corrects the initial_deposit values for all users to reflect
the cumulative behavior where initial_deposit = sum of all deposits.
"""

import logging
from app import app, db
from models import User, Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_user_initial_deposits():
    """Fix initial_deposit values for all users with deposits"""
    
    with app.app_context():
        try:
            # Get all users who have made deposits
            users_with_deposits = db.session.query(User).join(Transaction).filter(
                Transaction.transaction_type == 'deposit'
            ).distinct().all()
            
            print(f"Found {len(users_with_deposits)} users with deposits")
            print("=" * 60)
            
            fixed_count = 0
            
            for user in users_with_deposits:
                # Calculate total deposits for this user
                total_deposits = db.session.query(db.func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == 'deposit',
                    Transaction.status == 'completed'
                ).scalar() or 0.0
                
                # Check if initial_deposit needs correction
                if abs(user.initial_deposit - total_deposits) > 0.001:
                    old_initial = user.initial_deposit
                    user.initial_deposit = total_deposits
                    
                    print(f"User: {user.username} (TG: {user.telegram_id})")
                    print(f"  Old initial_deposit: {old_initial:.4f} SOL")
                    print(f"  New initial_deposit: {total_deposits:.4f} SOL")
                    print(f"  Current balance: {user.balance:.4f} SOL")
                    
                    fixed_count += 1
                else:
                    print(f"✓ User {user.username}: initial_deposit already correct ({user.initial_deposit:.4f} SOL)")
            
            # Commit all changes
            if fixed_count > 0:
                db.session.commit()
                print(f"\n✅ Fixed initial_deposit for {fixed_count} users")
            else:
                print("\n✅ All users already have correct initial_deposit values")
                
            return fixed_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error fixing initial deposits: {e}")
            import traceback
            traceback.print_exc()
            return 0


def verify_cumulative_behavior():
    """Verify that the cumulative behavior is working correctly"""
    
    with app.app_context():
        try:
            print("\nVERIFYING CUMULATIVE BEHAVIOR:")
            print("=" * 40)
            
            # Check users with multiple deposits
            users_with_multiple_deposits = db.session.query(User).join(Transaction).filter(
                Transaction.transaction_type == 'deposit'
            ).group_by(User.id).having(db.func.count(Transaction.id) > 1).all()
            
            for user in users_with_multiple_deposits:
                deposits = Transaction.query.filter_by(
                    user_id=user.id,
                    transaction_type='deposit'
                ).order_by(Transaction.timestamp.asc()).all()
                
                total_deposits = sum(d.amount for d in deposits)
                
                print(f"User: {user.username}")
                print(f"  Number of deposits: {len(deposits)}")
                print(f"  Total deposited: {total_deposits:.4f} SOL")
                print(f"  Initial deposit: {user.initial_deposit:.4f} SOL")
                print(f"  Current balance: {user.balance:.4f} SOL")
                
                if abs(user.initial_deposit - total_deposits) < 0.001:
                    print("  ✅ Cumulative behavior working correctly")
                else:
                    print("  ❌ Initial deposit doesn't match total deposits")
                print()
                
        except Exception as e:
            logger.error(f"Error verifying cumulative behavior: {e}")


if __name__ == "__main__":
    print("FIXING CUMULATIVE INITIAL DEPOSITS")
    print("=" * 50)
    
    # Fix existing users
    fixed_count = fix_user_initial_deposits()
    
    # Verify the fix worked
    if fixed_count > 0:
        verify_cumulative_behavior()
    
    print("\nDONE!")