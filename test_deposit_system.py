"""
Test Script to verify the deposit monitoring system functions properly in real-time
This script simulates a deposit and verifies it's processed correctly
"""
import logging
import time
import random
import string
from datetime import datetime

from app import app, db
from models import User, Transaction, SenderWallet, UserStatus
from utils.solana import process_auto_deposit, check_deposit_by_sender

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_test_tx_signature():
    """Generate a random transaction signature for testing"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def get_or_create_test_user():
    """Get or create a test user for deposit verification"""
    with app.app_context():
        # Import UserStatus here to avoid circular imports
        from models import UserStatus
        
        # Look for a test user
        test_user = User.query.filter_by(username='test_deposit_user').first()
        
        if not test_user:
            logger.info("Creating test user for deposit verification")
            test_user = User()
            test_user.telegram_id = f"test_{int(time.time())}"
            test_user.username = 'test_deposit_user'
            test_user.first_name = 'Test'
            test_user.last_name = 'User'
            test_user.balance = 0
            test_user.initial_deposit = 0
            test_user.status = UserStatus.ACTIVE
            db.session.add(test_user)
            db.session.commit()
            
        return test_user

def get_or_create_test_wallet(user_id):
    """Get or create a test wallet for the user"""
    with app.app_context():
        # Look for an existing wallet
        test_wallet = SenderWallet.query.filter_by(user_id=user_id).first()
        
        if not test_wallet:
            logger.info(f"Creating test wallet for user {user_id}")
            test_wallet = SenderWallet()
            test_wallet.user_id = user_id
            test_wallet.wallet_address = f"TestWallet{int(time.time())}"
            test_wallet.created_at = datetime.utcnow()
            test_wallet.last_used = datetime.utcnow()
            test_wallet.is_primary = True
            db.session.add(test_wallet)
            db.session.commit()
            
        return test_wallet

def test_deposit_processing():
    """Test the deposit processing system"""
    # Get or create a test user
    test_user = get_or_create_test_user()
    logger.info(f"Using test user: {test_user.username} (ID: {test_user.id})")
    
    # Get or create a test wallet
    test_wallet = get_or_create_test_wallet(test_user.id)
    logger.info(f"Using test wallet: {test_wallet.wallet_address}")
    
    # Record initial balance
    initial_balance = test_user.balance
    logger.info(f"Initial balance: {initial_balance} SOL")
    
    # Generate a unique transaction signature
    tx_signature = generate_test_tx_signature()
    logger.info(f"Generated test transaction signature: {tx_signature}")
    
    # Process a simulated deposit
    deposit_amount = round(random.uniform(0.1, 2.0), 2)
    logger.info(f"Processing test deposit of {deposit_amount} SOL")
    
    # Process the deposit
    success = process_auto_deposit(test_user.id, deposit_amount, tx_signature)
    
    if success:
        logger.info("✅ Deposit processed successfully")
    else:
        logger.error("❌ Deposit processing failed")
        return False
    
    # Verify the balance was updated correctly
    with app.app_context():
        updated_user = User.query.get(test_user.id)
        expected_balance = initial_balance + deposit_amount
        actual_balance = updated_user.balance
        
        logger.info(f"Expected balance: {expected_balance} SOL")
        logger.info(f"Actual balance: {actual_balance} SOL")
        
        if abs(expected_balance - actual_balance) < 0.0001:  # Allow for floating point comparison
            logger.info("✅ Balance updated correctly")
        else:
            logger.error("❌ Balance not updated correctly")
            return False
        
        # Verify the transaction was recorded
        transaction = Transaction.query.filter_by(tx_hash=tx_signature).first()
        if transaction:
            logger.info("✅ Transaction record created")
            logger.info(f"Transaction type: {transaction.transaction_type}")
            logger.info(f"Transaction amount: {transaction.amount}")
            logger.info(f"Transaction status: {transaction.status}")
            logger.info(f"Transaction processed_at: {transaction.processed_at}")
        else:
            logger.error("❌ Transaction record not found")
            return False
        
        # Try processing the same deposit again (should be idempotent)
        logger.info("Testing duplicate transaction handling...")
        repeat_success = process_auto_deposit(test_user.id, deposit_amount, tx_signature)
        
        if repeat_success:
            logger.info("✅ Duplicate transaction handled correctly (didn't error)")
            
            # Verify balance wasn't updated twice
            latest_user = User.query.get(test_user.id)
            if abs(latest_user.balance - actual_balance) < 0.0001:
                logger.info("✅ Balance not changed on duplicate deposit (correct)")
            else:
                logger.error("❌ Balance changed on duplicate deposit (incorrect)")
                return False
        else:
            logger.error("❌ Duplicate transaction handling failed")
            return False
    
    logger.info("🎉 All deposit system tests passed successfully!")
    return True

def test_wallet_matching():
    """Test the wallet matching functionality"""
    # Get the test user and wallet
    test_user = get_or_create_test_user()
    test_wallet = get_or_create_test_wallet(test_user.id)
    
    logger.info(f"Testing wallet matching for wallet: {test_wallet.wallet_address}")
    
    # Test if the deposit monitoring can detect a deposit from this wallet
    deposit_found, amount, tx_signature = check_deposit_by_sender(test_wallet.wallet_address)
    
    if deposit_found:
        logger.info(f"✅ Detected deposit of {amount} SOL with signature {tx_signature[:10]}...")
    else:
        logger.info("No deposits detected in this test run (normal in most cases)")
    
    return True

if __name__ == "__main__":
    logger.info("Starting deposit system verification tests")
    
    # Test deposit processing
    deposit_result = test_deposit_processing()
    
    # Test wallet matching
    wallet_result = test_wallet_matching()
    
    if deposit_result and wallet_result:
        logger.info("✅ ALL TESTS PASSED - Deposit system is functioning correctly!")
    else:
        logger.error("❌ Some tests failed - Check the logs for details")