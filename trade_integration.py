"""
Trade Integration - Adds the new trade format to the bot
This script integrates the trade execution system with the bot
allowing admins to use the Buy/Sell format directly
"""

import logging
import os
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def integrate_trade_format():
    """
    Integrate the new trade format with the bot
    
    This adds a command handler for admin trade messages in the format:
    Buy $TOKEN PRICE TX_LINK or Sell $TOKEN PRICE TX_LINK
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
            
        # First, check if simple_trade_handler.py exists
        if not os.path.exists('simple_trade_handler.py'):
            logger.error("simple_trade_handler.py not found")
            return False
            
        # Read the file content
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
            
        # Check if it's already integrated
        if 'import simple_trade_handler' in content:
            logger.info("Trade format already integrated")
            return True
            
        # Add the import
        import_pattern = r'(import os\nimport sys\nimport requests\nimport time\nimport json\nimport random)'
        import_replacement = 'import os\nimport sys\nimport requests\nimport time\nimport json\nimport random\nimport simple_trade_handler'
        
        content = content.replace(import_pattern, import_replacement)
        
        # Find the process_message function
        process_pattern = r'(def process_message\(update\):)'
        process_match = re.search(process_pattern, content)
        
        if not process_match:
            logger.error("Could not find process_message function")
            return False
            
        # Find a good insertion point for the trade handler
        insertion_pattern = r'(message\s*=\s*update\.get\(\'message\'\)\s*if\s*update\.get\(\'message\'\)\s*else\s*update\.get\(\'callback_query\'\).*?\n\s*)(if\s*message\.get\(\'text\'\))'
        insertion_match = re.search(insertion_pattern, content, re.DOTALL)
        
        if not insertion_match:
            logger.error("Could not find insertion point")
            return False
            
        # Code to insert for handling trade messages
        trade_handler = """
        # Check for simple trade messages (Buy/Sell format)
        if message.get('text') and not message['text'].startswith('/'):
            # Get message text and chat_id
            text = message['text']
            chat_id = str(message['chat']['id'])
            
            # Check if this looks like a trade message
            if text.lower().startswith('buy ') or text.lower().startswith('sell '):
                # Check if user is admin
                user_id = message['from']['id']
                if is_admin(user_id):
                    try:
                        # Process the trade message
                        success, response, details = simple_trade_handler.handle_trade_message(text, user_id, bot)
                        
                        # Send response
                        bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)
                        
                        # If it was a successful SELL, notify users
                        if success and details and details.get('trade_type') == 'sell' and details.get('roi_percentage') is not None:
                            logger.info(f"Trade processed: {details.get('token')} with ROI {details.get('roi_percentage'):.2f}%")
                        
                        return  # Don't process further
                    except Exception as e:
                        logger.error(f"Error processing trade message: {e}")
                        bot.send_message(chat_id, f"⚠️ Error processing trade message: {str(e)}")
                        return
                else:
                    # Non-admin tried to use trade format
                    bot.send_message(chat_id, "⚠️ Only admins can post trades in this format.")
                    return
        
        """
        
        # Insert the trade handler
        new_content = content[:insertion_match.end(1)] + trade_handler + content[insertion_match.end(1):]
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(new_content)
            
        logger.info("Successfully integrated trade format with the bot")
        return True
        
    except Exception as e:
        logger.error(f"Error integrating trade format: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def add_trade_help_command():
    """
    Add a trade help command to the bot
    
    This adds a /trade_help command for admins to see
    instructions on how to use the new trade format
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
            
        # Read the file content
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
            
        # Check if it's already added
        if '/trade_help' in content:
            logger.info("Trade help command already added")
            return True
            
        # Find the command handler function
        command_pattern = r'(def command_handler\(update\):)'
        command_match = re.search(command_pattern, content)
        
        if not command_match:
            logger.error("Could not find command_handler function")
            return False
            
        # Find a good insertion point
        insertion_pattern = r'(elif\s*command\s*==\s*\'/help\':\s*.*?\n\s*)(elif|else)'
        insertion_match = re.search(insertion_pattern, content, re.DOTALL)
        
        if not insertion_match:
            logger.error("Could not find insertion point for trade_help command")
            return False
            
        # Code to insert for the trade_help command
        trade_help = """
        elif command == '/trade_help':
            # Only admins can use this command
            if is_admin(update['message']['from']['id']):
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
                bot.send_message(chat_id, help_text, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "⚠️ Only admins can use this command.")
                
        """
        
        # Insert the trade help command
        new_content = content[:insertion_match.end(1)] + trade_help + content[insertion_match.end(1):]
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(new_content)
            
        logger.info("Successfully added trade help command")
        return True
        
    except Exception as e:
        logger.error(f"Error adding trade help command: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Integrating trade format with the bot...")
    
    # First, integrate the trade format
    if integrate_trade_format():
        print("✅ Trade format integration successful")
    else:
        print("❌ Trade format integration failed")
    
    # Then, add the trade help command
    if add_trade_help_command():
        print("✅ Trade help command added successfully")
    else:
        print("❌ Trade help command addition failed")