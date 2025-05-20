"""
Balance handler module
Handles deposit, withdrawal, and balance adjustment operations
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Import services
from services.trading_engine import start_trading_with_amount
from services.roi_tracker import get_user_roi

# Import utilities
from utils.logger import log_exception

logger = logging.getLogger(__name__)

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /deposit command"""
    user = update.effective_user
    
    # Create deposit instructions
    deposit_address = "YOUR_DEPOSIT_ADDRESS"  # This would be fetched from database
    
    message = (
        "📥 *Deposit SOL to Start Trading*\n\n"
        "1️⃣ Send SOL to this deposit address:\n"
        f"`{deposit_address}`\n\n"
        "2️⃣ Your deposit will be automatically detected\n\n"
        "3️⃣ Trading will start immediately after confirmation\n\n"
        "Minimum deposit: 0.1 SOL\n"
        "Recommended: 1+ SOL for better results"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Copy Address", callback_data="copy_address")],
        [InlineKeyboardButton("✅ I've Made a Deposit", callback_data="deposit_confirmed")]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def copy_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Copy Address' button click"""
    query = update.callback_query
    await query.answer("Address copied to clipboard!")
    # The actual copy to clipboard is handled by Telegram automatically

async def deposit_confirmed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'I've Made a Deposit' button click"""
    query = update.callback_query
    await query.answer()
    
    # In a real implementation, you would check the blockchain
    # For this example, we'll just inform the user
    message = (
        "🔍 *Checking for your deposit*\n\n"
        "We're monitoring the blockchain for your transaction.\n\n"
        "As soon as your deposit is confirmed (typically 1-2 minutes),\n"
        "trading will begin automatically, and you'll receive a notification.\n\n"
        "You can check your dashboard at any time to see your balance."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 View Dashboard", callback_data="dashboard")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /withdraw command"""
    user = update.effective_user
    
    # Would normally get this from the database
    available_balance = 1.25  # Example balance in SOL
    
    message = (
        "💸 *Withdraw Funds*\n\n"
        f"Available balance: {available_balance:.4f} SOL\n\n"
        "To withdraw, please specify the amount in SOL.\n"
        "Example: `/withdraw 0.5`\n\n"
        "Withdrawals are typically processed within 30 minutes."
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdraw command with amount"""
    user = update.effective_user
    
    try:
        # Parse the withdraw amount
        if len(context.args) < 1:
            await update.message.reply_text(
                "Please specify an amount to withdraw.\n"
                "Example: `/withdraw 0.5`"
            )
            return
            
        amount = float(context.args[0])
        
        # In a real implementation, you would check balance and process withdrawal
        # For this example, we'll just acknowledge the request
        
        if amount <= 0:
            await update.message.reply_text("Withdrawal amount must be greater than 0.")
            return
            
        # Mock withdrawal process
        message = (
            "✅ *Withdrawal Request Received*\n\n"
            f"Amount: {amount:.4f} SOL\n\n"
            "Your withdrawal is being processed and will be sent to your registered wallet address.\n\n"
            "You will receive a confirmation when the transaction is complete."
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 View Dashboard", callback_data="dashboard")]
        ])
        
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")
        
    except ValueError:
        await update.message.reply_text(
            "Invalid amount format. Please use a number.\n"
            "Example: `/withdraw 0.5`"
        )
    except Exception as e:
        log_exception(logger, e, f"Error in withdraw_amount_handler for user {user.id}")
        await update.message.reply_text("An error occurred processing your withdrawal. Please try again.")

def register_balance_handlers(application: Application):
    """Register all handlers related to balance operations"""
    # Deposit handlers
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CallbackQueryHandler(copy_address_callback, pattern="^copy_address$"))
    application.add_handler(CallbackQueryHandler(deposit_confirmed_callback, pattern="^deposit_confirmed$"))
    
    # Withdraw handlers
    application.add_handler(CommandHandler("withdraw", withdraw_amount_handler, filters.COMMAND & ~filters.FORWARDED))