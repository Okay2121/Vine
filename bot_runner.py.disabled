#!/usr/bin/env python
"""
Bot Runner - Direct execution to get the bot responding
"""
import os
import sys
import logging

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import and start the bot
try:
    from bot_v20_runner import bot, run_polling
    
    logger.info("Starting bot polling...")
    run_polling()
    
except Exception as e:
    logger.error(f"Error starting bot: {e}")
    import traceback
    traceback.print_exc()