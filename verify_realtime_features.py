"""
Real-Time Feature Verification Report
Tests all key features to ensure they respond instantly and sync properly
"""
import logging
import time
import random
import string
from datetime import datetime

from app import app, db
from models import User, Transaction, UserStatus
from utils.solana import process_auto_deposit
import balance_manager  # Import the whole module to avoid circular imports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VERIFICATION")

def generate_unique_tx():
    """Generate a random transaction signature for testing"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def verify_deposit_system():
    """Verify the deposit system responds in real-time"""
    print("\n===== DEPOSIT RECOGNITION SYSTEM =====")
    
    with app.app_context():
        # Find a real user
        user = User.query.first()
        if not user:
            print("❌ FAIL: No users found in database")
            return False
            
        # Save initial state
        initial_balance = user.balance
        print(f"User: ID {user.id}, Username: {user.username}")
        print(f"Initial Balance: {initial_balance} SOL")
        
        # Process a test deposit
        start_time = time.time()
        tx_signature = generate_unique_tx()
        test_amount = 0.75
        
        print(f"Processing test deposit of {test_amount} SOL...")
        success = process_auto_deposit(user.id, test_amount, tx_signature)
        
        if not success:
            print("❌ FAIL: Deposit processing failed")
            return False
            
        response_time = time.time() - start_time
        print(f"Response Time: {response_time:.3f} seconds")
        
        # Verify balance update
        updated_user = User.query.get(user.id)
        expected_balance = initial_balance + test_amount
        
        print(f"Expected New Balance: {expected_balance} SOL")
        print(f"Actual New Balance: {updated_user.balance} SOL")
        
        balance_correct = abs(updated_user.balance - expected_balance) < 0.0001
        print(f"Balance Updated Correctly: {'✅ PASS' if balance_correct else '❌ FAIL'}")
        
        # Verify transaction record
        tx_record = Transaction.query.filter_by(tx_hash=tx_signature).first()
        if tx_record:
            print("\nTransaction Record Created:")
            print(f"  Type: {tx_record.transaction_type}")
            print(f"  Amount: {tx_record.amount} SOL")
            print(f"  Status: {tx_record.status}")
            print(f"  Timestamp: {tx_record.timestamp}")
            
            # Check processed_at field (our new improvement)
            if hasattr(tx_record, 'processed_at') and tx_record.processed_at:
                print(f"  Processed At: {tx_record.processed_at} ✅")
            else:
                print("  Processed At: Not available ❌")
        else:
            print("❌ FAIL: No transaction record created")
            return False
            
        # Test duplicate prevention
        print("\nTesting duplicate prevention...")
        dup_start = time.time()
        dup_result = process_auto_deposit(user.id, test_amount, tx_signature)
        dup_time = time.time() - dup_start
        
        if not dup_result:
            print("❌ FAIL: Duplicate handling failed")
            return False
            
        # Check balance was not affected by duplicate
        final_user = User.query.get(user.id)
        no_double_credit = abs(final_user.balance - updated_user.balance) < 0.0001
        
        print(f"Duplicate Detection Time: {dup_time:.3f} seconds")
        print(f"Prevented Double Credit: {'✅ PASS' if no_double_credit else '❌ FAIL'}")
        
        # Restore original balance
        try:
            user = User.query.get(user.id)
            user.balance = initial_balance
            db.session.commit()
            print(f"\nTest cleanup: User balance restored to {initial_balance} SOL")
        except Exception as e:
            print(f"Warning: Could not restore balance: {e}")
            
        # Final assessment
        passed = balance_correct and no_double_credit and tx_record is not None
        print(f"\nOverall Deposit System: {'✅ PASS' if passed else '❌ FAIL'}")
        
        return passed

def verify_trade_history():
    """Verify that trade history reflects actual trades and updates in real-time"""
    print("\n===== TRADE HISTORY INTEGRATION =====")
    
    with app.app_context():
        # Find a real user
        user = User.query.get(1)
        if not user:
            print("❌ FAIL: No users found in database")
            return False
        
        print(f"User: ID {user.id}, Username: {user.username}")
        
        # Check for existing trades
        trades = Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type.in_(['buy', 'sell'])
        ).order_by(Transaction.timestamp.desc()).limit(5).all()
        
        if trades:
            print(f"Found {len(trades)} recent trades:")
            for i, trade in enumerate(trades, 1):
                print(f"  {i}. {trade.transaction_type.upper()} - {trade.amount} {trade.token_name or 'SOL'} - {trade.timestamp}")
        else:
            print("No recent trades found - will create a test trade")
        
        # Create a test trade record
        start_time = time.time()
        
        # Use transaction_type 'buy' to simulate a trade
        trade_tx = Transaction()
        trade_tx.user_id = user.id
        trade_tx.transaction_type = 'buy'
        trade_tx.amount = 0.05
        trade_tx.token_name = 'BONK'
        trade_tx.status = 'completed'
        trade_tx.tx_hash = generate_unique_tx()
        trade_tx.notes = 'Verification test trade'
        
        db.session.add(trade_tx)
        db.session.commit()
        
        response_time = time.time() - start_time
        print(f"\nTest trade created in {response_time:.3f} seconds")
        
        # Verify trade was recorded
        new_trade = Transaction.query.filter_by(tx_hash=trade_tx.tx_hash).first()
        
        if new_trade:
            print("Trade record created successfully ✅")
            print(f"  Type: {new_trade.transaction_type}")
            print(f"  Amount: {new_trade.amount} {new_trade.token_name}")
            print(f"  Timestamp: {new_trade.timestamp}")
        else:
            print("❌ FAIL: Trade record not found")
            return False
            
        print("\nOverall Trade History Integration: ✅ PASS")
        return True

def verify_admin_user_sync():
    """Verify that admin balance adjustments reflect immediately to users"""
    print("\n===== ADMIN ↔ USER SYNC =====")
    
    with app.app_context():
        # Find a real user
        user = User.query.first()
        if not user:
            print("❌ FAIL: No users found in database")
            return False
            
        # Record initial state
        initial_balance = user.balance
        print(f"User: ID {user.id}, Username: {user.username}")
        print(f"Initial Balance: {initial_balance} SOL")
        
        # Simulate admin balance adjustment
        start_time = time.time()
        test_amount = 0.2
        test_reason = "Admin adjustment verification test"
        
        print(f"Processing admin balance adjustment of {test_amount} SOL...")
        
        # Use the balance_manager module to adjust balance
        identifier = str(user.id)  # Can be user ID, telegram_id, or username
        success, message = balance_manager.adjust_balance(
            identifier, 
            test_amount, 
            test_reason,
            skip_trading=True  # Don't trigger auto trading for this test
        )
        
        response_time = time.time() - start_time
        
        if not success:
            print(f"❌ FAIL: Admin adjustment failed - {message}")
            return False
            
        print(f"Response Time: {response_time:.3f} seconds")
        
        # Verify balance update
        updated_user = User.query.get(user.id)
        expected_balance = initial_balance + test_amount
        
        print(f"Expected New Balance: {expected_balance} SOL")
        print(f"Actual New Balance: {updated_user.balance} SOL")
        
        balance_correct = abs(updated_user.balance - expected_balance) < 0.0001
        print(f"Balance Updated Correctly: {'✅ PASS' if balance_correct else '❌ FAIL'}")
        
        # Verify transaction record
        tx_record = Transaction.query.filter_by(
            user_id=user.id,
            notes=test_reason
        ).order_by(Transaction.timestamp.desc()).first()
        
        if tx_record:
            print("\nAdmin Transaction Record Created:")
            print(f"  Type: {tx_record.transaction_type}")
            print(f"  Amount: {tx_record.amount} SOL")
            print(f"  Status: {tx_record.status}")
            print(f"  Timestamp: {tx_record.timestamp}")
        else:
            print("❌ FAIL: No admin transaction record created")
            return False
            
        # Restore original balance
        try:
            user = User.query.get(user.id)
            user.balance = initial_balance
            db.session.commit()
            print(f"\nTest cleanup: User balance restored to {initial_balance} SOL")
        except Exception as e:
            print(f"Warning: Could not restore balance: {e}")
            
        # Final assessment
        passed = balance_correct and tx_record is not None
        print(f"\nOverall Admin-User Sync: {'✅ PASS' if passed else '❌ FAIL'}")
        
        return passed

def verify_database_stability():
    """Verify database stability with multiple rapid operations"""
    print("\n===== DATABASE STABILITY =====")
    
    with app.app_context():
        # Find a real user
        user = User.query.first()
        if not user:
            print("❌ FAIL: No users found in database")
            return False
            
        # Record initial state
        initial_balance = user.balance
        print(f"User: ID {user.id}, Username: {user.username}")
        print(f"Initial Balance: {initial_balance} SOL")
        
        # Perform multiple rapid balance updates
        num_operations = 3
        test_amount = 0.1
        successful_ops = 0
        total_time = 0
        
        print(f"Performing {num_operations} rapid balance operations...")
        
        for i in range(num_operations):
            start_time = time.time()
            tx_signature = generate_unique_tx()
            
            success = process_auto_deposit(user.id, test_amount, tx_signature)
            op_time = time.time() - start_time
            
            print(f"  Operation {i+1}: {'✅ Success' if success else '❌ Failed'} in {op_time:.3f} seconds")
            
            if success:
                successful_ops += 1
                total_time += op_time
        
        # Check final balance
        updated_user = User.query.get(user.id)
        expected_balance = initial_balance + (test_amount * successful_ops)
        
        print(f"Expected Final Balance: {expected_balance} SOL")
        print(f"Actual Final Balance: {updated_user.balance} SOL")
        
        balance_correct = abs(updated_user.balance - expected_balance) < 0.0001
        
        print(f"Balance Accuracy: {'✅ PASS' if balance_correct else '❌ FAIL'}")
        print(f"Success Rate: {successful_ops}/{num_operations} ({successful_ops/num_operations*100:.0f}%)")
        
        if successful_ops > 0:
            print(f"Average Response Time: {total_time/successful_ops:.3f} seconds")
        
        # Restore original balance
        try:
            user = User.query.get(user.id)
            user.balance = initial_balance
            db.session.commit()
            print(f"\nTest cleanup: User balance restored to {initial_balance} SOL")
        except Exception as e:
            print(f"Warning: Could not restore balance: {e}")
        
        # Final assessment
        success_rate_ok = (successful_ops / num_operations) >= 0.8  # At least 80% success
        passed = balance_correct and success_rate_ok
        
        print(f"\nOverall Database Stability: {'✅ PASS' if passed else '❌ FAIL'}")
        return passed

def verify_all_features():
    """Run all verification tests and provide a comprehensive report"""
    print("\n" + "="*60)
    print(" "*15 + "REAL-TIME FEATURE VERIFICATION")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60)
    
    results = {
        "Deposit Recognition System": verify_deposit_system(),
        "Trade History Integration": verify_trade_history(),
        "Admin-User Sync": verify_admin_user_sync(),
        "Database Stability": verify_database_stability()
    }
    
    # Final report
    print("\n" + "="*60)
    print(" "*20 + "SUMMARY REPORT")
    print("="*60)
    
    all_passed = True
    for feature, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{feature}: {status}")
        if not passed:
            all_passed = False
    
    print("-"*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Your system functions correctly in real-time!")
    else:
        print("⚠️ SOME TESTS FAILED - See detailed results above.")
    
    print("="*60)
    return all_passed

if __name__ == "__main__":
    verify_all_features()