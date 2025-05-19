#!/usr/bin/env python

import logging
import os
import threading
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                      MessageHandler, filters, ConversationHandler, CallbackContext)
from handlers.start import (start_command, how_it_works_callback, 
                          process_wallet_address, WAITING_FOR_WALLET_ADDRESS, 
                          WAITING_FOR_CONFIRMATION)
from handlers.deposit import (deposit_command, copy_address_callback, 
                           deposit_confirmed_callback)
from handlers.dashboard import (dashboard_command, withdraw_profit_callback, 
                             reinvest_callback)
from handlers.settings import settings_command
from handlers.help import help_command
from handlers.referral import (referral_command, share_referral_callback,
                            referral_stats_callback)
from handlers.admin import admin_command, admin_user_management_callback, admin_wallet_settings_callback, admin_broadcast_callback

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def run_telegram_bot():
    """Start the Telegram bot using polling."""
    logger.info("Starting Telegram bot...")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    try:
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Onboarding conversation handler for getting wallet address
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
        
        # Add callback query handlers
        application.add_handler(CallbackQueryHandler(how_it_works_callback, pattern="^how_it_works$"))
        application.add_handler(CallbackQueryHandler(copy_address_callback, pattern="^copy_address$"))
        application.add_handler(CallbackQueryHandler(deposit_confirmed_callback, pattern="^deposit_confirmed$"))
        application.add_handler(CallbackQueryHandler(withdraw_profit_callback, pattern="^withdraw_profit$"))
        application.add_handler(CallbackQueryHandler(reinvest_callback, pattern="^reinvest$"))
        application.add_handler(CallbackQueryHandler(share_referral_callback, pattern="^share_referral$"))
        application.add_handler(CallbackQueryHandler(referral_stats_callback, pattern="^referral_stats$"))
        
        # Admin callback handlers
        application.add_handler(CallbackQueryHandler(admin_user_management_callback, pattern="^admin_user_management$"))
        application.add_handler(CallbackQueryHandler(admin_wallet_settings_callback, pattern="^admin_wallet_settings$"))
        application.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$"))
        
        logger.info("Starting bot polling...")
        # Start the bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep the bot running
        await application.updater.stop()
        await application.stop()
        
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise e

import asyncio

if __name__ == "__main__":
    # Run the async function in the event loop
    try:
        logger.info("Starting bot in main thread")
        asyncio.run(run_telegram_bot())
    except KeyboardInterrupt:
        logger.info("Bot process interrupted.")
    except Exception as e:
        logger.error(f"Error in main thread: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("Bot has stopped.")
