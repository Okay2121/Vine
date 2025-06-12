#!/usr/bin/env python3
"""
Persistent Bot Runner - Keeps the bot running and responding
"""
import os
import sys
import time
import signal
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set the bot token
os.environ['BOT_TOKEN'] = '7562541416:AAGxe-j7r26pO7ku1m5kunmwes0n0e3p2XQ'

# Import and run the bot
try:
    import bot_v20_runner
    
    def signal_handler(sig, frame):
        logger.info("Bot shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Starting ThriveQuantbot - Persistent Mode")
    
    # Run the bot
    bot_v20_runner.run_polling()
    
except Exception as e:
    logger.error(f"Bot error: {e}")
    import traceback
    traceback.print_exc()