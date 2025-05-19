from yield_module import setup_yield_module
import logging
import os
import sys
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from handlers.start import (start_command, how_it_works_callback, 
    process_wallet_address, WAITING_FOR_WALLET_ADDRESS, WAITING_FOR_CONFIRMATION)
from handlers.deposit import (
    deposit_command, 
    copy_address_callback, 
    deposit_confirmed_callback
)
from handlers.dashboard import (
    dashboard_command, 
    withdraw_profit_callback, 
    reinvest_callback
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
from utils.scheduler import setup_schedulers
from config import BOT_TOKEN, ADMIN_USER_ID

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def start_bot():
    """Start the Telegram bot."""
    logger.info("Starting bot...")
    
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN', BOT_TOKEN)
    admin_id = os.getenv('ADMIN_USER_ID', ADMIN_USER_ID)
    
    # Check if we have a valid bot token
    if not token:
        logger.warning("No valid Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        logger.info("The bot will not start. Application will continue running in web-only mode.")
        return False
    
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
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("deposit", deposit_command))
        application.add_handler(CommandHandler("dashboard", dashboard_command))
        application.add_handler(CommandHandler("profit", dashboard_command))  # Alias for dashboard
        application.add_handler(CommandHandler("status", dashboard_command))  # Alias for dashboard
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CommandHandler("referral", referral_command))
        application.add_handler(CommandHandler("refer", referral_command))  # Alias for referral
        application.add_handler(CommandHandler("admin", admin_command))
        
        # Add callback query handlers
        application.add_handler(CallbackQueryHandler(how_it_works_callback, pattern='^how_it_works$'))
        application.add_handler(CallbackQueryHandler(deposit_command, pattern='^deposit$'))
        application.add_handler(CallbackQueryHandler(copy_address_callback, pattern='^copy_address$'))
        application.add_handler(CallbackQueryHandler(deposit_confirmed_callback, pattern='^deposit_confirmed$'))
        application.add_handler(CallbackQueryHandler(dashboard_command, pattern='^view_dashboard$'))
        application.add_handler(CallbackQueryHandler(withdraw_profit_callback, pattern='^withdraw_profit$'))
        application.add_handler(CallbackQueryHandler(reinvest_callback, pattern='^reinvest$'))
        application.add_handler(CallbackQueryHandler(settings_command, pattern='^settings$'))
        application.add_handler(CallbackQueryHandler(referral_command, pattern='^referral$'))
        application.add_handler(CallbackQueryHandler(share_referral_callback, pattern='^share_referral$'))
        application.add_handler(CallbackQueryHandler(referral_stats_callback, pattern='^referral_stats$'))
        
        # Admin panel callback query handlers
        application.add_handler(CallbackQueryHandler(admin_user_management_callback, pattern='^admin_user_management$'))
        application.add_handler(CallbackQueryHandler(admin_wallet_settings_callback, pattern='^admin_wallet_settings$'))
        application.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern='^admin_broadcast$'))
        application.add_handler(CallbackQueryHandler(admin_direct_message_callback, pattern='^admin_direct_message$'))
        application.add_handler(CallbackQueryHandler(admin_view_stats_callback, pattern='^admin_view_stats$'))
        application.add_handler(CallbackQueryHandler(admin_adjust_balance_callback, pattern='^admin_adjust_balance$'))
        application.add_handler(CallbackQueryHandler(admin_bot_settings_callback, pattern='^admin_bot_settings$'))
        application.add_handler(CallbackQueryHandler(admin_exit_callback, pattern='^admin_exit$'))
        application.add_handler(CallbackQueryHandler(admin_back_callback, pattern='^admin_back$'))
        application.add_handler(CallbackQueryHandler(admin_change_wallet_callback, pattern='^admin_change_wallet$'))
        application.add_handler(CallbackQueryHandler(admin_view_wallet_qr_callback, pattern='^admin_view_wallet_qr$'))
        application.add_handler(CallbackQueryHandler(admin_send_broadcast_callback, pattern='^admin_send_broadcast$'))
        application.add_handler(CallbackQueryHandler(admin_export_csv_callback, pattern='^admin_export_csv$'))
        application.add_handler(CallbackQueryHandler(admin_send_message_callback, pattern='^admin_send_message$'))
        application.add_handler(CallbackQueryHandler(admin_adjust_user_balance_callback, pattern='^admin_adjust_user_balance$'))
        application.add_handler(CallbackQueryHandler(admin_reset_user_callback, pattern='^admin_reset_user$'))
        application.add_handler(CallbackQueryHandler(admin_remove_user_callback, pattern='^admin_remove_user$'))
        application.add_handler(CallbackQueryHandler(admin_confirm_remove_user_callback, pattern='^admin_confirm_remove_user$'))
        application.add_handler(CallbackQueryHandler(admin_confirm_adjustment_callback, pattern='^admin_confirm_adjustment$'))
        application.add_handler(CallbackQueryHandler(admin_send_direct_message_callback, pattern='^admin_send_direct_message$'))
        application.add_handler(CallbackQueryHandler(admin_process_withdrawal_callback, pattern='^admin_process_withdrawal$'))
        application.add_handler(CallbackQueryHandler(admin_confirm_withdrawal_callback, pattern='^admin_confirm_withdrawal$'))
        
        # Admin panel conversation handlers
        user_management_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_user_management_callback, pattern='^admin_user_management$')],
            states={
                WAITING_FOR_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_user_id)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        application.add_handler(user_management_conv_handler)
        
        direct_message_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(admin_direct_message_callback, pattern='^admin_direct_message$'),
                CallbackQueryHandler(admin_send_message_callback, pattern='^admin_send_message$')
            ],
            states={
                WAITING_FOR_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_direct_message_user_id)],
                WAITING_FOR_USER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_user_message)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        application.add_handler(direct_message_conv_handler)
        
        broadcast_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_broadcast_callback, pattern='^admin_broadcast$')],
            states={
                WAITING_FOR_BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_broadcast)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        application.add_handler(broadcast_conv_handler)
        
        adjust_balance_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(admin_adjust_balance_callback, pattern='^admin_adjust_balance$'),
                CallbackQueryHandler(admin_adjust_user_balance_callback, pattern='^admin_adjust_user_balance$')
            ],
            states={
                WAITING_FOR_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_adjust_balance_user_id)],
                WAITING_FOR_BALANCE_ADJUSTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_balance_adjustment)],
                WAITING_FOR_BALANCE_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_balance_reason)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        application.add_handler(adjust_balance_conv_handler)
        
        change_wallet_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_change_wallet_callback, pattern='^admin_change_wallet$')],
            states={
                WAITING_FOR_NEW_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_new_wallet)]
            },
            fallbacks=[CommandHandler('admin', admin_command)]
        )
        application.add_handler(change_wallet_conv_handler)
        
        # Set up scheduled jobs
        setup_schedulers(application)
        
        # Log the admin user ID
        logger.info(f"Admin user ID set to: {admin_id}")
        
        # Start the Bot
        logger.info("Bot started, polling for updates...")
        
# Set up the yield module
setup_yield_module(application)

application.run_polling()
        return True
    except Exception as e:
        logger.error(f"Error starting the Telegram bot: {e}")
        logger.info("Application will continue running in web-only mode.")
        return False


if __name__ == '__main__':
    start_bot()
