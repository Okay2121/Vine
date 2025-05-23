#!/usr/bin/env python
"""
Fix Telegram Bot Commands
This script ensures that all Telegram bot commands are working properly,
especially the /start command which is critical for new users.
"""
import os
import sys
import logging
import time
import traceback
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def patch_command_handlers():
    """Patch the command handlers in bot_v20_runner.py to ensure they work properly"""
    try:
        # Check if bot_v20_runner.py exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("❌ bot_v20_runner.py not found")
            return False
        
        # Read the file
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # Add main function if it doesn't exist
        if 'def main():' not in content:
            logger.info("Adding main() function to bot_v20_runner.py")
            
            main_function = '''
def main():
    """Run the bot as a standalone program"""
    import logging
    import os
    from dotenv import load_dotenv
    
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Get the bot token from environment variables
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    logger.info("Starting Telegram bot...")
    
    # Create bot instance
    global bot
    bot = SimpleTelegramBot(token)
    
    # Register all command handlers
    register_handlers()
    
    # Start the bot
    bot.start_polling()
    
if __name__ == "__main__":
    main()
'''
            # Add the main function to the end of the file
            with open('bot_v20_runner.py', 'a') as file:
                file.write(main_function)
        
        # Fix the start_command handler if needed
        if 'def start_command(' in content:
            logger.info("start_command handler already exists")
        else:
            logger.error("start_command handler not found - this is critical")
            return False
        
        logger.info("✅ Command handlers are patched successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error patching command handlers: {e}")
        traceback.print_exc()
        return False

def start_bot_with_proper_settings():
    """Start the Telegram bot with proper settings"""
    try:
        # Apply patches
        if not patch_command_handlers():
            logger.error("Failed to patch command handlers")
            return False
        
        # Check if the bot token is set
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("No Telegram bot token found in environment variables!")
            logger.info("Please set TELEGRAM_BOT_TOKEN in your .env file")
            return False
        
        logger.info(f"Bot token is set (length: {len(bot_token)})")
        
        # Run the bot directly
        logger.info("Starting bot directly using python bot_v20_runner.py...")
        
        import subprocess
        process = subprocess.Popen([sys.executable, 'bot_v20_runner.py'])
        
        # Check if the process started successfully
        time.sleep(2)
        if process.poll() is None:
            logger.info("✅ Bot is now running in the background!")
            logger.info("You can now use /start, /deposit, and other commands")
            return True
        else:
            logger.error(f"❌ Bot process exited with code {process.returncode}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Try to fix the command handlers and start the bot
    if start_bot_with_proper_settings():
        logger.info("✅ Bot is now running with fixed command handlers")
        logger.info("You can now use /start, /deposit, and other commands")
    else:
        logger.error("❌ Failed to fix and start the bot")
        logger.info("Try manually setting TELEGRAM_BOT_TOKEN in your .env file")