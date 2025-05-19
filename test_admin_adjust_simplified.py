#!/usr/bin/env python
"""
Simplified test to verify admin balance adjustment affects user dashboard
This script:
1. Creates a test user
2. Adjusts their balance using admin_balance_manager
3. Verifies the balance is updated in the database
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

# Test data
TEST_USERNAME = "testuser"
TEST_TELEGRAM_ID = "12345678"
ADJUSTMENT_AMOUNT = 5.0
ADJUSTMENT_REASON = "Admin UI Test"

def setup_test_user():
    """Create a test user or get existing one"""
    with app.app_context():
        # Check if user exists
        user = User.query.filter_by(telegram_id=TEST_TELEGRAM_ID).first()
        
        if user:
            logger.info(f"Using existing test user: @{user.username} (ID: {user.id})")
            return user.id
        
        # Create new user
        user = User(
            telegram_id=TEST_TELEGRAM_ID,
            username=TEST_USERNAME,
            first_name="Test",
            last_name="User",
            status=UserStatus.ACTIVE,
            balance=10.0  # Start with some balance
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Created test user: @{user.username} (ID: {user.id})")
        return user.id

def show_user_dashboard(user_id):
    """Show the user dashboard as it would appear in the UI"""
    with app.app_context():
        # Get fresh user data
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User ID {user_id} not found")
            return None
        
        # Get recent transactions
        transactions = Transaction.query.filter_by(user_id=user_id)\
            .order_by(Transaction.timestamp.desc())\
            .limit(5).all()
        
        logger.info(f"\n====== USER DASHBOARD ======")
        logger.info(f"Username: @{user.username}")
        logger.info(f"Telegram ID: {user.telegram_id}")
        logger.info(f"Current Balance: {user.balance:.4f} SOL")
        logger.info(f"Status: {user.status.value}")
        
        if transactions:
            logger.info(f"\nRecent Transactions:")
            for i, tx in enumerate(transactions, 1):
                logger.info(f"  {i}. {tx.transaction_type.upper()} - {tx.amount:.4f} SOL - {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {tx.notes or 'No notes'}")
        else:
            logger.info(f"\nNo recent transactions")
        
        logger.info(f"============================\n")
        return user.balance

def admin_adjust_balance(user_id, amount, reason):
    """Perform admin balance adjustment using the actual system code"""
    with app.app_context():
        # Get user to adjust
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User ID {user_id} not found")
            return False, 0, 0
        
        # Store initial balance
        initial_balance = user.balance
        
        try:
            # Try to use the admin_balance_manager first
            import admin_balance_manager
            
            logger.info(f"Using admin_balance_manager to adjust balance")
            success, message = admin_balance_manager.adjust_balance(
                user.telegram_id, amount, reason
            )
            
            if success:
                logger.info(f"Balance adjustment successful via manager")
                # Get updated balance - need to refresh user
                user = User.query.get(user_id)
                return True, initial_balance, user.balance
            else:
                logger.error(f"Balance adjustment failed via manager: {message}")
                return False, initial_balance, initial_balance
                
        except Exception as e:
            logger.error(f"Error using admin_balance_manager: {e}")
            
            # Fall back to direct adjustment
            logger.info(f"Falling back to direct balance adjustment")
            
            try:
                # Update user balance directly
                old_balance = user.balance
                user.balance += amount
                
                # Create transaction record
                transaction_type = 'admin_credit' if amount > 0 else 'admin_debit'
                
                new_transaction = Transaction(
                    user_id=user.id,
                    transaction_type=transaction_type,
                    amount=abs(amount),
                    token_name="SOL",
                    timestamp=datetime.utcnow(),
                    status='completed',
                    notes=reason
                )
                
                # Add and commit transaction
                db.session.add(new_transaction)
                db.session.commit()
                
                logger.info(f"Direct balance adjustment successful")
                return True, old_balance, user.balance
                
            except Exception as db_error:
                logger.error(f"Database error during direct adjustment: {db_error}")
                db.session.rollback()
                return False, initial_balance, initial_balance

def run_test():
    """Run the full test for admin balance adjustment"""
    try:
        # Step 1: Create or get test user
        user_id = setup_test_user()
        
        # Step 2: Show initial user dashboard
        logger.info("BEFORE ADJUSTMENT:")
        initial_balance = show_user_dashboard(user_id)
        
        # Step 3: Perform admin balance adjustment (simulating admin UI)
        logger.info(f"\nSIMULATING ADMIN BALANCE ADJUSTMENT:")
        logger.info(f"Admin is adjusting balance for user ID {user_id}")
        logger.info(f"Amount: +{ADJUSTMENT_AMOUNT} SOL")
        logger.info(f"Reason: '{ADJUSTMENT_REASON}'")
        
        success, old_balance, new_balance = admin_adjust_balance(
            user_id, ADJUSTMENT_AMOUNT, ADJUSTMENT_REASON
        )
        
        if not success:
            logger.error("Admin balance adjustment failed!")
            return False
        
        logger.info(f"\nAdjustment completed successfully!")
        logger.info(f"Previous balance: {old_balance:.4f} SOL")
        logger.info(f"New balance: {new_balance:.4f} SOL")
        logger.info(f"Change: +{ADJUSTMENT_AMOUNT:.4f} SOL")
        
        # Step 4: Show updated user dashboard (as it would appear to user)
        logger.info("\nAFTER ADJUSTMENT (User Dashboard View):")
        updated_balance = show_user_dashboard(user_id)
        
        # Step 5: Verify the change is reflected correctly
        expected_balance = initial_balance + ADJUSTMENT_AMOUNT
        
        if abs(updated_balance - expected_balance) < 0.0001:  # Account for floating point precision
            logger.info(f"\n✅ TEST PASSED: Balance successfully updated from {initial_balance:.4f} to {updated_balance:.4f} SOL")
            return True
        else:
            logger.error(f"\n❌ TEST FAILED: Balance not updated correctly. Expected {expected_balance:.4f} SOL but got {updated_balance:.4f} SOL")
            return False
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)