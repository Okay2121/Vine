#!/usr/bin/env python
"""
Solana Memecoin Trading Bot - Main Entry Point
This file initializes and runs the Telegram bot with all handlers properly set up
"""

import logging
import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)

# Import handlers based on your existing structure
# Adjust these imports according to your actual project structure
from handlers.start import (
    start_command, how_it_works_callback, 
    process_wallet_address, WAITING_FOR_WALLET_ADDRESS, 
    WAITING_FOR_CONFIRMATION
)
from handlers.deposit import (
    deposit_command, copy_address_callback, 
    deposit_confirmed_callback
)
from handlers.dashboard import (
    dashboard_command, withdraw_profit_callback, 
    reinvest_callback
)
from handlers.settings import settings_command
from handlers.help import help_command
from handlers.referral import (
    referral_command, share_referral_callback,
    referral_stats_callback
)
from handlers.admin import (
    admin_command, admin_user_management_callback,
    admin_wallet_settings_callback, admin_broadcast_callback,
    admin_direct_message_callback, admin_view_stats_callback,
    admin_adjust_balance_callback, admin_bot_settings_callback,
    admin_exit_callback, admin_back_callback
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Get bot token from environment
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID')

async def main():
    """Initialize and start the Telegram bot."""
    logger.info("Starting Solana Memecoin Trading Bot...")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    try:
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Onboarding conversation handler
        start_conversation_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start_command)],
            states={
                WAITING_FOR_WALLET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet_address)],
                WAITING_FOR_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet_address)]
            },
            fallbacks=[CommandHandler("start", start_command)]
        )
        application.add_handler(start_conversation_handler)
        
        # Add command handlers
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("deposit", deposit_command))
        application.add_handler(CommandHandler("dashboard", dashboard_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CommandHandler("referral", referral_command))
        application.add_handler(CommandHandler("admin", admin_command))
        
        # Add specific callback query handlers
        application.add_handler(CallbackQueryHandler(how_it_works_callback, pattern="^how_it_works$"))
        application.add_handler(CallbackQueryHandler(dashboard_command, pattern="^view_dashboard$"))
        application.add_handler(CallbackQueryHandler(dashboard_command, pattern="^dashboard$"))
        application.add_handler(CallbackQueryHandler(copy_address_callback, pattern="^copy_address$"))
        application.add_handler(CallbackQueryHandler(deposit_confirmed_callback, pattern="^deposit_confirmed$"))
        application.add_handler(CallbackQueryHandler(withdraw_profit_callback, pattern="^withdraw_profit$"))
        application.add_handler(CallbackQueryHandler(reinvest_callback, pattern="^reinvest$"))
        application.add_handler(CallbackQueryHandler(share_referral_callback, pattern="^share_referral$"))
        application.add_handler(CallbackQueryHandler(referral_stats_callback, pattern="^referral_stats$"))
        
        # Admin callbacks
        application.add_handler(CallbackQueryHandler(admin_user_management_callback, pattern="^admin_user_management$"))
        application.add_handler(CallbackQueryHandler(admin_wallet_settings_callback, pattern="^admin_wallet_settings$"))
        application.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$"))
        application.add_handler(CallbackQueryHandler(admin_direct_message_callback, pattern="^admin_direct_message$"))
        application.add_handler(CallbackQueryHandler(admin_view_stats_callback, pattern="^admin_view_stats$"))
        application.add_handler(CallbackQueryHandler(admin_adjust_balance_callback, pattern="^admin_adjust_balance$"))
        application.add_handler(CallbackQueryHandler(admin_bot_settings_callback, pattern="^admin_bot_settings$"))
        application.add_handler(CallbackQueryHandler(admin_exit_callback, pattern="^admin_exit$"))
        application.add_handler(CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"))
        
        # Start the bot
        logger.info("Starting Telegram bot polling...")
        
        # Running with polling
        await application.initialize()
        await application.start_polling()
        
        logger.info("Bot started successfully")
        
        # Keep the bot running until interrupted
        try:
            # Keep the bot running until interrupted
            logger.info("Bot is running. Press Ctrl+C to stop")
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot stopping...")
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        logger.info("Bot has stopped")