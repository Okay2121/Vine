#!/usr/bin/env python
"""
This script adds support for the trade broadcast format shown in the image:
$TOKEN_NAME ENTRY_PRICE EXIT_PRICE ROI_PERCENT TX_HASH [OPTIONAL:TRADE_TYPE]
"""

import os
import re
import sys
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def update_trade_format():
    """Update the bot to handle the new trade broadcast format"""
    try:
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
        
        # Read the file content
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # Import the trade_broadcast_handler
        import_line = "import trade_broadcast_handler"
        if import_line not in content:
            # Add import after the other imports
            import_section = "import os\nimport sys\nimport requests\nimport time\nimport json\nimport random"
            new_import_section = import_section + "\n" + import_line
            content = content.replace(import_section, new_import_section)
            logger.info("Added import for trade_broadcast_handler")
        
        # Add new admin_broadcast_trade_handler function
        if 'def admin_broadcast_trade_handler' in content:
            logger.info("admin_broadcast_trade_handler function already exists, updating it")
            
            # Find the existing function
            pattern = r'def admin_broadcast_trade_handler\(update, chat_id\):.*?(?=def \w+)'
            match = re.search(pattern, content, re.DOTALL)
            
            if not match:
                logger.error("Could not find admin_broadcast_trade_handler function")
                return False
            
            # Replace the function with our implementation
            new_function = """def admin_broadcast_trade_handler(update, chat_id):
    """Handle admin broadcasting of trade information with the format: $TOKEN ENTRY EXIT ROI TX_HASH [TYPE]"""
    try:
        # Check for admin privileges
        if not is_admin(update['callback_query']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return
            
        # Show input instructions for the trade broadcast
        with app.app_context():
            # Get active user count
            active_users = User.query.filter(User.balance > 0).count()
            
            # Format example trade message
            message = (
                "📊 *Broadcast Trade Alert*\\n\\n"
                f"*Active Users:* {active_users}\\n\\n"
                "Send the trade details in the following format:\\n"
                "$TOKEN_NAME ENTRY_PRICE EXIT_PRICE ROI_PERCENT TX_HASH [OPTIONAL:TRADE_TYPE]\\n\\n"
                "Examples:\\n"
                "$ZING 0.0041 0.0074 80.5 https://solscan.io/tx/abc123\\n"
                "$ZING 0.0041 0.0074 80.5 https://solscan.io/tx/abc123 scalp\\n\\n"
                "This will be broadcast to all active users with personalized profit calculations based on their balance."
            )
            
            # Add cancel button
            keyboard = bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "admin_broadcast"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, "broadcast_trade", admin_broadcast_trade_message_handler)
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error setting up trade broadcast: {str(e)}")

"""
            content = content.replace(match.group(0), new_function)
            logger.info("Updated admin_broadcast_trade_handler function")
        else:
            logger.info("admin_broadcast_trade_handler function doesn't exist, adding it")
            
            # Find a good insertion point, after another handler
            pattern = r'def admin_broadcast_announcement_handler\(update, chat_id\):.*?(?=def \w+)'
            match = re.search(pattern, content, re.DOTALL)
            
            if not match:
                logger.error("Could not find insertion point for admin_broadcast_trade_handler")
                return False
            
            # Create new function
            new_function = """
def admin_broadcast_trade_handler(update, chat_id):
    """Handle admin broadcasting of trade information with the format: $TOKEN ENTRY EXIT ROI TX_HASH [TYPE]"""
    try:
        # Check for admin privileges
        if not is_admin(update['callback_query']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return
            
        # Show input instructions for the trade broadcast
        with app.app_context():
            # Get active user count
            active_users = User.query.filter(User.balance > 0).count()
            
            # Format example trade message
            message = (
                "📊 *Broadcast Trade Alert*\\n\\n"
                f"*Active Users:* {active_users}\\n\\n"
                "Send the trade details in the following format:\\n"
                "$TOKEN_NAME ENTRY_PRICE EXIT_PRICE ROI_PERCENT TX_HASH [OPTIONAL:TRADE_TYPE]\\n\\n"
                "Examples:\\n"
                "$ZING 0.0041 0.0074 80.5 https://solscan.io/tx/abc123\\n"
                "$ZING 0.0041 0.0074 80.5 https://solscan.io/tx/abc123 scalp\\n\\n"
                "This will be broadcast to all active users with personalized profit calculations based on their balance."
            )
            
            # Add cancel button
            keyboard = bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "admin_broadcast"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, "broadcast_trade", admin_broadcast_trade_message_handler)
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error setting up trade broadcast: {str(e)}")

"""
            content = content[:match.end()] + new_function + content[match.end():]
            logger.info("Added admin_broadcast_trade_handler function")
        
        # Add message handler for processing trade broadcasts
        if 'def admin_broadcast_trade_message_handler' in content:
            logger.info("admin_broadcast_trade_message_handler function already exists, updating it")
            
            # Find the existing function
            pattern = r'def admin_broadcast_trade_message_handler\(update, chat_id, text\):.*?(?=def \w+|\Z)'
            match = re.search(pattern, content, re.DOTALL)
            
            if not match:
                logger.error("Could not find admin_broadcast_trade_message_handler function")
                return False
            
            # Replace the function with our implementation
            new_function = """def admin_broadcast_trade_message_handler(update, chat_id, text):
    """Process the trade broadcast message from admin."""
    try:
        # Remove the listener
        bot.remove_listener(chat_id)
        
        # Process the trade broadcast
        success, response = trade_broadcast_handler.handle_broadcast_message(text, bot, chat_id)
        
        # Send response
        bot.send_message(
            chat_id,
            response,
            parse_mode="Markdown"
        )
        
        # Return to broadcast menu if successful
        if success:
            # Add a slight delay to ensure notifications are sent
            import time
            time.sleep(1)
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Broadcast Menu", "callback_data": "admin_broadcast"}]
            ])
            
            bot.send_message(
                chat_id,
                "What would you like to do next?",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing trade broadcast: {str(e)}")

"""
            content = content.replace(match.group(0), new_function)
            logger.info("Updated admin_broadcast_trade_message_handler function")
        else:
            logger.info("admin_broadcast_trade_message_handler function doesn't exist, adding it")
            
            # Find a good insertion point, after another handler
            pattern = r'def admin_broadcast_announcement_message_handler\(update, chat_id, text\):.*?(?=def \w+|\Z)'
            match = re.search(pattern, content, re.DOTALL)
            
            if not match:
                logger.error("Could not find insertion point for admin_broadcast_trade_message_handler")
                return False
            
            # Create new function
            new_function = """
def admin_broadcast_trade_message_handler(update, chat_id, text):
    """Process the trade broadcast message from admin."""
    try:
        # Remove the listener
        bot.remove_listener(chat_id)
        
        # Process the trade broadcast
        success, response = trade_broadcast_handler.handle_broadcast_message(text, bot, chat_id)
        
        # Send response
        bot.send_message(
            chat_id,
            response,
            parse_mode="Markdown"
        )
        
        # Return to broadcast menu if successful
        if success:
            # Add a slight delay to ensure notifications are sent
            import time
            time.sleep(1)
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Broadcast Menu", "callback_data": "admin_broadcast"}]
            ])
            
            bot.send_message(
                chat_id,
                "What would you like to do next?",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing trade broadcast: {str(e)}")

"""
            content = content[:match.end()] + new_function + content[match.end():]
            logger.info("Added admin_broadcast_trade_message_handler function")
        
        # Check if the trade broadcast callback is registered
        callback_registration = "'admin_broadcast_trade': admin_broadcast_trade_handler,"
        if callback_registration not in content:
            # Find the callback handlers section
            pattern = r'# Add all admin panel callback handlers\s*handlers\s*=\s*{'
            match = re.search(pattern, content)
            
            if not match:
                logger.error("Could not find callback handlers section")
                return False
            
            # Add the callback registration
            new_content = content[:match.end()] + "\n        " + callback_registration + content[match.end():]
            content = new_content
            logger.info("Added callback registration for admin_broadcast_trade")
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(content)
        
        logger.info("Successfully updated bot_v20_runner.py")
        return True
    except Exception as e:
        logger.error(f"Error updating trade format: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Updating bot with new trade broadcast format...")
    if update_trade_format():
        print("✅ Update successful")
    else:
        print("❌ Update failed")