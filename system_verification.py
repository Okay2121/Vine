"""
Comprehensive Real-Time System Verification
Tests all key features to ensure they function correctly and sync in real-time
"""
import logging
import time
import random
import string
from datetime import datetime, timedelta
import sys

from app import app, db
from models import User, Transaction, UserStatus
from utils.solana import process_auto_deposit
from balance_manager import adjust_balance

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("SYSTEM VERIFICATION")

class VerificationResults:
    """Store verification results for each feature"""
    def __init__(self):
        self.results = []
        self.start_time = datetime.utcnow()
        
    def add_result(self, feature_name, status, user_ids=None, response_time=None, details=None):
        """Add a test result"""
        if user_ids is None:
            user_ids = []
        
        self.results.append({
            "feature": feature_name,
            "status": "PASS" if status else "FAIL",
            "user_ids": user_ids,
            "timestamp": datetime.utcnow(),
            "response_time": response_time,
            "details": details
        })
        
    def print_report(self):
        """Print a formatted report of all test results"""
        print("\n" + "="*80)
        print(" "*30 + "SYSTEM VERIFICATION REPORT")
        print("="*80)
        print(f"Test Run: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Features Tested: {len(self.results)}")
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = len(self.results) - passed
        
        print(f"Passed: {passed}, Failed: {failed}")
        print("-"*80)
        
        for i, result in enumerate(self.results, 1):
            print(f"{i}. {result['feature']}")
            print(f"   Status: {result['status']}")
            print(f"   Timestamp: {result['timestamp'].strftime('%H:%M:%S')}")
            
            if result["user_ids"]:
                print(f"   Affected User IDs: {', '.join(str(uid) for uid in result['user_ids'])}")
                
            if result["response_time"]:
                print(f"   Response Time: {result['response_time']:.3f} seconds")
                
            if result["details"]:
                print(f"   Details: {result['details']}")
                
            print()
            
        print("="*80)
        
        if failed > 0:
            print("❌ VERIFICATION FAILED - Some features are not working correctly.")
        else:
            print("✅ VERIFICATION PASSED - All features are working correctly!")
        
        print("="*80 + "\n")

def time_execution(func, *args, **kwargs):
    """Measure execution time of a function"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time

def generate_tx_signature():
    """Generate a random transaction signature"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def test_deposit_recognition(results):
    """Test deposit recognition and real-time balance updates"""
    logger.info("Testing Deposit Recognition System...")
    
    with app.app_context():
        # Find an existing user
        user = User.query.first()
        if not user:
            results.add_result(
                "Deposit Recognition", 
                False, 
                details="No users found in database"
            )
            return
            
        # Record initial state
        initial_balance = user.balance
        logger.info(f"User: {user.username}, Initial Balance: {initial_balance} SOL")
        
        # Create a unique transaction
        tx_signature = generate_tx_signature()
        deposit_amount = 0.5
        
        # Process deposit with timing
        deposit_func = lambda: process_auto_deposit(user.id, deposit_amount, tx_signature)
        deposit_result, deposit_time = time_execution(deposit_func)
        
        if not deposit_result:
            results.add_result(
                "Deposit Recognition", 
                False, 
                [user.id], 
                deposit_time,
                "Failed to process deposit"
            )
            return
            
        # Check balance was updated correctly
        updated_user = User.query.get(user.id)
        expected_balance = initial_balance + deposit_amount
        actual_balance = updated_user.balance
        
        balance_correct = abs(expected_balance - actual_balance) < 0.0001
        
        # Check for duplicate prevention
        duplicate_func = lambda: process_auto_deposit(user.id, deposit_amount, tx_signature)
        dup_result, dup_time = time_execution(duplicate_func)
        
        # Verify duplicate handling
        updated_user_after_dup = User.query.get(user.id)
        no_double_credit = abs(updated_user_after_dup.balance - actual_balance) < 0.0001
        
        # Check transaction record
        transaction = Transaction.query.filter_by(tx_hash=tx_signature).first()
        tx_record_exists = transaction is not None
        processed_at_works = hasattr(transaction, 'processed_at') and transaction.processed_at is not None
        
        # Restore original balance
        with db.session.begin():
            final_user = User.query.get(user.id)
            final_user.balance = initial_balance
            db.session.commit()
        
        # Compile results
        passed = balance_correct and no_double_credit and tx_record_exists and processed_at_works
        details = (
            f"Balance update: {'✓' if balance_correct else '✗'}, "
            f"Duplicate prevention: {'✓' if no_double_credit else '✗'}, "
            f"Transaction record: {'✓' if tx_record_exists else '✗'}, "
            f"Processed_at field: {'✓' if processed_at_works else '✗'}"
        )
        
        results.add_result(
            "Deposit Recognition", 
            passed, 
            [user.id], 
            deposit_time,
            details
        )
        
        logger.info(f"Deposit test completed. Success: {passed}")

