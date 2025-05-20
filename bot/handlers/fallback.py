"""
Fallback handler module
Catches all unknown commands and messages to provide helpful responses
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)

logger = logging.getLogger(__name__)

async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands"""
    command = update.message.text
    user = update.effective_user
    
    logger.info(f"User {user.id} sent unknown command: {command}")
    
    message = (
        "Sorry, I don't recognize that command.\n\n"
        "Here are the available commands:\n"
        "/start - Start or restart the bot\n"
        "/dashboard - View your account dashboard\n"
        "/deposit - Make a deposit\n"
        "/withdraw - Withdraw funds\n"
        "/trading - View and control trading\n"
        "/referral - Access the referral program\n"
        "/help - Get help and support"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("📥 Deposit", callback_data="deposit")]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard)

async def general_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle general text messages that are not commands"""
    text = update.message.text
    user = update.effective_user
    
    logger.info(f"User {user.id} sent message: {text[:20]}...")
    
    # If the message looks like a question, provide help
    if '?' in text:
        await update.message.reply_text(
            "If you have a question, please use the /help command to get assistance."
        )
    else:
        # General response for any text message
        message = (
            "I can only respond to specific commands. Please use one of these:\n\n"
            "/dashboard - View your account status\n"
            "/deposit - Make a deposit\n"
            "/help - Get assistance"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 Dashboard", callback_data="dashboard")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        
        await update.message.reply_text(message, reply_markup=keyboard)

def register_fallback_handlers(application: Application):
    """Register all fallback handlers - these should be registered last"""
    # Handle unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler))
    
    # Handle general messages (not commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, general_message_handler))