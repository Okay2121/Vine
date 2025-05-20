"""
Settings handler module
Allows users to configure their preferences
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Import utilities
from utils.database import update_user_setting, get_user_settings

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_WALLET = 1
WAITING_FOR_RISK_LEVEL = 2

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /settings command"""
    user = update.effective_user
    
    # In a real implementation, these would be fetched from database
    # Mock settings for demonstration
    settings = {
        'wallet_address': 'SOLANA123456...',
        'risk_level': 'Medium',
        'auto_reinvest': False,
        'notifications_enabled': True,
        'daily_report': True
    }
    
    message = (
        "⚙️ *YOUR SETTINGS*\n\n"
        f"🔑 *Wallet Address:* `{settings['wallet_address'][:8]}...`\n"
        f"🎯 *Risk Level:* {settings['risk_level']}\n"
        f"♻️ *Auto-Reinvest:* {'On' if settings['auto_reinvest'] else 'Off'}\n"
        f"🔔 *Notifications:* {'On' if settings['notifications_enabled'] else 'Off'}\n"
        f"📊 *Daily Report:* {'On' if settings['daily_report'] else 'Off'}\n\n"
        "What would you like to change?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Change Wallet Address", callback_data="change_wallet")],
        [InlineKeyboardButton("🎯 Change Risk Level", callback_data="change_risk")],
        [InlineKeyboardButton("♻️ Toggle Auto-Reinvest", callback_data="toggle_reinvest")],
        [InlineKeyboardButton("🔔 Toggle Notifications", callback_data="toggle_notifications")],
        [InlineKeyboardButton("📊 Toggle Daily Report", callback_data="toggle_daily_report")]
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

async def change_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Change Wallet Address' button click"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "🔑 *CHANGE WALLET ADDRESS*\n\n"
        "Please enter your new Solana wallet address.\n\n"
        "This address will be used for all future withdrawals."
    )
    
    # Store that we're waiting for a wallet address
    context.user_data['settings_state'] = WAITING_FOR_WALLET
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="settings")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def process_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the user's submitted wallet address"""
    wallet_address = update.message.text.strip()
    
    # Basic validation - should be enhanced with actual Solana address validation
    if len(wallet_address) < 30 or not wallet_address.startswith(('So', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
        await update.message.reply_text(
            "❌ That doesn't look like a valid Solana wallet address. Please provide a valid Solana address.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")]
            ])
        )
        return ConversationHandler.END
    
    # In a real implementation, this would update the database
    success = True  # Assume success for demonstration
    
    if success:
        message = (
            "✅ *Wallet Address Updated*\n\n"
            f"Your new withdrawal address has been set to:\n`{wallet_address[:8]}...{wallet_address[-4:]}`\n\n"
            "All future withdrawals will be sent to this address."
        )
    else:
        message = "❌ There was an error updating your wallet address. Please try again."
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")
    return ConversationHandler.END

async def change_risk_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Change Risk Level' button click"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "🎯 *CHANGE RISK LEVEL*\n\n"
        "Select your preferred risk level:\n\n"
        "🟢 *Low Risk*\n"
        "• Smaller, safer trades\n"
        "• Lower potential ROI (5-8%)\n"
        "• Higher success rate\n\n"
        "🟠 *Medium Risk*\n"
        "• Balanced approach\n"
        "• Moderate ROI (8-12%)\n"
        "• Good success rate\n\n"
        "🔴 *High Risk*\n"
        "• Larger, more volatile trades\n"
        "• Higher potential ROI (12-20%)\n"
        "• Lower success rate"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Low Risk", callback_data="risk_low")],
        [InlineKeyboardButton("🟠 Medium Risk", callback_data="risk_medium")],
        [InlineKeyboardButton("🔴 High Risk", callback_data="risk_high")],
        [InlineKeyboardButton("⬅️ Cancel", callback_data="settings")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def risk_level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle risk level selection"""
    query = update.callback_query
    await query.answer()
    
    # Get the selected risk level
    callback_data = query.data
    if callback_data == "risk_low":
        risk_level = "Low"
    elif callback_data == "risk_medium":
        risk_level = "Medium"
    elif callback_data == "risk_high":
        risk_level = "High"
    else:
        # Invalid selection
        await query.edit_message_text(
            "❌ Invalid risk level selection. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")]
            ])
        )
        return
    
    # In a real implementation, this would update the database
    success = True  # Assume success for demonstration
    
    if success:
        message = (
            f"✅ *Risk Level Updated*\n\n"
            f"Your risk level has been set to: *{risk_level}*\n\n"
            f"This will take effect for all new trades."
        )
    else:
        message = "❌ There was an error updating your risk level. Please try again."
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def toggle_setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle toggling a boolean setting"""
    query = update.callback_query
    await query.answer()
    
    # Get the setting to toggle
    callback_data = query.data
    
    if callback_data == "toggle_reinvest":
        setting_name = "Auto-Reinvest"
        setting_key = "auto_reinvest"
    elif callback_data == "toggle_notifications":
        setting_name = "Notifications"
        setting_key = "notifications_enabled"
    elif callback_data == "toggle_daily_report":
        setting_name = "Daily Report"
        setting_key = "daily_report"
    else:
        # Invalid setting
        await query.edit_message_text(
            "❌ Invalid setting. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")]
            ])
        )
        return
    
    # In a real implementation, this would get and update the database
    # For demonstration, we'll just toggle a mock value
    current_value = False  # This would be fetched from database
    new_value = not current_value
    
    # Assume the update is successful
    success = True
    
    if success:
        message = (
            f"✅ *{setting_name} Updated*\n\n"
            f"Your {setting_name} setting has been turned {'On' if new_value else 'Off'}."
        )
    else:
        message = f"❌ There was an error updating your {setting_name} setting. Please try again."
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

def register_settings_handlers(application: Application):
    """Register all handlers related to settings"""
    # Settings command handler
    application.add_handler(CommandHandler("settings", settings_command))
    
    # Settings callback handlers
    application.add_handler(CallbackQueryHandler(settings_command, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(change_wallet_callback, pattern="^change_wallet$"))
    application.add_handler(CallbackQueryHandler(change_risk_callback, pattern="^change_risk$"))
    application.add_handler(CallbackQueryHandler(toggle_setting_callback, pattern="^toggle_reinvest$"))
    application.add_handler(CallbackQueryHandler(toggle_setting_callback, pattern="^toggle_notifications$"))
    application.add_handler(CallbackQueryHandler(toggle_setting_callback, pattern="^toggle_daily_report$"))
    application.add_handler(CallbackQueryHandler(risk_level_callback, pattern="^risk_"))
    
    # Conversation handler for wallet address
    wallet_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(change_wallet_callback, pattern="^change_wallet$")],
        states={
            WAITING_FOR_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet_address)
            ]
        },
        fallbacks=[CommandHandler("settings", settings_command)]
    )
    
    application.add_handler(wallet_conversation)