def test_balance_manager(results):
    """Test balance_manager functionality for real-time updates"""
    logger.info("Testing Balance Manager System...")
    
    with app.app_context():
        # Find an existing user
        user = User.query.first()
        if not user:
            results.add_result(
                "Balance Manager", 
                False, 
                details="No users found in database"
            )
            return
            
        # Record initial state
        initial_balance = user.balance
        logger.info(f"User: {user.username}, Initial Balance: {initial_balance} SOL")
        
        # Test balance adjustment with timing
        test_amount = 0.25
        reason = "System verification test"
        adjustment_func = lambda: adjust_balance(str(user.id), test_amount, reason, skip_trading=True)
        success_result, success_time = time_execution(adjustment_func)
        
        if not success_result[0]:  # adjust_balance returns (success, message)
            results.add_result(
                "Balance Manager", 
                False, 
                [user.id], 
                success_time,
                f"Failed to adjust balance: {success_result[1]}"
            )
            return
            
        # Check balance was updated correctly
        updated_user = User.query.get(user.id)
        expected_balance = initial_balance + test_amount
        actual_balance = updated_user.balance
        
        balance_correct = abs(expected_balance - actual_balance) < 0.0001
        
        # Check transaction record
        latest_tx = Transaction.query.filter_by(
            user_id=user.id,
            notes=reason
        ).order_by(Transaction.timestamp.desc()).first()
        
        tx_record_exists = latest_tx is not None
        
        # Restore original balance
        with db.session.begin():
            final_user = User.query.get(user.id)
            final_user.balance = initial_balance
            db.session.commit()
        
        # Compile results
        passed = balance_correct and tx_record_exists
        details = (
            f"Balance update: {'✓' if balance_correct else '✗'}, "
            f"Transaction record: {'✓' if tx_record_exists else '✗'}"
        )
        
        results.add_result(
            "Balance Manager", 
            passed, 
            [user.id], 
            success_time,
            details
        )
        
        logger.info(f"Balance Manager test completed. Success: {passed}")

def test_transaction_indexing(results):
    """Test transaction indexing for improved performance"""
    logger.info("Testing Transaction Indexing Performance...")
    
    with app.app_context():
        # Find an existing user
        user = User.query.first()
        if not user:
            results.add_result(
                "Transaction Indexing", 
                False, 
                details="No users found in database"
            )
            return
            
        # Test query performance with new indexes
        # 1. Query by tx_hash (should be fast with new index)
        def query_by_hash():
            # Get a recent transaction hash
            recent_tx = Transaction.query.filter_by(user_id=user.id).first()
            if recent_tx and recent_tx.tx_hash:
                return Transaction.query.filter_by(tx_hash=recent_tx.tx_hash).first()
            return None
            
        hash_result, hash_time = time_execution(query_by_hash)
        
        # 2. Query with multiple conditions using indexes
        def query_complex():
            return Transaction.query.filter_by(
                user_id=user.id,
                transaction_type='deposit'
            ).order_by(Transaction.timestamp.desc()).limit(10).all()
            
        complex_result, complex_time = time_execution(query_complex)
        
        # Performance is acceptable if queries are fast enough
        hash_perf_ok = hash_time < 0.1  # less than 100ms
        complex_perf_ok = complex_time < 0.2  # less than 200ms
        
        # Compile results
        passed = hash_perf_ok and complex_perf_ok
        details = (
            f"Hash query time: {hash_time:.3f}s {'✓' if hash_perf_ok else '✗'}, "
            f"Complex query time: {complex_time:.3f}s {'✓' if complex_perf_ok else '✗'}"
        )
        
        results.add_result(
            "Transaction Indexing", 
            passed, 
            [user.id], 
            max(hash_time, complex_time),
            details
        )
        
        logger.info(f"Transaction Indexing test completed. Success: {passed}")

def test_database_stability(results):
    """Test database stability with concurrent operations"""
    logger.info("Testing Database Stability...")
    
    with app.app_context():
        # Find an existing user
        user = User.query.first()
        if not user:
            results.add_result(
                "Database Stability", 
                False, 
                details="No users found in database"
            )
            return
            
        # Record initial state
        initial_balance = user.balance
        logger.info(f"User: {user.username}, Initial Balance: {initial_balance} SOL")
        
        # Series of rapid balance adjustments to test stability
        operations_count = 5
        test_amount = 0.1
        success_count = 0
        total_time = 0
        
        for i in range(operations_count):
            # Generate unique deposit each time
            tx_signature = generate_tx_signature()
            
            # Process deposit with timing
            deposit_func = lambda: process_auto_deposit(user.id, test_amount, tx_signature)
            deposit_result, deposit_time = time_execution(deposit_func)
            
            total_time += deposit_time
            if deposit_result:
                success_count += 1
        
        # Check final balance against expected
        updated_user = User.query.get(user.id)
        expected_balance = initial_balance + (test_amount * success_count)
        actual_balance = updated_user.balance
        
        balance_correct = abs(expected_balance - actual_balance) < 0.0001
        
        # Restore original balance
        with db.session.begin():
            final_user = User.query.get(user.id)
            final_user.balance = initial_balance
            db.session.commit()
        
        # Compile results
        success_rate = success_count / operations_count
        passed = balance_correct and success_rate >= 0.8  # At least 80% success
        details = (
            f"Operations: {operations_count}, Success rate: {success_rate*100:.0f}%, "
            f"Balance accuracy: {'✓' if balance_correct else '✗'}, "
            f"Avg response time: {total_time/operations_count:.3f}s"
        )
        
        results.add_result(
            "Database Stability", 
            passed, 
            [user.id], 
            total_time/operations_count,
            details
        )
        
        logger.info(f"Database Stability test completed. Success: {passed}")

def run_verification():
    """Run all verification tests"""
    logger.info("Starting Comprehensive System Verification...")
    
    results = VerificationResults()
    
    # Run all tests
    test_deposit_recognition(results)
    test_balance_manager(results)
    test_transaction_indexing(results)
    test_database_stability(results)
    
    # Print report
    results.print_report()
    
    return all(r["status"] == "PASS" for r in results.results)

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)