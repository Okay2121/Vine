#!/usr/bin/env python
"""
Test Future Cumulative Deposits
===============================
Test that new deposits will correctly accumulate the initial_deposit value
"""

import logging
from app import app, db
from models import User, Transaction
from utils.solana import process_auto_deposit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_new_user_cumulative_deposits():
    """Test cumulative deposits for a new user"""
    
    with app.app_context():
        try:
            # Clean up any existing test user
            test_user = User.query.filter_by(username='cumulative_test_user').first()
            if test_user:
                Transaction.query.filter_by(user_id=test_user.id).delete()
                db.session.delete(test_user)
                db.session.commit()
            
            # Create a new test user
            from models import UserStatus
            test_user = User(
                telegram_id='555555555',
                username='cumulative_test_user',
                first_name='CumulativeTest',
                balance=0.0,
                initial_deposit=0.0,
                status=UserStatus.ACTIVE
            )
            
            db.session.add(test_user)
            db.session.commit()
            
            print(f"Created test user: {test_user.username} (ID: {test_user.id})")
            print(f"Starting state: Balance={test_user.balance:.4f}, Initial={test_user.initial_deposit:.4f}")
            
            # Test deposit sequence
            deposits = [1.0, 2.5, 0.8, 1.7]
            expected_cumulative = 0.0
            
            for i, amount in enumerate(deposits, 1):
                print(f"\n--- DEPOSIT {i}: {amount} SOL ---")
                
                # Process the deposit
                success = process_auto_deposit(test_user.id, amount, f"test_tx_{i}")
                
                if success:
                    # Refresh user data
                    db.session.refresh(test_user)
                    expected_cumulative += amount
                    
                    print(f"Deposit processed successfully")
                    print(f"Balance: {test_user.balance:.4f} SOL")
                    print(f"Initial Deposit: {test_user.initial_deposit:.4f} SOL")
                    print(f"Expected Cumulative: {expected_cumulative:.4f} SOL")
                    
                    # Verify cumulative behavior
                    if abs(test_user.initial_deposit - expected_cumulative) < 0.001:
                        print("✅ Cumulative behavior working correctly")
                    else:
                        print(f"❌ Initial deposit mismatch! Expected {expected_cumulative:.4f}, got {test_user.initial_deposit:.4f}")
                        return False
                else:
                    print(f"❌ Failed to process deposit {i}")
                    return False
            
            print(f"\n{'='*50}")
            print("✅ ALL CUMULATIVE DEPOSITS WORKING CORRECTLY")
            print(f"Final Balance: {test_user.balance:.4f} SOL")
            print(f"Final Initial Deposit: {test_user.initial_deposit:.4f} SOL")
            print(f"Total Deposited: {sum(deposits):.4f} SOL")
            print("✅ Future deposits will correctly accumulate initial_deposit")
            print(f"{'='*50}")
            
            return True
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("TESTING FUTURE CUMULATIVE DEPOSIT BEHAVIOR")
    print("=" * 50)
    
    success = test_new_user_cumulative_deposits()
    
    if success:
        print("\n🎯 CUMULATIVE INITIAL DEPOSIT SYSTEM IS WORKING")
        print("All new user deposits will correctly accumulate initial_deposit values")
    else:
        print("\n❌ CUMULATIVE SYSTEM NEEDS FIXING")