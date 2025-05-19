import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin panel if user is authorized."""
    user = update.effective_user
    logger.info(f"User {user.id} attempted to access admin command")
    
    # Hardcoded admin for testing
    admin_id = "5488280696"
    
    if str(user.id) != admin_id:
        await update.message.reply_text(
            "Sorry, you do not have permission to access the admin panel."
        )
        return
    
    admin_text = (
        "🔑 *Admin Control Panel*\n\n"
        "Welcome to the admin panel! You can manage users, settings, and wallet addresses here."
    )
    
    keyboard = [
        [InlineKeyboardButton("User Management", callback_data="admin_user_management")],
        [InlineKeyboardButton("Wallet Settings", callback_data="admin_wallet_settings")],
        [InlineKeyboardButton("Send Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("View Stats", callback_data="admin_view_stats")],
        [InlineKeyboardButton("Exit Admin Panel", callback_data="admin_exit")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=admin_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
