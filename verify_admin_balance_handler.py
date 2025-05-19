#!/usr/bin/env python
"""
Script to check if admin_adjust_balance_handler is defined in bot_v20_runner.py
and properly invokes the admin_adjust_balance_user_id_handler function
"""
import re
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_admin_balance_handlers():
    """Check if the admin balance adjustment handlers are defined properly"""
    
    # Path to the file
    file_path = 'bot_v20_runner.py'
    
    try:
        # Read the file
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Check if admin_adjust_balance_handler is defined
        if re.search(r'def\s+admin_adjust_balance_handler\s*\(', content):
            logger.info("✅ admin_adjust_balance_handler function is defined")
        else:
            logger.error("❌ admin_adjust_balance_handler function is NOT defined")
            
        # Check if admin_adjust_balance_user_id_handler is defined
        if re.search(r'def\s+admin_adjust_balance_user_id_handler\s*\(', content):
            logger.info("✅ admin_adjust_balance_user_id_handler function is defined")
        else:
            logger.error("❌ admin_adjust_balance_user_id_handler function is NOT defined")
            
        # Check if the bot adds a listener for the username input
        if re.search(r'bot\.add_message_listener\s*\(\s*chat_id\s*,\s*"text"\s*,\s*admin_adjust_balance_user_id_handler\s*\)', content):
            logger.info("✅ Bot correctly adds listener for admin_adjust_balance_user_id_handler")
        else:
            logger.error("❌ Bot does NOT add listener for admin_adjust_balance_user_id_handler")
            
        # Check if case-insensitive username search is implemented
        if 'func.lower(User.username) == func.lower(' in content:
            logger.info("✅ Case-insensitive username search is implemented")
        else:
            logger.error("❌ Case-insensitive username search is NOT implemented")
            
        return True
        
    except Exception as e:
        logger.error(f"Error checking handlers: {e}")
        return False

if __name__ == "__main__":
    # Check the handlers
    check_admin_balance_handlers()