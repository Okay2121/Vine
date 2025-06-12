#!/usr/bin/env python3
"""
Manual Bot Starter for AWS/Production Environments
=================================================
This script provides a clean way to start the bot manually on AWS or other
production environments where auto-start should be disabled.

Usage:
    python start_bot_manual.py

This script:
1. Sets the environment to manual mode
2. Prevents auto-start conflicts
3. Starts the bot with proper logging
4. Includes health monitoring
"""

import os
import sys
import logging
import time
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def check_required_environment():
    """Check that all required environment variables are set"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables before starting the bot")
        return False
    
    return True

def set_manual_environment():
    """Set environment to manual mode to prevent auto-start conflicts"""
    os.environ['BOT_ENVIRONMENT'] = 'aws'
    logger.info("Environment set to manual mode (AWS)")

def start_bot():
    """Start the bot manually"""
    try:
        # Import and start the bot
        from main import start_bot_thread
        
        logger.info("Starting Telegram bot in manual mode...")
        
        if start_bot_thread():
            logger.info("✅ Bot started successfully")
            return True
        else:
            logger.error("❌ Failed to start bot")
            return False
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def monitor_bot():
    """Monitor bot health and keep the process running"""
    logger.info("Bot monitoring started - Press Ctrl+C to stop")
    
    try:
        while True:
            # Check if bot process is still running
            time.sleep(30)  # Check every 30 seconds
            
            # You can add health checks here if needed
            # For now, just keep the main process alive
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Monitor error: {e}")

def main():
    """Main function to start the bot manually"""
    logger.info("🚀 Manual Bot Starter for AWS/Production")
    logger.info("=" * 50)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check environment variables
    if not check_required_environment():
        sys.exit(1)
    
    # Set manual environment mode
    set_manual_environment()
    
    # Start the bot
    if start_bot():
        logger.info("Bot is now running in manual mode")
        monitor_bot()
    else:
        logger.error("Failed to start bot")
        sys.exit(1)

if __name__ == "__main__":
    main()