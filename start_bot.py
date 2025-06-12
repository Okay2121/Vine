#!/usr/bin/env python3
"""
Dedicated Bot Starter - Ensures the Telegram bot runs and responds to commands
"""
import os
import sys
import time
import logging
from threading import Thread

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start_bot():
    """Start the bot and keep it running"""
    try:
        # Set the bot token
        os.environ['BOT_TOKEN'] = '7562541416:AAGxe-j7r26pO7ku1m5kunmwes0n0e3p2XQ'
        
        # Import and start the bot
        import bot_v20_runner
        logger.info("Starting Telegram bot...")
        
        bot = bot_v20_runner.SimpleTelegramBot('7562541416:AAGxe-j7r26pO7ku1m5kunmwes0n0e3p2XQ')
        logger.info("Bot initialized, starting polling...")
        
        # Run the bot using the correct method
        import bot_v20_runner
        bot_v20_runner.run_polling()
        
    except Exception as e:
        logger.error(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
        
        # Wait a bit before restarting
        time.sleep(5)
        logger.info("Restarting bot...")
        start_bot()

if __name__ == "__main__":
    logger.warning("⚠️ This script is deprecated. Use 'python start_bot_manual.py' for manual start or rely on environment-aware auto-start.")
    logger.info("For AWS deployment: python start_bot_manual.py")
    logger.info("For Replit: Auto-start is enabled automatically")
    sys.exit(1)