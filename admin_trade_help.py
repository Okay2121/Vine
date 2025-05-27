"""
Admin Trade Help - Guide for using the simplified trade format
Provides instructions and examples for the new Buy/Sell trade format
"""

import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def show_trade_system_help(bot, chat_id):
    """
    Display help information about the new trade system
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send the message to
    """
    help_text = (
        "📊 *Broadcast Trade Alert - New Format*\n\n"
        "Send the trade details in one of these formats:\n\n"
        "`Buy $TOKEN PRICE AMOUNT TX_LINK`\n"
        "`Sell $TOKEN PRICE AMOUNT TX_LINK`\n\n"
        "*Examples:*\n"
        "`Buy $ZING 0.004107 812345 https://solscan.io/tx/abc123`\n"
        "`Sell $ZING 0.006834 812345 https://solscan.io/tx/def456`\n\n"
        "*Format Breakdown:*\n"
        "• Buy/Sell — trade type\n"
        "• $ZING — token symbol\n"
        "• 812345 — amount of tokens\n"
        "• 0.0041 / 0.0068 — token price (entry or exit)\n"
        "• Transaction Link — proof of trade (Solscan)\n\n"
        "✅ *How It Works:*\n"
        "1. BUY orders are stored for matching\n"
        "2. SELL orders auto-match with the oldest BUY\n"
        "3. ROI calculated as ((Sell - Buy) / Buy) × 100\n"
        "4. Profit applied to all active users' balances\n"
        "5. Users receive personalized trade notifications\n\n"
        "📌 *Note:* Timestamps are recorded automatically\n\n"
        "When a trade is completed (BUY + SELL):\n"
        "• User balances are updated instantly\n"
        "• Transaction history is updated immediately\n"
        "• Trading positions are recorded with complete details\n"
        "• Users receive immediate personalized notifications"
    )
    
    # Back button to admin panel
    keyboard = [
        [
            {"text": "◀️ Back to Admin Panel", "callback_data": "admin_back"}
        ]
    ]
    reply_markup = {"inline_keyboard": keyboard}
    
    bot.send_message(chat_id, help_text, parse_mode="Markdown", reply_markup=reply_markup)

def add_to_admin_panel():
    """
    Add the trade system help to the admin panel
    
    This function modifies the bot_v20_runner.py file to add:
    1. A button in the admin panel
    2. A callback handler for the button
    3. The help display function
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import os
        import re
        
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
        
        # Read the file content
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # Find admin menu insertion point
        admin_menu_pattern = r'(\s*keyboard\s*=\s*\[\s*# Admin panel main menu items)'
        admin_menu_match = re.search(admin_menu_pattern, content)
        
        if not admin_menu_match:
            logger.error("Could not find admin menu in bot_v20_runner.py")
            return False
        
        # Check if trade system button already exists
        if "Trade System" in content and "admin_trade_system" in content:
            logger.info("Trade system already in admin panel, no changes needed")
            return True
        
        # Create button for admin panel
        admin_menu_button = """
            # Trade System button
            [
                {"text": "📊 Trade System Guide", "callback_data": "admin_trade_system"},
            ],"""
        
        # Insert the button in the admin menu
        new_content = content[:admin_menu_match.end()] + admin_menu_button + content[admin_menu_match.end():]
        
        # Find the callback handlers section
        callback_pattern = r'(\s*# Add all admin panel callback handlers\s*handlers\s*=\s*\{)'
        callback_match = re.search(callback_pattern, new_content)
        
        if not callback_match:
            logger.error("Could not find callback handlers section in bot_v20_runner.py")
            return False
        
        # Add the callback handler for trade system
        callback_entry = """
        'admin_trade_system': admin_trade_system_handler,"""
        
        # Insert the callback handler
        new_content = new_content[:callback_match.end()] + callback_entry + new_content[callback_match.end():]
        
        # Find a good place to add the handler function
        func_pattern = r'(def admin_exit_handler\(update, chat_id\):.*?\n\s*return\s*\n)'
        func_match = re.search(func_pattern, new_content, re.DOTALL)
        
        if not func_match:
            logger.error("Could not find insertion point for admin_trade_system_handler")
            return False
        
        # Import admin_trade_help at the top
        import_pattern = r'(import os\nimport sys\nimport requests\nimport time\nimport json\nimport random)'
        import_match = re.search(import_pattern, new_content)
        
        if import_match:
            import_line = 'import os\nimport sys\nimport requests\nimport time\nimport json\nimport random\nimport admin_trade_help'
            new_content = new_content.replace(import_match.group(1), import_line)
        
        # Create the handler function
        handler_func = """
def admin_trade_system_handler(update, chat_id):
    \"\"\"Handle admin_trade_system callback - shows the trade system guide.\"\"\"
    try:
        # Use admin_trade_help to show the help
        admin_trade_help.show_trade_system_help(bot, chat_id)
    except Exception as e:
        logger.error(f"Error in admin_trade_system_handler: {e}")
        bot.send_message(chat_id, f"Error showing trade system guide: {str(e)}")

"""
        
        # Insert the handler function
        new_content = new_content[:func_match.end()] + handler_func + new_content[func_match.end():]
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(new_content)
        
        logger.info("Successfully added trade system help to admin panel")
        return True
    except Exception as e:
        logger.error(f"Error adding trade system to admin panel: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Adding trade system help to admin panel...")
    if add_to_admin_panel():
        print("✅ Trade system help added to admin panel successfully")
    else:
        print("❌ Failed to add trade system help to admin panel")