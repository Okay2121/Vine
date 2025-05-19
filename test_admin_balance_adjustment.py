#!/usr/bin/env python
"""
Script to test the admin balance adjustment functionality
This script will:
1. Create a test user if not exists
2. Perform an admin balance adjustment
3. Verify the change is reflected in the database
"""
import logging
import sys
from datetime import datetime
from app import app, db
from models import User, Transaction, UserStatus

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Test Constants
TEST_USER_TELEGRAM_ID = "12345678"
TEST_USERNAME = "testuser"
ADMIN_ADJUSTMENT_AMOUNT = 5.0  # SOL
ADJUSTMENT_REASON = "Admin UI Test"
TRANSACTION_TYPE = "admin_credit"

def create_test_user_if_missing():
    """Create a test user if they don't exist"""
    with app.app_context():
        # Check if user exists
        user = User.query.filter_by(telegram_id=TEST_USER_TELEGRAM_ID).first()
        
        if user:
            logger.info(f"Test user already exists with ID {user.id}")
            return user
        
        # Create new user
        new_user = User(
            telegram_id=TEST_USER_TELEGRAM_ID,
            username=TEST_USERNAME,
            first_name=TEST_USERNAME,
            last_name="TestAccount",
            status=UserStatus.ACTIVE,
            balance=0.0
        )
        
        # Save user
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"Created new test user {TEST_USERNAME} with ID {new_user.id}")
        return new_user

def perform_admin_balance_adjustment(user):
    """Perform an admin balance adjustment on the user"""
    with app.app_context():
        try:
            # Get latest user data
            user = User.query.get(user.id)
            
            # Store old balance for reporting
            old_balance = user.balance
            
            # Update user balance
            user.balance += ADMIN_ADJUSTMENT_AMOUNT
            
            # Create transaction record
            new_transaction = Transaction()
            new_transaction.user_id = user.id
            new_transaction.transaction_type = TRANSACTION_TYPE
            new_transaction.amount = ADMIN_ADJUSTMENT_AMOUNT
            new_transaction.token_name = "SOL"
            new_transaction.timestamp = datetime.utcnow()
            new_transaction.status = 'completed'
            new_transaction.notes = ADJUSTMENT_REASON
            
            # Add and commit transaction
            db.session.add(new_transaction)
            db.session.commit()
            
            logger.info(f"Balance adjustment successful")
            logger.info(f"User: {user.username} (ID: {user.id})")
            logger.info(f"Old balance: {old_balance:.4f} SOL")
            logger.info(f"New balance: {user.balance:.4f} SOL")
            logger.info(f"Adjustment: +{ADMIN_ADJUSTMENT_AMOUNT:.4f} SOL")
            logger.info(f"Transaction ID: {new_transaction.id}")
            
            # Try to trigger auto trading based on the balance adjustment
            try:
                from utils.auto_trading_history import handle_admin_balance_adjustment
                handle_admin_balance_adjustment(user.id, ADMIN_ADJUSTMENT_AMOUNT)
                logger.info(f"Auto trading history started for user {user.id} after balance adjustment")
            except Exception as trading_error:
                logger.error(f"Failed to start auto trading history for user {user.id}: {trading_error}")
                # Don't fail the balance adjustment process if auto trading fails
            
            return True, user.balance, old_balance, new_transaction.id
            
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error during balance adjustment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, 0, 0, None

def verify_transaction_record(user_id, transaction_id):
    """Verify the transaction record exists and is correct"""
    with app.app_context():
        try:
            # Get the transaction
            transaction = Transaction.query.get(transaction_id)
            
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found")
                return False
                
            # Verify transaction details
            if transaction.user_id != user_id:
                logger.error(f"Transaction user_id mismatch: {transaction.user_id} != {user_id}")
                return False
                
            if transaction.transaction_type != TRANSACTION_TYPE:
                logger.error(f"Transaction type mismatch: {transaction.transaction_type} != {TRANSACTION_TYPE}")
                return False
                
            if transaction.amount != ADMIN_ADJUSTMENT_AMOUNT:
                logger.error(f"Transaction amount mismatch: {transaction.amount} != {ADMIN_ADJUSTMENT_AMOUNT}")
                return False
                
            if transaction.status != 'completed':
                logger.error(f"Transaction status mismatch: {transaction.status} != completed")
                return False
                
            if transaction.notes != ADJUSTMENT_REASON:
                logger.error(f"Transaction reason mismatch: {transaction.notes} != {ADJUSTMENT_REASON}")
                return False
                
            logger.info(f"Transaction record verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying transaction: {e}")
            return False

def simulate_user_dashboard_check(user):
    """Simulate checking the user dashboard to verify the balance"""
    with app.app_context():
        try:
            # Get latest user data
            user = User.query.get(user.id)
            
            # Get the user's transactions
            transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
            
            logger.info(f"\n===== USER DASHBOARD SIMULATION =====")
            logger.info(f"Username: @{user.username}")
            logger.info(f"Telegram ID: {user.telegram_id}")
            logger.info(f"Current Balance: {user.balance:.4f} SOL")
            logger.info(f"Status: {user.status.value}")
            
            logger.info(f"\nRecent Transactions:")
            for idx, tx in enumerate(transactions, 1):
                logger.info(f"{idx}. {tx.transaction_type.upper()}: {tx.amount:.4f} SOL - {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {tx.notes or 'No notes'}")
            
            logger.info(f"=================================\n")
            
            return True, user.balance
            
        except Exception as e:
            logger.error(f"Error checking user dashboard: {e}")
            return False, 0

def run_test():
    """Run the full test process"""
    try:
        # Step 1: Create/get test user
        user = create_test_user_if_missing()
        if not user:
            logger.error("Failed to create or find test user")
            return False
            
        # Step 2: Check initial dashboard
        initial_check, initial_balance = simulate_user_dashboard_check(user)
        if not initial_check:
            logger.error("Failed to check initial user dashboard")
            return False
            
        # Step 3: Perform admin balance adjustment
        success, new_balance, old_balance, transaction_id = perform_admin_balance_adjustment(user)
        if not success:
            logger.error("Failed to perform admin balance adjustment")
            return False
            
        # Step 4: Verify transaction record
        verified = verify_transaction_record(user.id, transaction_id)
        if not verified:
            logger.error("Failed to verify transaction record")
            return False
            
        # Step 5: Check updated dashboard
        final_check, final_balance = simulate_user_dashboard_check(user)
        if not final_check:
            logger.error("Failed to check updated user dashboard")
            return False
            
        # Step 6: Verify balance change
        if final_balance != initial_balance + ADMIN_ADJUSTMENT_AMOUNT:
            logger.error(f"Balance mismatch: {final_balance} != {initial_balance + ADMIN_ADJUSTMENT_AMOUNT}")
            return False
            
        logger.info(f"Test completed successfully!")
        logger.info(f"Balance adjustment of +{ADMIN_ADJUSTMENT_AMOUNT} SOL reflected correctly in user dashboard")
        logger.info(f"Old balance: {old_balance:.4f} SOL")
        logger.info(f"New balance: {new_balance:.4f} SOL")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Run the test
    success = run_test()
    sys.exit(0 if success else 1)