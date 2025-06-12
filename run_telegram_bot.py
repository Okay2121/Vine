#!/usr/bin/env python3
"""
DEPRECATED: This file has been disabled to prevent duplicate bot instances.
Use the environment-aware startup system instead:
- Replit: Auto-start enabled automatically
- AWS/Production: Use 'python start_bot_manual.py'
"""
import sys
print("⚠️ This script is deprecated. Use environment-aware startup system.")
sys.exit(1)

# Original content disabled below:
# #!/usr/bin/env python
# """
Dedicated launcher for the Telegram bot
This addresses issues where the bot may not respond to commands correctly
# """
import os
import sys
import logging
import time
import threading

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_runner.log")
    ]
)
logger = logging.getLogger(__name__)

def ensure_bot_responds():
    # """Make sure the bot stays responsive to commands# """
    try:
        # Fix any circular import issues
        import importlib
        
        # Clear any cached modules that might be causing issues
        for module in list(sys.modules.keys()):
            if module.startswith('utils.') or module == 'balance_manager':
                if module in sys.modules:
                    del sys.modules[module]
        
        # Import and run the bot with error handling
        import bot_v20_runner
        
        # Show success message
        logger.info("✅ Bot started successfully and ready to respond to commands")
        logger.info("📱 You can now use /start, /admin, and other commands")
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    logger.info("🚀 Starting Telegram bot...")
    
    # If any balance manager module has issues, print information
    try:
        import balance_manager
        logger.info("✅ Balance manager imported successfully")
    except Exception as e:
        logger.error(f"⚠️ Balance manager import error: {e}")
    
    # Start the bot
    if ensure_bot_responds():
        # Keep the script running
        logger.info("✅ Bot is now running and responding to commands")
        
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
    else:
        logger.error("❌ Failed to start bot")