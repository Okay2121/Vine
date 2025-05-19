import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information and available commands (FAQs)."""
    help_text = (
        "🤔 *Need Help? Here's How THRIVE Works*\n\n"
        "• *Getting Started:* Use the /start command to begin\n"
        "• *Deposit:* Add SOL to start automated trading\n"
        "• *Dashboard:* Check profits and trading performance\n"
        "• *Withdrawal:* Get your profits anytime\n"
        "• *Settings:* Customize your trading preferences\n"
        "• *Referral:* Invite friends and earn 5% of their profits\n\n"
        "🏆 *Our Strategy:*\n"
        "THRIVE analyzes social media sentiment, trading volume, and market momentum to identify promising memecoins. Our intelligent algorithms execute precise trades to maximize your returns.\n\n"
        "📈 *Common Commands:*\n"
        "/start - Set up your account\n"
        "/deposit - Add funds to start trading\n"
        "/dashboard - View trading performance\n"
        "/settings - Manage your account\n"
        "/referral - Share with friends\n"
        "/help - Get assistance\n\n"
        "💬 *Still have questions?* Tap the Customer Support button in your dashboard."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="view_dashboard"),
            InlineKeyboardButton("💰 Deposit", callback_data="deposit")
        ],
        [
            InlineKeyboardButton("📈 Trade History", callback_data="trading_history"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="start")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Handle both direct commands and callback queries
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
