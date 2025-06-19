#!/usr/bin/env python
"""
Test Cumulative Initial Deposit Behavior
Verifies that initial deposit increases with each new deposit
"""
import logging
from app import app, db
from models import User, Transaction
from utils.solana import process_auto_deposit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cumulative_initial_deposit():
    """Test that initial deposit grows with each deposit"""
    
    with app.app_context():
        try:
            # Clean up any existing test data
            test_user = User.query.filter_by(username='test_cumulative_user').first()
            if test_user:
                Transaction.query.filter_by(user_id=test_user.id).delete()
                db.session.delete(test_user)
                db.session.commit()
            
            # Create a fresh test user
            test_user = User(
                telegram_id='888888888',
                username='test_cumulative_user',
                first_name='Test',
                balance=0.0,
                initial_deposit=0.0
            )
            db.session.add(test_user)
            db.session.commit()
            
            print(f"Created test user: {test_user.username}")
            print(f"Starting state - Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            
            # Test 1: First deposit
            print("\n=== First Deposit: 1.0 SOL ===")
            process_auto_deposit(test_user.id, 1.0, "tx_001")
            db.session.refresh(test_user)
            print(f"Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            assert test_user.balance == 1.0
            assert test_user.initial_deposit == 1.0
            
            # Test 2: Second deposit - initial should increase
            print("\n=== Second Deposit: 2.5 SOL ===")
            process_auto_deposit(test_user.id, 2.5, "tx_002")
            db.session.refresh(test_user)
            print(f"Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            assert test_user.balance == 3.5  # 1.0 + 2.5
            assert test_user.initial_deposit == 3.5  # 1.0 + 2.5
            
            # Test 3: Third deposit - initial should continue growing
            print("\n=== Third Deposit: 1.2 SOL ===")
            process_auto_deposit(test_user.id, 1.2, "tx_003")
            db.session.refresh(test_user)
            print(f"Balance: {test_user.balance}, Initial Deposit: {test_user.initial_deposit}")
            assert test_user.balance == 4.7  # 3.5 + 1.2
            assert test_user.initial_deposit == 4.7  # 3.5 + 1.2
            
            print("\n" + "="*50)
            print("✅ CUMULATIVE INITIAL DEPOSIT WORKING CORRECTLY")
            print("✅ Initial deposit grows with each new deposit")
            print("✅ Balance and initial deposit stay synchronized")
            print("="*50)
            
            return True
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    test_cumulative_initial_deposit()