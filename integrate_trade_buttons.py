#!/usr/bin/env python
"""
Integrate Trade Buttons
This script adds trade history and simulation buttons to your existing bot.
Run this file to directly modify the main menu and dashboard of your bot.
"""
import logging
import os
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_trade_buttons_to_bot():
    """
    Add trade history and simulation buttons to the bot.
    This function directly modifies the bot files.
    """
    # Find all relevant bot files
    bot_files = []
    for file in os.listdir('.'):
        if file.startswith('bot_') and file.endswith('.py'):
            bot_files.append(file)
    
    if not bot_files:
        logger.error("No bot files found. Make sure you're in the correct directory.")
        return False
    
    logger.info(f"Found bot files: {', '.join(bot_files)}")
    
    # Keep track of which files were modified
    modified_files = []
    
    # Process each bot file
    for file_name in bot_files:
        try:
            with open(file_name, 'r') as file:
                content = file.read()
            
            # Check if this file has a main menu
            if "Dashboard" in content and "callback_data" in content:
                logger.info(f"Modifying {file_name}...")
                
                # Add new buttons to main menu
                main_menu_pattern = r'(keyboard\s*=\s*\[\s*\[[^\]]*\],\s*\[[^\]]*\],\s*\[[^\]]*\]\s*\])'
                if re.search(main_menu_pattern, content):
                    content = re.sub(
                        main_menu_pattern,
                        r'\1 + [\n        {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},\n        {"text": "📜 Trade History", "callback_data": "view_trade_history"}\n    ]',
                        content
                    )
                    logger.info(f"Added trade buttons to main menu in {file_name}")
                
                # Add new buttons to dashboard keyboard
                dashboard_pattern = r'(keyboard\s*=\s*bot\.create_inline_keyboard\(\[\s*\[[^\]]*\],\s*\[[^\]]*\],\s*\[[^\]]*\]\s*\]))'
                if re.search(dashboard_pattern, content):
                    content = re.sub(
                        dashboard_pattern,
                        r'\1 + [\n                [\n                    {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},\n                    {"text": "📜 Trade History", "callback_data": "view_trade_history"}\n                ]\n            ]',
                        content
                    )
                    logger.info(f"Added trade buttons to dashboard in {file_name}")
                
                # Add callback handlers for the buttons
                callback_pattern = r'(bot\.add_callback_handler\([^)]*\)\s*bot\.add_callback_handler\([^)]*\)\s*)'
                if re.search(callback_pattern, content):
                    handlers_to_add = '\n    bot.add_callback_handler("simulate_trade", lambda update, chat_id: bot.send_message(chat_id, "Use /simulate to generate a new trade"))' + \
                                     '\n    bot.add_callback_handler("view_trade_history", lambda update, chat_id: bot.send_message(chat_id, "Use /history to view your simulated trade history"))\n    '
                    content = re.sub(callback_pattern, r'\1' + handlers_to_add, content)
                    logger.info(f"Added button handlers in {file_name}")
                
                # Write the modified content back to the file
                with open(file_name, 'w') as file:
                    file.write(content)
                
                modified_files.append(file_name)
                logger.info(f"Successfully modified {file_name}")
        
        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}")
    
    # Create a direct integration file for the yield module
    create_direct_integration_file()
    
    return len(modified_files) > 0

def create_direct_integration_file():
    """Create a direct integration file for the yield module."""
    file_name = 'integrate_yield_module.py'
    
    content = '''#!/usr/bin/env python
"""
Integrate Yield Module
Add this single import line to your main bot file to activate the yield module.
"""
from yield_module import setup_yield_module

def integrate_with_bot(application):
    """
    Integrate the yield module with your Telegram bot.
    
    Args:
        application: The Telegram bot application
    """
    # Setup the yield module
    setup_yield_module(application)
    
    print("Yield module successfully integrated with your bot!")
    print("Users can now access:")
    print("  /simulate - Generate a simulated trade")
    print("  /history - View trade history")
    print("  /balance - Check simulated balance")

# Example usage in your main bot file:
"""
from telegram.ext import Application
from integrate_yield_module import integrate_with_bot

# Create your application
application = Application.builder().token(BOT_TOKEN).build()

# Add your existing handlers
# ...

# Integrate the yield module
integrate_with_bot(application)

# Start your application
application.run_polling()
"""
'''
    
    with open(file_name, 'w') as file:
        file.write(content)
    
    logger.info(f"Created {file_name} for easy integration")

if __name__ == "__main__":
    print("Adding trade buttons to your bot...")
    success = add_trade_buttons_to_bot()
    
    if success:
        print("\n✅ Trade buttons added successfully!")
        print("\nTo complete the integration:")
        print("1. Add the yield module to your main bot file:")
        print("   from yield_module import setup_yield_module")
        print("   setup_yield_module(application)")
        print("   or")
        print("   from integrate_yield_module import integrate_with_bot")
        print("   integrate_with_bot(application)")
        print("\n2. Restart your bot")
    else:
        print("\n❌ No files were modified. Please check the logs.")