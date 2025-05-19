#!/usr/bin/env python
import logging
import os
import sys
from dotenv import load_dotenv

# Using try/except to handle different versions of python-telegram-bot
try:
    # Try python-telegram-bot v13.x imports
    from telegram import Update, Bot
    from telegram.ext import (
        Updater, 
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        Filters,
        ConversationHandler,
        CallbackContext
    )
    print("Using python-telegram-bot v13.x")
except ImportError:
    try:
        # Try python-telegram-bot v20.x imports
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
        print("Using python-telegram-bot v20.x")
    except ImportError:
        print("ERROR: Could not import python-telegram-bot. Make sure it's installed.")
        sys.exit(1)

# Import handlers
from handlers.start import (
    start_command, 
    how_it_works_callback, 
    process_wallet_address,
    skip_wallet_callback,
    WAITING_FOR_WALLET_ADDRESS, 
    WAITING_FOR_CONFIRMATION
)
from handlers.deposit import (
    deposit_command, 
    copy_address_callback,
    deposit_confirmed_callback
)
from handlers.dashboard import (
    dashboard_command, 
    withdraw_profit_callback, 
    withdraw_all_callback,
    withdraw_profit_only_callback,
    reinvest_callback,
    trading_history_callback,
    transaction_history_callback,
    my_wallet_callback,
    notifications_callback,
    support_callback,
    view_positions_callback,
    view_profit_chart_callback,
    view_allocation_callback,
    more_options_callback
)
from handlers.settings import settings_command
from handlers.help import help_command
from handlers.referral import (
    referral_command,
    share_referral_callback,
    referral_stats_callback
)
from handlers.admin import (
    admin_command,
    admin_user_management_callback,
    admin_wallet_settings_callback,
    admin_broadcast_callback,
    admin_direct_message_callback,
    admin_view_stats_callback,
    admin_adjust_balance_callback,
    admin_bot_settings_callback,
    admin_exit_callback,
    admin_back_callback,
    admin_change_wallet_callback,
    admin_view_wallet_qr_callback,
    admin_send_broadcast_callback,
    admin_export_csv_callback,
    admin_send_message_callback,
    admin_adjust_user_balance_callback,
    admin_reset_user_callback,
    admin_remove_user_callback,
    admin_confirm_remove_user_callback,
    admin_confirm_adjustment_callback,
    admin_send_direct_message_callback,
    admin_process_withdrawal_callback,
    admin_confirm_withdrawal_callback,
    admin_process_user_id,
    admin_process_broadcast,
    admin_direct_message_user_id,
    admin_process_user_message,
    admin_adjust_balance_user_id,
    admin_process_balance_adjustment,
    admin_process_balance_reason,
    admin_process_new_wallet,
    WAITING_FOR_USER_ID,
    WAITING_FOR_USER_MESSAGE,
    WAITING_FOR_BROADCAST_MESSAGE,
    WAITING_FOR_BALANCE_ADJUSTMENT,
    WAITING_FOR_BALANCE_REASON,
    WAITING_FOR_NEW_WALLET
)
# Import ROI admin handlers
from handlers.roi_admin import (
    admin_start_roi_cycle_callback,
    admin_pause_roi_cycle_callback,
    admin_resume_roi_cycle_callback,
    admin_adjust_roi_percentage_callback,
    admin_process_roi_percentage,
    WAITING_FOR_ROI_PERCENTAGE
)
from utils.scheduler import setup_schedulers
from config import BOT_TOKEN, ADMIN_USER_ID

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_polling():
    """Start the Telegram bot using polling."""
    logger.info("Starting Telegram bot with polling...")
    
    # Get bot token from environment variable
    token = os.environ.get('TELEGRAM_BOT_TOKEN', BOT_TOKEN)
    admin_id = os.environ.get('ADMIN_USER_ID', ADMIN_USER_ID)
    
    if not token:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    try:
        # For python-telegram-bot v20+
        from telegram.ext import Application
        
        # Create the Application
        app = Application.builder().token(token).build()
        
        # Store reference to app
        run_polling.app = app
        
        logger.info("Using python-telegram-bot v20+")
        return run_polling_v20(app)
    except (ImportError, AttributeError):
        # Fall back to v13 syntax
        try:
            # Create the Updater and Dispatcher
            updater = Updater(token=token, use_context=True)
            dp = updater.dispatcher
            logger.info("Using python-telegram-bot v13.x")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return False
            
