#!/usr/bin/env python
"""
Test Day Counter with SOL Balance
---------------------------------
This script creates a test scenario with a user who has SOL to confirm
the day counter works properly when users have funds.
"""

from app import app, db
from models import User, Transaction, UserStatus
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_user_with_sol():
    """Test day counter for a user with SOL balance"""
    
    with app.app_context():
        # Find a user or use admin balance manager to give someone SOL
        from admin_balance_manager import adjust_balance
        
        # Find an existing user
        test_user = User.query.first()
        if not test_user:
            logger.info("No users found in database")
            return
            
        logger.info(f"Testing with user: {test_user.telegram_id}")
        logger.info(f"Current balance: {test_user.balance} SOL")
        
        # Give them some SOL if they don't have any
        if test_user.balance <= 0:
            logger.info("Adding 1.5 SOL to test user...")
            success, message = adjust_balance(test_user.telegram_id, 1.5, "Test deposit for day counter")
            if success:
                logger.info("✓ Successfully added SOL to test user")
                # Refresh user data
                db.session.refresh(test_user)
            else:
                logger.error(f"Failed to add SOL: {message}")
                return
        
        # Now test the day counter logic (same as in dashboard)
        first_deposit = Transaction.query.filter_by(
            user_id=test_user.id, 
            transaction_type='deposit',
            status='completed'
        ).order_by(Transaction.timestamp).first()
        
        if first_deposit and test_user.balance > 0:
            days_active = (datetime.utcnow().date() - first_deposit.timestamp.date()).days + 1
            logger.info(f"✓ User has SOL ({test_user.balance:.2f}) and deposit record")
            logger.info(f"✓ First deposit: {first_deposit.timestamp.date()}")
            logger.info(f"✓ Days active: {days_active}")
        elif test_user.balance > 0:
            days_active = (datetime.utcnow().date() - test_user.joined_at.date()).days + 1
            logger.info(f"✓ User has SOL ({test_user.balance:.2f}) but no deposit record")
            logger.info(f"✓ Using join date: {test_user.joined_at.date()}")
            logger.info(f"✓ Days active: {days_active}")
        else:
            days_active = 0
            logger.info(f"✗ User has no SOL - days active: {days_active}")
            
        # Show what the dashboard would display
        if days_active > 0:
            dashboard_text = f"• Day: {days_active}"
        else:
            dashboard_text = "• Day: Start your streak today!"
            
        logger.info(f"Dashboard would show: '{dashboard_text}'")
        
        return days_active > 0

if __name__ == "__main__":
    test_user_with_sol()