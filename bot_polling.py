#!/usr/bin/env python

import logging
import os
import asyncio
import sys
from telegram import Update
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters, ConversationHandler)
from app import app
from handlers.start import skip_wallet_callback

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7562541416:AAGxe-j7r26pO7ku1m5kunmwes0n0e3p2XQ')

# Define conversation states
(WAITING_FOR_WALLET_ADDRESS,
 WAITING_FOR_CONFIRMATION) = range(2)

async def start_command(update: Update, context) -> int:
    """Send welcome message when the command /start is issued."""
    user = update.effective_user
    
    logger.info(f"User {user.id} ({user.username}) initiated /start command")
    
    welcome_message = (
        f"👋 Welcome to SolanaMemobot, {user.first_name}! I'm your automated Solana memecoin trading assistant. \n\n"
        "We help grow your SOL by buying/selling trending memecoins with safe, automated strategies. "
        "You retain control of your funds at all times.\n\n"
        "Use /deposit to add funds and start trading!\n"
        "Use /help to see all available commands.\n"
    )
    
    # Create a keyboard with basic options
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("How It Works", callback_data="how_it_works")],
        [InlineKeyboardButton("Deposit SOL", callback_data="deposit")],
        [InlineKeyboardButton("Referral Program 💰", callback_data="referral")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    return ConversationHandler.END

async def help_command(update: Update, context) -> None:
    """Show help information and available commands."""
    # Import the handler from handlers/help.py for consistent UI
    from handlers.help import help_command as handler_help
    await handler_help(update, context)

async def deposit_command(update: Update, context) -> None:
    """Handle the deposit command."""
    # Import the handler from handlers/deposit.py for consistent UI
    from handlers.deposit import deposit_command as handler_deposit
    await handler_deposit(update, context)

async def dashboard_command(update: Update, context) -> None:
    """Show the profit dashboard."""
    # Use the handler from handlers/dashboard.py for consistent UI
    from handlers.dashboard import dashboard_command as handler_dashboard
    await handler_dashboard(update, context)
        
async def settings_command(update: Update, context) -> None:
    """Handle the settings command."""
    # Import the handler from handlers/settings.py for consistent UI
    from handlers.settings import settings_command as handler_settings
    await handler_settings(update, context)

async def referral_command(update: Update, context) -> None:
    """Handle the referral command."""
    # Import the handler from handlers/referral.py for consistent UI
    from handlers.referral import referral_command as handler_referral
    await handler_referral(update, context)

async def how_it_works_callback(update: Update, context) -> None:
    """Explain how the bot works."""
    # Use the handler from handlers/start.py for consistent UI
    from handlers.start import how_it_works_callback as handler_how_it_works
    await handler_how_it_works(update, context)

async def skip_engagement_callback(update: Update, context) -> None:
    """Handle user skipping an engagement message."""
    query = update.callback_query
    await query.answer("Message skipped")
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("Main Menu", callback_data="start")],
        [InlineKeyboardButton("Dashboard", callback_data="dashboard")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the user's last activity timestamp to avoid immediate follow-up reminders
    with app.app_context():
        try:
            from models import User
            from datetime import datetime
            from app import db
            
            user_id = update.effective_user.id
            user_record = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if user_record:
                # Update the last activity timestamp
                user_record.last_activity = datetime.utcnow()
                db.session.commit()
                logger.info(f"Updated last_activity for user {user_id} after skipping engagement message")
        except Exception as e:
            logger.error(f"Error updating user record after skip: {e}")
    
    await query.edit_message_text(
        "You can always come back later! I'll be here when you're ready.",
        reply_markup=reply_markup
    )

async def callback_handler(update: Update, context) -> None:
    """Handle callback queries from button presses."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user = update.effective_user
    logger.info(f"User {user.id} pressed button: {callback_data}")
    
    if callback_data == "start":
        # Import from handlers to ensure we're using the updated UI layout
        from handlers.start import show_main_menu
        
        # Get the user from the database
        from app import app, db
        from models import User
        
        with app.app_context():
            db_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                # Create a new user if not found
                db_user = User(
                    telegram_id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                db.session.add(db_user)
                db.session.commit()
            
            # Show the main menu with the improved layout
            await show_main_menu(update, context, db_user)
    elif callback_data == "deposit":
        # Call the deposit command
        context.user_data["callback_query"] = query
        await deposit_command(update, context)
    elif callback_data == "dashboard" or callback_data == "view_dashboard":
        # Call the dashboard command
        context.user_data["callback_query"] = query
        await dashboard_command(update, context)
    elif callback_data == "settings":
        # Call the settings command
        context.user_data["callback_query"] = query
        await settings_command(update, context)
    elif callback_data == "referral":
        # Call the referral command
        context.user_data["callback_query"] = query
        await referral_command(update, context)
    elif callback_data == "help":
        # Call the help command
        context.user_data["callback_query"] = query
        await help_command(update, context)
    elif callback_data == "copy_address":
        # Import the handler from handlers/deposit.py for consistent UI
        from handlers.deposit import copy_address_callback
        await copy_address_callback(update, context)
    elif callback_data == "skip_engagement":
        # Handle skipping engagement message
        await skip_engagement_callback(update, context)
    elif callback_data == "skip_wallet":
        # Import the handler from handlers/start.py for consistent UI
        from handlers.start import skip_wallet_callback as handler_skip_wallet
        await handler_skip_wallet(update, context)
    elif callback_data == "deposit_confirmed":
        # Import the handler from handlers/deposit.py for consistent UI
        from handlers.deposit import deposit_confirmed_callback
        await deposit_confirmed_callback(update, context)
    else:
        # For any other callback, just acknowledge
        await query.answer(f"Button {callback_data} pressed")

async def main():
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot...")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    try:
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("deposit", deposit_command))
        application.add_handler(CommandHandler("dashboard", dashboard_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CommandHandler("referral", referral_command))
        
        # Add specific callback query handlers
        application.add_handler(CallbackQueryHandler(how_it_works_callback, pattern="^how_it_works$"))
        application.add_handler(CallbackQueryHandler(dashboard_command, pattern="^view_dashboard$"))
        application.add_handler(CallbackQueryHandler(dashboard_command, pattern="^dashboard$"))
        
        # Add general callback handler for remaining patterns
        application.add_handler(CallbackQueryHandler(callback_handler))
        
        # Add message handler for all user text messages - this will auto-delete user messages after 30 seconds
        from utils.message_handlers import handle_user_message_cleanup
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message_cleanup))
        
        logger.info("Starting bot polling...")
        # Start the bot with polling
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Keep the bot running until interrupted
        logger.info("Bot is now polling for updates...")
        # Run until interrupted
        await application.updater.idle()
        
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    """Run the Telegram bot"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Bot has stopped.")
