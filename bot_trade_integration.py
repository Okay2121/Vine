"""
Bot Integration for Simple Trade Message Handler
------------------------------------------------
This script integrates the simple trade message handler with the bot_v20_runner.py file
to process "Buy $TOKEN PRICE TX_LINK" and "Sell $TOKEN PRICE TX_LINK" messages.
"""

import os
import re
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def integrate_trade_handler():
    """
    Add the simple trade handler integration to the bot_v20_runner.py file
    """
    try:
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
        
        # Check if simple_trade_handler.py exists
        if not os.path.exists('simple_trade_handler.py'):
            logger.error("simple_trade_handler.py not found")
            return False
        
        # Read the file content
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # First, add import for simple_trade_handler
        import_pattern = r'import os\nimport sys\nimport requests\nimport time\nimport json\nimport random'
        import_replacement = 'import os\nimport sys\nimport requests\nimport time\nimport json\nimport random\nimport simple_trade_handler'
        
        if 'import simple_trade_handler' not in content:
            content = content.replace(import_pattern, import_replacement)
            logger.info("Added import for simple_trade_handler")
        
        # Find the process_message function
        process_message_pattern = r'def process_message\(update\):'
        process_message_match = re.search(process_message_pattern, content)
        
        if not process_message_match:
            logger.error("Could not find process_message function")
            return False
        
        # Insert the trade message handler logic into the process_message function
        # Find a good insertion point - the first if/elif block after text assignment
        insertion_pattern = r'(message\s*=\s*update\.get\(\'message\'\)\s*if\s*update\.get\(\'message\'\)\s*else\s*update\.get\(\'callback_query\'\).*?\n\s*)(if\s*message\.get\(\'text\'\)\s*and\s*message\[\'text\'\]\.startswith\(\'/\'\):)'
        
        insertion_match = re.search(insertion_pattern, content, re.DOTALL)
        if not insertion_match:
            logger.error("Could not find insertion point for trade message handler")
            return False
        
        # Create the trade message handler code
        trade_handler_code = """        # Check for simple trade messages (Buy/Sell format)
        if message.get('text') and not message['text'].startswith('/'):
            # Get message text and chat_id
            text = message['text']
            chat_id = str(message['chat']['id'])
            
            # Check if this might be a trade message
            if text.lower().startswith('buy ') or text.lower().startswith('sell '):
                # Check if user is admin
                user_id = message['from']['id']
                if is_admin(user_id):
                    try:
                        # Process the trade message
                        success, response, details = simple_trade_handler.handle_trade_message(text, user_id, bot)
                        
                        # Send response
                        bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)
                        
                        # If it was a successful SELL with ROI, update user metrics
                        if success and details and details.get('trade_type') == 'sell' and details.get('roi_percentage'):
                            # Update user metrics if needed (handled in simple_trade_handler)
                            pass
                        
                        return  # Don't process further
                    except Exception as e:
                        logger.error(f"Error processing trade message: {e}")
                        bot.send_message(chat_id, f"⚠️ Error processing trade message: {str(e)}")
                        return
        
        """
        
        # Insert the trade handler code
        updated_content = content[:insertion_match.end(1)] + trade_handler_code + content[insertion_match.end(1):]
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(updated_content)
        
        logger.info("Successfully integrated trade message handler into bot_v20_runner.py")
        return True
    except Exception as e:
        logger.error(f"Error integrating trade handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def add_admin_trade_help_command():
    """
    Add a help command for the new trade format
    """
    try:
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
        
        # Read the file content
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # Find the admin_command_handler function
        admin_handler_pattern = r'def admin_command_handler\(update, chat_id\):'
        admin_handler_match = re.search(admin_handler_pattern, content)
        
        if not admin_handler_match:
            logger.error("Could not find admin_command_handler function")
            return False
        
        # Find insertion point inside the admin menu keyboard
        keyboard_pattern = r'(\s*keyboard\s*=\s*\[\s*# Admin panel main menu items\s*\[\s*.*?\]\s*,\s*.*?\]\s*,)'
        keyboard_match = re.search(keyboard_pattern, content, re.DOTALL)
        
        if not keyboard_match:
            logger.error("Could not find admin menu keyboard")
            return False
        
        # Create new admin menu option for trade help
        new_menu_option = """
        # Trade system buttons
        [
            {"text": "📊 Trade System", "callback_data": "admin_trade_system"},
        ],"""
        
        # Insert the new menu option
        updated_content = content[:keyboard_match.end(1)] + new_menu_option + content[keyboard_match.end(1):]
        
        # Now add the callback handler for admin_trade_system
        callback_pattern = r'(\s*# Add all admin panel callback handlers\s*handlers\s*=\s*\{)'
        callback_match = re.search(callback_pattern, content)
        
        if not callback_match:
            logger.error("Could not find admin callback handlers")
            return False
        
        # Add the new callback handler entry
        new_callback = """
        'admin_trade_system': admin_trade_system_handler,"""
        
        # Insert the new callback
        updated_content = updated_content[:callback_match.end(1)] + new_callback + updated_content[callback_match.end(1):]
        
        # Finally, add the admin_trade_system_handler function
        function_pattern = r'(def admin_exit_handler\(update, chat_id\):.*?\n\s*return\s*\n)'
        function_match = re.search(function_pattern, content, re.DOTALL)
        
        if not function_match:
            logger.error("Could not find insertion point for admin_trade_system_handler")
            return False
        
        # Create the new handler function
        new_function = """
def admin_trade_system_handler(update, chat_id):
    \"\"\"Show admin trade system help and options.\"\"\""
    try:
        help_text = (
            "📊 *Simple Trade System*\\n\\n"
            "*New Format:*\\n"
            "Simply type a message with the following format:\\n\\n"
            "`Buy $TOKEN PRICE TX_LINK`\\n"
            "or\\n"
            "`Sell $TOKEN PRICE TX_LINK`\\n\\n"
            "*Examples:*\\n"
            "`Buy $ZING 0.0041 https://solscan.io/tx/abc123`\\n"
            "`Sell $ZING 0.0065 https://solscan.io/tx/def456`\\n\\n"
            "✅ *How It Works:*\\n"
            "1. BUY orders are stored for matching\\n"
            "2. SELL orders auto-match with the oldest BUY\\n"
            "3. ROI calculated as ((Sell - Buy) / Buy) × 100\\n"
            "4. Profit applied to all active users' balances\\n"
            "5. Users receive personalized trade notifications\\n\\n"
            "📌 *Note:* Timestamps are recorded automatically"
        )
        
        # Back button
        keyboard = [
            [
                {"text": "◀️ Back to Admin Panel", "callback_data": "admin_back"}
            ]
        ]
        reply_markup = {"inline_keyboard": keyboard}
        
        bot.send_message(chat_id, help_text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in admin_trade_system_handler: {e}")
        bot.send_message(chat_id, f"Error: {str(e)}")

"""
        
        # Insert the new function
        updated_content = updated_content[:function_match.end()] + new_function + updated_content[function_match.end():]
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(updated_content)
        
        logger.info("Successfully added admin trade help command to bot_v20_runner.py")
        return True
    except Exception as e:
        logger.error(f"Error adding admin trade help command: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    print("Integrating simple trade handler with the Telegram bot...")
    
    # First integrate the trade handler
    if integrate_trade_handler():
        print("✅ Trade handler integration successful")
    else:
        print("❌ Trade handler integration failed")
        
    # Add the admin trade help command
    if add_admin_trade_help_command():
        print("✅ Admin trade help command added successfully")
    else:
        print("❌ Admin trade help command addition failed")