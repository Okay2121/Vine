#!/usr/bin/env python
"""
Test Initial Deposit Fix
Verifies that initial deposit stays fixed after the first deposit
and doesn't increase with subsequent deposits
"""
import logging
from datetime import datetime
from app import app, db
from models import User, Transaction
from utils.solana import process_auto_deposit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_initial_deposit_behavior():
    """Test that initial deposit only gets set once and doesn't change with subsequent deposits"""
    
    with app.app_context():
        try:
            # Clean up any existing test data
            test_user = User.query.filter_by(username='test_deposit_user').first()
            if test_user:
                Transaction.query.filter_by(user_id=test_user.id).delete()
                db.session.delete(test_user)
                db.session.commit()
            
            # Create a fresh test user
            test_user = User(
                telegram_id='999999999',
                username='test_deposit_user',
                first_name='Test',
                balance=0.0,
                initial_deposit=0.0
            )
            db.session.add(test_user)
            db.session.commit()
            
            print(f"Created test user: {test_user.username} (ID: {test_user.id})")
            print(f"Initial state - Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            
            # Test 1: First deposit should set initial_deposit
            print("\n=== TEST 1: First Deposit ===")
            success1 = process_auto_deposit(test_user.id, 1.5, "tx_hash_001")
            
            # Refresh user data
            db.session.refresh(test_user)
            print(f"After first deposit - Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            
            expected_balance_1 = 1.5
            expected_initial_1 = 1.5
            
            assert test_user.balance == expected_balance_1, f"Expected balance {expected_balance_1}, got {test_user.balance}"
            assert test_user.initial_deposit == expected_initial_1, f"Expected initial deposit {expected_initial_1}, got {test_user.initial_deposit}"
            print("✅ First deposit correctly set initial_deposit")
            
            # Test 2: Second deposit should NOT change initial_deposit
            print("\n=== TEST 2: Second Deposit ===")
            success2 = process_auto_deposit(test_user.id, 2.0, "tx_hash_002")
            
            # Refresh user data
            db.session.refresh(test_user)
            print(f"After second deposit - Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            
            expected_balance_2 = 3.5  # 1.5 + 2.0
            expected_initial_2 = 1.5  # Should remain the same!
            
            assert test_user.balance == expected_balance_2, f"Expected balance {expected_balance_2}, got {test_user.balance}"
            assert test_user.initial_deposit == expected_initial_2, f"Expected initial deposit {expected_initial_2}, got {test_user.initial_deposit}"
            print("✅ Second deposit correctly preserved initial_deposit")
            
            # Test 3: Third deposit should also NOT change initial_deposit
            print("\n=== TEST 3: Third Deposit ===")
            success3 = process_auto_deposit(test_user.id, 0.8, "tx_hash_003")
            
            # Refresh user data
            db.session.refresh(test_user)
            print(f"After third deposit - Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            
            expected_balance_3 = 4.3  # 3.5 + 0.8
            expected_initial_3 = 1.5  # Should still remain the same!
            
            assert test_user.balance == expected_balance_3, f"Expected balance {expected_balance_3}, got {test_user.balance}"
            assert test_user.initial_deposit == expected_initial_3, f"Expected initial deposit {expected_initial_3}, got {test_user.initial_deposit}"
            print("✅ Third deposit correctly preserved initial_deposit")
            
            # Verify transaction count
            deposit_count = Transaction.query.filter_by(
                user_id=test_user.id,
                transaction_type='deposit',
                status='completed'
            ).count()
            print(f"\nTotal deposit transactions: {deposit_count}")
            assert deposit_count == 3, f"Expected 3 deposit transactions, found {deposit_count}"
            
            print("\n" + "="*60)
            print("🎉 ALL TESTS PASSED!")
            print("✅ Initial deposit is now fixed after first deposit")
            print("✅ Subsequent deposits no longer increase initial deposit")
            print("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run the test"""
    logger.info("Testing Initial Deposit Fix")
    success = test_initial_deposit_behavior()
    
    if success:
        print("\n✅ INITIAL DEPOSIT FIX VERIFIED")
        print("The system now correctly:")
        print("• Sets initial deposit only on the first deposit")
        print("• Preserves initial deposit value for all subsequent deposits")
        print("• Prevents initial deposit from increasing with more deposits")
    else:
        print("\n❌ TEST FAILED - Issues detected")
    
    return success

if __name__ == "__main__":
    main()