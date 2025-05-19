"""
Welcome message handler for Telegram bot.
This module provides the functionality to display a welcome message before
the user presses the /start command.
"""

from flask import current_app as app
from telegram import Update
from telegram.ext import ContextTypes

async def display_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display the welcome message when a user first interacts with the bot,
    even before they press /start.
    """
    # Get the user information
    user = update.message.from_user
    
    # Crafted welcome message with clean formatting
    welcome_text = (
        "Welcome to THRIVE BOT. The auto-trading system built *for* real memecoin winners.\n\n"
        "- Trades live tokens on Solana in real-time\n"
        "- Tracks profits with full transparency\n"
        "- Withdraw anytime with proof in hand\n\n"
        "No subscriptions. No empty promises. Just results.\n\n"
        "Tap \"Start\" to begin your climb."
    )
    
    # Send the welcome message with Markdown formatting
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text,
        parse_mode="Markdown"
    )