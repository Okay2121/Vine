#!/usr/bin/env python
"""
Script to start the Telegram bot separately from the web application
"""
import os
import sys
import logging
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logger.info("Starting Telegram bot...")

try:
    # Import and run the bot
    import bot_v20_runner
    logger.info("Bot initialization successful")
    
    # Keep the script running
    while True:
        time.sleep(10)
except Exception as e:
    logger.error(f"Error starting the bot: {e}")
    import traceback
    logger.error(traceback.format_exc())