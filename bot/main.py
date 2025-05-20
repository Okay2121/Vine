#!/usr/bin/env python
"""
Solana Memecoin Trading Bot - Main Entrypoint
This file imports and registers all handlers while providing error recovery
"""

import logging
import os
import sys
from dotenv import load_dotenv
from telegram.ext import Application
from telegram.ext import (
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    filters, 
    ConversationHandler
)

# Import core utilities
from utils.config import BOT_TOKEN, ADMIN_USER_ID
from utils.logger import setup_logger
from utils.scheduler import setup_schedulers

# Import all handlers
from handlers.start import register_start_handlers
from handlers.dashboard import register_dashboard_handlers
from handlers.balance import register_balance_handlers
from handlers.trading import register_trading_handlers
from handlers.referrals import register_referral_handlers
from handlers.admin import register_admin_handlers
from handlers.fallback import register_fallback_handlers
from handlers.settings import register_settings_handlers
from handlers.help import register_help_handlers

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger()

def create_application():
    """Create and configure the application with all handlers"""
    logger.info("Initializing bot application...")
    
    try:
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Register all handlers with error handling
        handlers = [
            register_start_handlers,
            register_dashboard_handlers,
            register_balance_handlers,
            register_trading_handlers, 
            register_referral_handlers,
            register_admin_handlers,
            register_settings_handlers,
            register_help_handlers,
            register_fallback_handlers  # Must be registered last
        ]
        
        for register_handler in handlers:
            try:
                logger.info(f"Registering handler: {register_handler.__name__}")
                register_handler(application)
            except Exception as e:
                logger.error(f"Error registering handler {register_handler.__name__}: {e}")
                logger.exception(e)
        
        # Setup scheduled tasks (e.g., ROI updates, notifications)
        setup_schedulers(application)
        
        return application
    except Exception as e:
        logger.critical(f"Failed to initialize application: {e}")
        logger.exception(e)
        raise

def main():
    """Run the bot application"""
    logger.info("Starting Solana Memecoin Trading Bot...")
    
    try:
        # Create application with all handlers
        application = create_application()
        
        # Run the bot
        application.run_polling()
    except Exception as e:
        logger.critical(f"Critical error in main process: {e}")
        logger.exception(e)
        return 1
    finally:
        logger.info("Bot has stopped.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())