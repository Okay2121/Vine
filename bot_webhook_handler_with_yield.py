#!/usr/bin/env python
"""
Enhanced Telegram Bot with Yield Tracker & Trade History Module
This version integrates the yield module with the main bot functionality.
"""

import logging
import os
import threading
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                      MessageHandler, filters, ConversationHandler, ContextTypes)
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

# Import the yield module
from yield_module import setup_yield_module

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
        application.add_handler(CallbackQueryHandler(admin_user_management_callback, pattern="^admin_users$"))
        application.add_handler(CallbackQueryHandler(admin_wallet_settings_callback, pattern="^admin_wallets$"))
        application.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$"))
        
        # **********************************************
        # YIELD TRACKER & TRADE HISTORY MODULE INTEGRATION
        # **********************************************
        #
        # Initialize the yield tracking module
        # This adds:
        # - /simulate command: Simulate a random trade with realistic yield
        # - /history command: Show paginated trade history
        # - /balance command: Check simulated SOL balance
        #
        setup_yield_module(application)
        logger.info("Yield tracker & trade history module initialized")
        # **********************************************
        # END YIELD MODULE INTEGRATION
        # **********************************************
        
        await application.initialize()
        await application.start_polling()
        await application.updater.start_polling()
        
        logger.info("Bot started and is polling for updates...")
        
        # Run until the application is stopped
        await application.updater.idle()
        
    except Exception as e:
        logger.error(f"Error starting the Telegram bot: {e}")
        raise

# Flask routes
@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handle webhook updates from Telegram."""
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), None)
        # Process incoming update
        # This would be used in webhook mode, but we're using polling for reliability
        return jsonify({'status': 'ok'})

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Set the Telegram bot webhook."""
    # We're using polling for reliability, so this route is just for information
    return jsonify({'status': 'Using polling mode for better reliability'})

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})

@app.route('/', methods=['GET'])
def index():
    """Main index route."""
    return "Telegram Bot Server is running. Bot is using polling mode for updates."

# Start the Telegram bot in a separate thread
bot_thread = None
def start_bot_thread():
    """Start the bot in a separate thread."""
    global bot_thread
    import asyncio
    
    def run_async_bot():
        asyncio.run(run_telegram_bot())
    
    bot_thread = threading.Thread(target=run_async_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    return True

# Start the bot when the Flask app starts
@app.before_first_request
def start_bot_on_first_request():
    """Start the bot on the first request to the Flask app."""
    start_bot_thread()

# Manual control routes for the bot
@app.route('/start_bot', methods=['GET'])
def start_bot_route():
    """Start the Telegram bot manually."""
    if start_bot_thread():
        return jsonify({'status': 'Bot started successfully'})
    else:
        return jsonify({'status': 'Failed to start bot'}), 500

if __name__ == "__main__":
    # Start the Flask application
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))