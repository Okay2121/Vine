import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information and available commands."""
    help_text = (
        "🔍 *Available Commands*:\n\n"
        "/start - Start the bot and access main menu\n"
        "/help - Show this help message\n"
        "/deposit - View deposit instructions and wallet address\n"
        "/dashboard - Check your profit dashboard\n"
        "/settings - Adjust your settings and preferences\n"
        "/referral - Access your referral code and earnings"
    )
    
    keyboard = [
        [InlineKeyboardButton("Deposit SOL", callback_data="deposit")],
        [InlineKeyboardButton("Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("Settings", callback_data="settings")],
        [InlineKeyboardButton("Referral Program", callback_data="referral")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the deposit command or callback."""
    user = update.effective_user
    logger.info(f"User {user.id} accessed deposit command")
    
    # A simulated wallet address - in a real app, would be retrieved from the database
    wallet_address = "Sol1Memkpjvfu3Y9Z5Jr9EPChJMJsYzD7YX8SJbmM"
    
    deposit_text = (
        "💰 *Deposit Instructions*:\n\n"
        "To start using the trading bot, deposit SOL to the following address:\n\n"
        f"`{wallet_address}`\n\n"
        "Minimum deposit: 10 SOL\n"
        "After depositing, click the 'I've Made a Deposit' button below."
    )
    
    keyboard = [
        [InlineKeyboardButton("Copy Address", callback_data="copy_address")],
        [InlineKeyboardButton("I've Made a Deposit", callback_data="deposit_confirmed")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=deposit_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=deposit_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the profit dashboard with trading stats."""
    user = update.effective_user
    logger.info(f"User {user.id} accessed dashboard command")
    
    # Simulated data - in a real app, would be retrieved from the database
    balance = 10.0  # SOL
    initial_deposit = 10.0  # SOL
    profit = 0.0  # SOL
    profit_percentage = 0.0  # %
    daily_profit = 0.0  # SOL
    active_trades = 0
    
    # Calculate profit data
    profit_percentage = (profit / initial_deposit * 100) if initial_deposit > 0 else 0
    
    dashboard_text = (
        "📊 *Your Trading Dashboard*:\n\n"
        f"Balance: {balance:.2f} SOL\n"
        f"Initial Deposit: {initial_deposit:.2f} SOL\n"
        f"Total Profit: {profit:.2f} SOL ({profit_percentage:.1f}%)\n"
        f"Profit Today: {daily_profit:.2f} SOL\n\n"
    )
    
    # Add trading status message
    if initial_deposit == 0:
        dashboard_text += "No active trades. Make a deposit to start trading!"
    else:
        dashboard_text += f"Active trades: {active_trades}\n\nThe bot is actively trading for you!"
    
    keyboard = [
        [InlineKeyboardButton("Withdraw Profit", callback_data="withdraw_profit")],
        [InlineKeyboardButton("Reinvest Profit", callback_data="reinvest")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=dashboard_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=dashboard_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show settings menu."""
    user = update.effective_user
    logger.info(f"User {user.id} accessed settings command")
    
    settings_text = (
        "⚙️ *Settings*:\n\n"
        "Notification preferences: Daily updates\n"
        "Trading status: Active\n\n"
        "Use the buttons below to adjust your settings."
    )
    
    keyboard = [
        [InlineKeyboardButton("Update Wallet Address", callback_data="update_wallet")],
        [InlineKeyboardButton("Notification Settings", callback_data="notifications")],
        [InlineKeyboardButton("Trading Preferences", callback_data="trading_prefs")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=settings_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=settings_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the referral program information and user's referral code."""
    user = update.effective_user
    logger.info(f"User {user.id} accessed referral command")
    
    # Simulated data - in a real app, would be retrieved from the database
    referral_code = f"REF{user.id}"
    total_referrals = 0
    referral_earnings = 0.0  # SOL
    
    referral_text = (
        "🔗 *Referral Program*:\n\n"
        "Share your unique referral link with friends and earn 5% of their profits!\n\n"
        f"Your referral code: `{referral_code}`\n\n"
        f"Total referrals: {total_referrals}\n"
        f"Referral earnings: {referral_earnings:.2f} SOL"
    )
    
    keyboard = [
        [InlineKeyboardButton("Share Referral Link", callback_data="share_referral")],
        [InlineKeyboardButton("View Referral Stats", callback_data="referral_stats")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=referral_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=referral_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
