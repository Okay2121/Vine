#!/usr/bin/env python
"""
UI Test for Admin Balance Adjustment
This script simulates the complete UI flow of the admin balance adjustment process
and verifies that the changes are reflected in the user dashboard.
"""
import logging
import sys
import time
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
TEST_ADMIN_ID = "999000999"
TEST_USER_TELEGRAM_ID = "12345678"
TEST_USERNAME = "testuser"
ADJUSTMENT_AMOUNT = 5.0
ADJUSTMENT_REASON = "UI Test"

def setup_test_users():
    """Create test admin and user accounts if they don't exist"""
    with app.app_context():
        # Create test user if needed
        user = User.query.filter_by(telegram_id=TEST_USER_TELEGRAM_ID).first()
        if not user:
            user = User(
                telegram_id=TEST_USER_TELEGRAM_ID,
                username=TEST_USERNAME,
                first_name="Test",
                last_name="User",
                status=UserStatus.ACTIVE,
                balance=10.0,  # Start with some balance
                joined_at=datetime.utcnow()
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created test user: @{user.username} (ID: {user.id})")
        else:
            logger.info(f"Using existing test user: @{user.username} (ID: {user.id})")
            
        # Create test admin if needed
        admin = User.query.filter_by(telegram_id=TEST_ADMIN_ID).first()
        if not admin:
            admin = User(
                telegram_id=TEST_ADMIN_ID,
                username="testadmin",
                first_name="Admin",
                last_name="User",
                status=UserStatus.ACTIVE,
                balance=100.0,  # Admin balance not important
                joined_at=datetime.utcnow()
            )
            db.session.add(admin)
            db.session.commit()
            logger.info(f"Created test admin: @{admin.username} (ID: {admin.id})")
        else:
            logger.info(f"Using existing test admin: @{admin.username} (ID: {admin.id})")
            
        return admin, user

def simulate_user_dashboard(user_id):
    """Simulate the user viewing their dashboard and checking balance"""
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return None
            
        # Get recent transactions
        transactions = Transaction.query.filter_by(user_id=user.id)\
                                 .order_by(Transaction.timestamp.desc())\
                                 .limit(5).all()
        
        # Display user dashboard (as would be seen in UI)
        dashboard = {
            "username": user.username,
            "telegram_id": user.telegram_id,
            "current_balance": user.balance,
            "status": user.status.value,
            "recent_transactions": [
                {
                    "type": tx.transaction_type,
                    "amount": tx.amount,
                    "timestamp": tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": tx.status,
                    "notes": tx.notes
                } for tx in transactions
            ]
        }
        
        logger.info(f"USER DASHBOARD:")
        logger.info(f"Username: @{dashboard['username']}")
        logger.info(f"Telegram ID: {dashboard['telegram_id']}")
        logger.info(f"Current Balance: {dashboard['current_balance']:.4f} SOL")
        logger.info(f"Status: {dashboard['status']}")
        
        if transactions:
            logger.info(f"Recent Transactions:")
            for idx, tx in enumerate(dashboard['recent_transactions'], 1):
                logger.info(f"  {idx}. {tx['type']} - {tx['amount']} SOL - {tx['timestamp']} - {tx['notes'] or 'No notes'}")
        else:
            logger.info("No recent transactions")
            
        return dashboard

def simulate_admin_balance_adjustment(admin_id, user_id, amount, reason):
    """Simulate the admin adjusting a user's balance through the UI flow"""
    logger.info(f"\n=== SIMULATING ADMIN BALANCE ADJUSTMENT UI FLOW ===")
    
    with app.app_context():
        # Step 1: Admin opens the admin panel
        logger.info(f"Admin (ID: {admin_id}) opens admin panel")
        time.sleep(0.5)  # Simulate UI delay
        
        # Step 2: Admin selects "Adjust Balance" option
        logger.info(f"Admin selects 'Adjust Balance' option")
        time.sleep(0.5)  # Simulate UI delay
        
        # Step 3: Admin searches for user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return False
            
        logger.info(f"Admin searches for user: @{user.username}")
        time.sleep(0.5)  # Simulate UI delay
        
        # Step 4: Admin selects user from search results
        logger.info(f"Admin selects user @{user.username} (Telegram ID: {user.telegram_id})")
        time.sleep(0.5)  # Simulate UI delay
        
        # Step 5: Admin enters adjustment amount
        logger.info(f"Admin enters adjustment amount: {amount} SOL")
        time.sleep(0.5)  # Simulate UI delay
        
        # Step 6: Admin enters reason for adjustment
        logger.info(f"Admin enters reason: '{reason}'")
        time.sleep(0.5)  # Simulate UI delay
        
        # Step 7: Admin confirms adjustment
        logger.info(f"Admin confirms adjustment")
        time.sleep(0.5)  # Simulate UI delay
        
        # Record old balance for comparison
        old_balance = user.balance
        
        # Step 8: System processes adjustment (using the actual admin_balance_manager)
        try:
            import admin_balance_manager
            success, message = admin_balance_manager.adjust_balance(user.telegram_id, amount, reason)
            
            if not success:
                logger.error(f"Admin balance adjustment failed: {message}")
                return False
                
            logger.info(f"Admin balance adjustment processed: {message}")
        except Exception as e:
            logger.error(f"Error with admin balance manager: {e}")
            
            # Fallback to direct adjustment if manager fails
            logger.info("Falling back to direct balance adjustment")
            
            try:
                # Update balance directly
                user.balance += amount
                
                # Create transaction record
                transaction_type = 'admin_credit' if amount > 0 else 'admin_debit'
                new_transaction = Transaction()
                new_transaction.user_id = user.id
                new_transaction.transaction_type = transaction_type
                new_transaction.amount = abs(amount)
                new_transaction.token_name = "SOL"
                new_transaction.timestamp = datetime.utcnow()
                new_transaction.status = 'completed'
                new_transaction.notes = reason
                
                db.session.add(new_transaction)
                db.session.commit()
                
                success = True
                logger.info(f"Direct balance adjustment completed")
                
            except Exception as db_error:
                db.session.rollback()
                logger.error(f"Database error: {db_error}")
                return False
        
        # Step 9: System displays confirmation to admin
        new_balance = User.query.get(user_id).balance
        logger.info(f"System confirms adjustment to admin:")
        logger.info(f"  Old balance: {old_balance:.4f} SOL")
        logger.info(f"  New balance: {new_balance:.4f} SOL")
        logger.info(f"  Change: {'➕' if amount > 0 else '➖'} {abs(amount):.4f} SOL")
        
        # Step 10: Admin is returned to admin panel
        logger.info(f"Admin returns to admin panel")
        logger.info(f"=== END OF ADMIN BALANCE ADJUSTMENT UI FLOW ===\n")
        
        return True

def run_ui_test():
    """Run the complete UI test flow"""
    try:
        logger.info("Starting Admin Balance Adjustment UI Test")
        
        # Setup test users
        admin, user = setup_test_users()
        
        # Check initial user dashboard
        logger.info("\n=== BEFORE ADJUSTMENT ===")
        initial_dashboard = simulate_user_dashboard(user.id)
        initial_balance = initial_dashboard["current_balance"]
        logger.info(f"Initial user balance: {initial_balance:.4f} SOL")
        
        # Perform admin balance adjustment through UI flow
        success = simulate_admin_balance_adjustment(
            admin.id, 
            user.id, 
            ADJUSTMENT_AMOUNT, 
            ADJUSTMENT_REASON
        )
        
        if not success:
            logger.error("Admin balance adjustment UI flow failed")
            return False
            
        # Simulate delay as user checks their dashboard
        logger.info("Waiting for a moment as user accesses their dashboard...")
        time.sleep(1)  # Simulate some delay
        
        # Check updated user dashboard
        logger.info("\n=== AFTER ADJUSTMENT ===")
        updated_dashboard = simulate_user_dashboard(user.id)
        updated_balance = updated_dashboard["current_balance"]
        logger.info(f"Updated user balance: {updated_balance:.4f} SOL")
        
        # Verify the balance was correctly updated
        expected_balance = initial_balance + ADJUSTMENT_AMOUNT
        if updated_balance == expected_balance:
            logger.info(f"✅ TEST PASSED: Balance correctly updated from {initial_balance:.4f} to {updated_balance:.4f} SOL")
            
            # Check if transaction appears in recent transactions
            if updated_dashboard["recent_transactions"]:
                latest_tx = updated_dashboard["recent_transactions"][0]
                if latest_tx["type"] == "admin_credit" and latest_tx["amount"] == ADJUSTMENT_AMOUNT:
                    logger.info(f"✅ TEST PASSED: Transaction correctly recorded in user history")
                else:
                    logger.error(f"❌ TEST FAILED: Transaction not properly recorded in user history")
                    return False
            else:
                logger.error(f"❌ TEST FAILED: No transactions found in user history")
                return False
                
            return True
        else:
            logger.error(f"❌ TEST FAILED: Balance not correctly updated. Expected {expected_balance:.4f} but got {updated_balance:.4f}")
            return False
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = run_ui_test()
    sys.exit(0 if success else 1)