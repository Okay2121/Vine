"""
Help handler module
Provides assistance and support to users
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    user = update.effective_user
    
    message = (
        "🆘 *HELP & SUPPORT*\n\n"
        "Here's how to use the Solana Memecoin Trading Bot:\n\n"
        "*Commands:*\n"
        "• /start - Start or restart the bot\n"
        "• /dashboard - View your account dashboard\n"
        "• /deposit - Make a deposit\n"
        "• /withdraw - Withdraw funds\n"
        "• /trading - View and control trading\n"
        "• /referral - Access the referral program\n"
        "• /settings - Configure your preferences\n"
        "• /help - Get help and support\n\n"
        "Choose an option below for more detailed help:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ How Trading Works", callback_data="help_trading")],
        [InlineKeyboardButton("💰 Deposits & Withdrawals", callback_data="help_deposits")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="help_settings")],
        [InlineKeyboardButton("👨‍💼 Contact Support", callback_data="help_support")]
    ])
    
    # Determine if this is a callback query or direct command
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            message, 
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            message, 
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

async def help_trading_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'How Trading Works' button click"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "📈 *HOW TRADING WORKS*\n\n"
        "Our bot uses advanced algorithms to trade Solana memecoins with exceptional accuracy:\n\n"
        "1. *Deposit SOL* to start trading\n"
        "2. Our system automatically selects promising memecoin opportunities\n"
        "3. Trades are executed with precise timing\n"
        "4. Profits are added to your balance\n"
        "5. You can withdraw anytime or reinvest\n\n"
        "*Trading Details:*\n"
        "• Success rate: 92-95%\n"
        "• Average ROI: 8-12% daily\n"
        "• Risk management: Advanced stop-loss protections\n"
        "• Multiple trades executed automatically\n\n"
        "Check your performance in the Dashboard."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def help_deposits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Deposits & Withdrawals' button click"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "💰 *DEPOSITS & WITHDRAWALS*\n\n"
        "*Making a Deposit:*\n"
        "1. Use the /deposit command\n"
        "2. Send SOL to the provided address\n"
        "3. Wait for confirmation (usually 1-2 minutes)\n"
        "4. Trading starts automatically\n\n"
        "*Minimum deposit:* 0.1 SOL\n"
        "*Recommended:* 1+ SOL for better results\n\n"
        "*Making a Withdrawal:*\n"
        "1. Use the /withdraw command\n"
        "2. Specify the amount to withdraw\n"
        "3. Confirm the transaction\n"
        "4. Funds will be sent to your registered wallet\n\n"
        "*Processing time:* Usually within 30 minutes\n"
        "*Minimum withdrawal:* 0.05 SOL"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def help_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Bot Settings' button click"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "⚙️ *BOT SETTINGS*\n\n"
        "You can customize your trading experience:\n\n"
        "*Available Settings:*\n"
        "• Change your wallet address\n"
        "• Update notification preferences\n"
        "• Adjust risk level\n"
        "• Toggle auto-reinvestment\n"
        "• Set profit targets\n\n"
        "To access settings, use the /settings command.\n\n"
        "You can also pause trading at any time from the /trading menu if you want to take a break."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def help_support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Contact Support' button click"""
    query = update.callback_query
    await query.answer()
    
    # In a real implementation, this would be fetched from configuration
    support_username = "@SolanaTradeSupport"
    
    message = (
        "👨‍💼 *CONTACT SUPPORT*\n\n"
        f"For any questions or issues, please contact our support team at {support_username}.\n\n"
        "*Support Hours:*\n"
        "Monday - Friday: 9:00 AM - 5:00 PM UTC\n"
        "Weekend: Limited availability\n\n"
        "*Common Support Topics:*\n"
        "• Deposit/withdrawal assistance\n"
        "• Account verification\n"
        "• Technical issues\n"
        "• Trading questions\n\n"
        "Our team typically responds within 24 hours."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

def register_help_handlers(application: Application):
    """Register all handlers related to help and support"""
    # Help command handler
    application.add_handler(CommandHandler("help", help_command))
    
    # Help callback handlers
    application.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(help_trading_callback, pattern="^help_trading$"))
    application.add_handler(CallbackQueryHandler(help_deposits_callback, pattern="^help_deposits$"))
    application.add_handler(CallbackQueryHandler(help_settings_callback, pattern="^help_settings$"))
    application.add_handler(CallbackQueryHandler(help_support_callback, pattern="^help_support$"))