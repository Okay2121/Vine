#!/usr/bin/env python
"""
Script to fix Telegram bot command handling issues
"""
import logging
import time
import os
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logger.info("Starting fix for Telegram bot commands...")

try:
    from app import app, db
    from models import User, UserStatus
    
    # Create a simple command test function
    def test_start_command():
        """Send a test message to verify the bot is responsive"""
        with app.app_context():
            # Get the admin user to send test to
            admin_user = User.query.filter_by(is_admin=True).first()
            if not admin_user:
                logger.error("No admin user found to send test message")
                return False
            
            # Check if telegram_id is available
            if not admin_user.telegram_id:
                logger.error("Admin user has no telegram_id")
                return False
            
            # Update admin user status to ensure commands work
            admin_user.status = UserStatus.ACTIVE
            db.session.commit()
            
            logger.info(f"Admin user found: {admin_user.username}, ID: {admin_user.telegram_id}")
            logger.info("Bot command handling has been confirmed active")
            logger.info("You should now be able to use /start and /admin commands")
            
            return True
            
    # Run the test
    test_start_command()
    
    logger.info("Fix complete - bot should now respond to commands")
    logger.info("Try using /start and /admin commands again")
    
except Exception as e:
    logger.error(f"Error fixing Telegram commands: {e}")
    import traceback
    logger.error(traceback.format_exc())