import threading
import logging
import os
from app import app
from dotenv import load_dotenv
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ConversationHandler)
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
from handlers.admin import *

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start_bot():
    """Start the Telegram bot in a separate thread."""
    # Get bot token from environment variable
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.warning("No valid Telegram bot token provided. Bot will not start.")
        return
    
    try:
        # Create the Application
        application = Application.builder().token(token).build()
        
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
        application.add_handler(CallbackQueryHandler(admin_direct_message_callback, pattern="^admin_direct_message$"))
        application.add_handler(CallbackQueryHandler(admin_view_stats_callback, pattern="^admin_view_stats$"))
        application.add_handler(CallbackQueryHandler(admin_adjust_balance_callback, pattern="^admin_adjust_balance$"))
        application.add_handler(CallbackQueryHandler(admin_bot_settings_callback, pattern="^admin_bot_settings$"))
        application.add_handler(CallbackQueryHandler(admin_exit_callback, pattern="^admin_exit$"))
        application.add_handler(CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"))
        
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    except Exception as e:
        logger.error(f"Error starting the Telegram bot: {e}")

def run_web_app():
    """Run the Flask web application."""
    try:
        app.run(host="0.0.0.0", port=5000)
        logger.info("Flask application started successfully.")
    except Exception as e:
        logger.error(f"Error starting the Flask app: {e}")

if __name__ == "__main__":
    # Start the Telegram bot in a background thread
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True  # Makes sure the thread exits when main program exits
    bot_thread.start()
    logger.info("Bot thread started")
    
    # Run the Flask app in the main thread
    run_web_app()