# Function for running the bot with v20+ API
def run_polling_v20(app):
    """Run the bot with python-telegram-bot v20+"""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("deposit", deposit_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("profit", dashboard_command))  # Alias for dashboard
    app.add_handler(CommandHandler("status", dashboard_command))  # Alias for dashboard
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("refer", referral_command))  # Alias for referral
    app.add_handler(CommandHandler("admin", admin_command))
    
    # Add callback query handlers
    app.add_handler(CallbackQueryHandler(how_it_works_callback, pattern=r"^how_it_works$"))
    app.add_handler(CallbackQueryHandler(deposit_command, pattern=r"^deposit$"))
    # Add other handlers as needed...
    
    # Add message handler for all user text messages - this will auto-delete user messages after 30 seconds
    from utils.message_handlers import handle_user_message_cleanup
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message_cleanup))
    
    # Start the Bot
    app.run_polling()

# Python-telegram-bot v13.x specific code
def setup_v13_handlers(updater, admin_id):
    """Set up handlers for python-telegram-bot v13.x"""
    dp = updater.dispatcher
    
    # Onboarding conversation handler for getting wallet address
    start_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WAITING_FOR_WALLET_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, process_wallet_address)],
            WAITING_FOR_CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, process_wallet_address)]
        },
        fallbacks=[CommandHandler("start", start_command)]
    )
    dp.add_handler(start_conversation_handler)
    
    # Add command handlers
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("deposit", deposit_command))
    dp.add_handler(CommandHandler("dashboard", dashboard_command))
    dp.add_handler(CommandHandler("profit", dashboard_command))  # Alias for dashboard
    dp.add_handler(CommandHandler("status", dashboard_command))  # Alias for dashboard
    dp.add_handler(CommandHandler("settings", settings_command))
    dp.add_handler(CommandHandler("referral", referral_command))
    dp.add_handler(CommandHandler("refer", referral_command))  # Alias for referral
    dp.add_handler(CommandHandler("admin", admin_command))
    
    # Add callback query handlers
    dp.add_handler(CallbackQueryHandler(how_it_works_callback, pattern='^how_it_works$'))
    dp.add_handler(CallbackQueryHandler(deposit_command, pattern='^deposit$'))
    dp.add_handler(CallbackQueryHandler(copy_address_callback, pattern='^copy_address$'))
    dp.add_handler(CallbackQueryHandler(deposit_confirmed_callback, pattern='^deposit_confirmed$'))
    dp.add_handler(CallbackQueryHandler(skip_wallet_callback, pattern='^skip_wallet$'))
    dp.add_handler(CallbackQueryHandler(dashboard_command, pattern='^view_dashboard$'))
    dp.add_handler(CallbackQueryHandler(withdraw_profit_callback, pattern='^withdraw_profit$'))
    dp.add_handler(CallbackQueryHandler(withdraw_all_callback, pattern='^withdraw_all$'))
    dp.add_handler(CallbackQueryHandler(withdraw_profit_only_callback, pattern='^withdraw_profit_only$'))
    dp.add_handler(CallbackQueryHandler(reinvest_callback, pattern='^reinvest$'))
    dp.add_handler(CallbackQueryHandler(trading_history_callback, pattern='^trading_history$'))
    dp.add_handler(CallbackQueryHandler(transaction_history_callback, pattern='^transaction_history$'))
    dp.add_handler(CallbackQueryHandler(my_wallet_callback, pattern='^my_wallet$'))
    dp.add_handler(CallbackQueryHandler(notifications_callback, pattern='^notifications$'))
    dp.add_handler(CallbackQueryHandler(settings_command, pattern='^settings$'))
    dp.add_handler(CallbackQueryHandler(help_command, pattern='^help$'))
    dp.add_handler(CallbackQueryHandler(help_command, pattern='^faqs$'))  # Added handler for FAQ button
    dp.add_handler(CallbackQueryHandler(support_callback, pattern='^support$'))
    dp.add_handler(CallbackQueryHandler(help_command, pattern='^live_chat$'))  # Temporary handler for live chat
    dp.add_handler(CallbackQueryHandler(help_command, pattern='^submit_ticket$'))  # Temporary handler for submit ticket
    dp.add_handler(CallbackQueryHandler(help_command, pattern='^contact_info$'))  # Temporary handler for contact info
    dp.add_handler(CallbackQueryHandler(referral_command, pattern='^referral$'))
    dp.add_handler(CallbackQueryHandler(share_referral_callback, pattern='^share_referral$'))
    dp.add_handler(CallbackQueryHandler(referral_stats_callback, pattern='^referral_stats$'))
    dp.add_handler(CallbackQueryHandler(more_options_callback, pattern='^more_options$'))
        
        # Performance dashboard callback query handlers
        dp.add_handler(CallbackQueryHandler(view_positions_callback, pattern='^view_positions$'))
        dp.add_handler(CallbackQueryHandler(view_profit_chart_callback, pattern='^view_profit_chart$'))
        dp.add_handler(CallbackQueryHandler(view_allocation_callback, pattern='^view_allocation$'))
        
        # Admin panel callback query handlers
        dp.add_handler(CallbackQueryHandler(admin_user_management_callback, pattern='^admin_user_management$'))
        dp.add_handler(CallbackQueryHandler(admin_wallet_settings_callback, pattern='^admin_wallet_settings$'))
        dp.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern='^admin_broadcast$'))
        dp.add_handler(CallbackQueryHandler(admin_direct_message_callback, pattern='^admin_direct_message$'))
        dp.add_handler(CallbackQueryHandler(admin_view_stats_callback, pattern='^admin_view_stats$'))
        dp.add_handler(CallbackQueryHandler(admin_adjust_balance_callback, pattern='^admin_adjust_balance$'))
        dp.add_handler(CallbackQueryHandler(admin_bot_settings_callback, pattern='^admin_bot_settings$'))
        dp.add_handler(CallbackQueryHandler(admin_exit_callback, pattern='^admin_exit$'))
        dp.add_handler(CallbackQueryHandler(admin_back_callback, pattern='^admin_back$'))
        dp.add_handler(CallbackQueryHandler(admin_change_wallet_callback, pattern='^admin_change_wallet$'))
        dp.add_handler(CallbackQueryHandler(admin_view_wallet_qr_callback, pattern='^admin_view_wallet_qr$'))
        dp.add_handler(CallbackQueryHandler(admin_send_broadcast_callback, pattern='^admin_send_broadcast$'))
        dp.add_handler(CallbackQueryHandler(admin_export_csv_callback, pattern='^admin_export_csv$'))
        dp.add_handler(CallbackQueryHandler(admin_send_message_callback, pattern='^admin_send_message$'))
        dp.add_handler(CallbackQueryHandler(admin_adjust_user_balance_callback, pattern='^admin_adjust_user_balance$'))
        dp.add_handler(CallbackQueryHandler(admin_reset_user_callback, pattern='^admin_reset_user$'))
        dp.add_handler(CallbackQueryHandler(admin_remove_user_callback, pattern='^admin_remove_user$'))
        dp.add_handler(CallbackQueryHandler(admin_confirm_remove_user_callback, pattern='^admin_confirm_remove_user$'))
        dp.add_handler(CallbackQueryHandler(admin_confirm_adjustment_callback, pattern='^admin_confirm_adjustment$'))
        dp.add_handler(CallbackQueryHandler(admin_send_direct_message_callback, pattern='^admin_send_direct_message$'))
        dp.add_handler(CallbackQueryHandler(admin_process_withdrawal_callback, pattern='^admin_process_withdrawal$'))
        dp.add_handler(CallbackQueryHandler(admin_confirm_withdrawal_callback, pattern='^admin_confirm_withdrawal$'))
        
        # ROI Admin callback handlers
        dp.add_handler(CallbackQueryHandler(admin_start_roi_cycle_callback, pattern='^admin_start_roi_cycle$'))
        dp.add_handler(CallbackQueryHandler(admin_pause_roi_cycle_callback, pattern='^admin_pause_roi_cycle$'))
        dp.add_handler(CallbackQueryHandler(admin_resume_roi_cycle_callback, pattern='^admin_resume_roi_cycle$'))
        dp.add_handler(CallbackQueryHandler(admin_adjust_roi_percentage_callback, pattern='^admin_adjust_roi_percentage$'))
        
        # Admin panel conversation handlers
        user_management_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_user_management_callback, pattern='^admin_user_management$')],
            states={
                WAITING_FOR_USER_ID: [MessageHandler(Filters.text & ~Filters.command, admin_process_user_id)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        dp.add_handler(user_management_conv_handler)
        
        direct_message_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(admin_direct_message_callback, pattern='^admin_direct_message$'),
                CallbackQueryHandler(admin_send_message_callback, pattern='^admin_send_message$')
            ],
            states={
                WAITING_FOR_USER_ID: [MessageHandler(Filters.text & ~Filters.command, admin_direct_message_user_id)],
                WAITING_FOR_USER_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, admin_process_user_message)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        dp.add_handler(direct_message_conv_handler)
        
        broadcast_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_broadcast_callback, pattern='^admin_broadcast$')],
            states={
                WAITING_FOR_BROADCAST_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, admin_process_broadcast)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        dp.add_handler(broadcast_conv_handler)
        
        adjust_balance_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(admin_adjust_balance_callback, pattern='^admin_adjust_balance$'),
                CallbackQueryHandler(admin_adjust_user_balance_callback, pattern='^admin_adjust_user_balance$')
            ],
            states={
                WAITING_FOR_USER_ID: [MessageHandler(Filters.text & ~Filters.command, admin_adjust_balance_user_id)],
                WAITING_FOR_BALANCE_ADJUSTMENT: [MessageHandler(Filters.text & ~Filters.command, admin_process_balance_adjustment)],
                WAITING_FOR_BALANCE_REASON: [MessageHandler(Filters.text & ~Filters.command, admin_process_balance_reason)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        dp.add_handler(adjust_balance_conv_handler)
        
        change_wallet_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_change_wallet_callback, pattern='^admin_change_wallet$')],
            states={
                WAITING_FOR_NEW_WALLET: [MessageHandler(Filters.text & ~Filters.command, admin_process_new_wallet)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        dp.add_handler(change_wallet_conv_handler)
        
        # ROI percentage adjustment conversation handler
        roi_percentage_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_adjust_roi_percentage_callback, pattern='^admin_adjust_roi_percentage$')],
            states={
                WAITING_FOR_ROI_PERCENTAGE: [MessageHandler(Filters.text & ~Filters.command, admin_process_roi_percentage)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        dp.add_handler(roi_percentage_conv_handler)
        
        # Set up scheduled jobs
        setup_schedulers(dp)
        
        # Add message handler for all user text messages - this will auto-delete user messages after 30 seconds
        from utils.message_handlers import handle_user_message_cleanup
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_user_message_cleanup))
        
        # Log the admin user ID
        logger.info(f"Admin user ID set to: {admin_id}")
        
        # Start the bot with polling
        logger.info("Starting bot polling...")
        updater.start_polling()
        
        # Keep the bot running until Ctrl+C is pressed
        logger.info("Bot is now polling for updates...")
        updater.idle()
        
    except Exception as e:
        logger.error(f"Error starting the Telegram bot: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """Run the Telegram bot"""
    try:
        run_polling()
    except KeyboardInterrupt:
        print("Bot stopped manually")
    finally:
        logger.info("Bot has stopped.")
        
if __name__ == "__main__":
    main()