#!/usr/bin/env python
"""
Dedicated Bot Runner - Ensures the Telegram bot runs properly
This script properly initializes and runs the bot in a dedicated process
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

def run_bot():
    """Run the bot directly"""
    try:
        logger.info("Starting bot directly...")
        
        # Import the bot runner module directly
        import importlib.util
        
        # Force reload any previously imported modules
        if 'bot_v20_runner' in sys.modules:
            del sys.modules['bot_v20_runner']
        
        # Import the bot_v20_runner module
        spec = importlib.util.spec_from_file_location("bot_v20_runner", "bot_v20_runner.py")
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)
        
        # Run the bot's main function if it exists
        if hasattr(bot_module, 'main'):
            logger.info("Starting bot via main() function...")
            bot_module.main()
        else:
            logger.info("Bot module loaded but no main() function found.")
        
        logger.info("Bot is now running!")
        
        # Keep the script running
        while True:
            logger.info("Bot is active...")
            time.sleep(300)  # Log every 5 minutes to show it's still alive
            
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check if bot token is available
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("No Telegram bot token found in environment variables!")
        logger.info("Please make sure TELEGRAM_BOT_TOKEN is set in your .env file")
        sys.exit(1)
    
    logger.info(f"Bot token found, length: {len(bot_token)}")
    run_bot()