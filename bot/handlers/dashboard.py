"""
Dashboard handler module
Provides users with their account overview, trading stats and balance information
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
from services.roi_tracker import get_user_roi, get_profit_history
from services.trading_engine import get_trading_stats

# Import utilities
from utils.database import get_user_balance, get_user_trades

logger = logging.getLogger(__name__)

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /dashboard command - shows user account overview"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # In real implementation, these would fetch from database
        # Mock data for demonstration
        balance = 1.25  # SOL
        active_trading = 1.0  # SOL
        profit = 0.25  # SOL
        roi_percentage = 25  # %
        streak = 3  # days
        
        message = (
            "💼 *YOUR DASHBOARD*\n\n"
            f"💰 *Balance:* {balance:.4f} SOL\n"
            f"⚙️ *Active Trading:* {active_trading:.4f} SOL\n"
            f"📈 *Profit:* +{profit:.4f} SOL\n"
            f"🔄 *ROI:* +{roi_percentage}%\n"
            f"🔥 *Profit Streak:* {streak} days\n\n"
            "What would you like to do?"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Trading History", callback_data="trading_history")],
            [
                InlineKeyboardButton("💸 Withdraw Profit", callback_data="withdraw_profit"),
                InlineKeyboardButton("♻️ Reinvest", callback_data="reinvest")
            ],
            [InlineKeyboardButton("📥 Deposit More", callback_data="deposit")]
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
            
    except Exception as e:
        logger.error(f"Error in dashboard_command: {e}")
        error_message = "Sorry, there was an error loading your dashboard. Please try again."
        
        if update.callback_query:
            await update.callback_query.answer("Error loading dashboard")
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def trading_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Trading History' button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Mock trade history data
        trades = [
            {"date": "2025-05-19", "token": "BONK", "profit": "+0.1 SOL", "roi": "+10%"},
            {"date": "2025-05-18", "token": "SAMO", "profit": "+0.08 SOL", "roi": "+8%"},
            {"date": "2025-05-17", "token": "PEPE", "profit": "+0.07 SOL", "roi": "+7%"},
        ]
        
        history_text = "*📊 YOUR TRADING HISTORY*\n\n"
        
        for trade in trades:
            history_text += (
                f"*{trade['date']}*\n"
                f"Token: {trade['token']}\n"
                f"Profit: {trade['profit']}\n"
                f"ROI: {trade['roi']}\n\n"
            )
        
        history_text += "Our trading algorithm targets consistent daily profits."
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="dashboard")]
        ])
        
        await query.edit_message_text(
            history_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in trading_history_callback: {e}")
        await query.edit_message_text(
            "Sorry, there was an error loading your trading history. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="dashboard")]
            ])
        )

async def withdraw_profit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Withdraw Profit' button click"""
    query = update.callback_query
    await query.answer()
    
    # In a real implementation, you would get this from the database
    profit = 0.25  # SOL
    
    message = (
        "💸 *Withdraw Your Profit*\n\n"
        f"Available profit: {profit:.4f} SOL\n\n"
        "To withdraw, use the command:\n"
        "`/withdraw [amount]`\n\n"
        "Example: `/withdraw 0.2`\n\n"
        "You can withdraw any amount up to your available profit."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="dashboard")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def reinvest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Reinvest' button click"""
    query = update.callback_query
    await query.answer()
    
    # In a real implementation, you would get this from the database
    profit = 0.25  # SOL
    
    message = (
        "♻️ *Reinvest Your Profit*\n\n"
        f"Available profit for reinvestment: {profit:.4f} SOL\n\n"
        "Reinvesting your profits can accelerate your earnings through compound growth.\n\n"
        "Do you want to reinvest all available profit?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Reinvest All", callback_data="confirm_reinvest"),
            InlineKeyboardButton("⬅️ Back", callback_data="dashboard")
        ]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def confirm_reinvest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Confirm Reinvest' button click"""
    query = update.callback_query
    await query.answer()
    
    # In a real implementation, you would update the database
    profit = 0.25  # SOL
    
    message = (
        "✅ *Profit Reinvested Successfully!*\n\n"
        f"{profit:.4f} SOL has been added to your active trading balance.\n\n"
        "Your increased trading balance will generate higher daily profits."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 View Updated Dashboard", callback_data="dashboard")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

def register_dashboard_handlers(application: Application):
    """Register all handlers related to the dashboard"""
    # Dashboard command handler
    application.add_handler(CommandHandler("dashboard", dashboard_command))
    
    # Dashboard callback handlers
    application.add_handler(CallbackQueryHandler(dashboard_command, pattern="^dashboard$"))
    application.add_handler(CallbackQueryHandler(trading_history_callback, pattern="^trading_history$"))
    application.add_handler(CallbackQueryHandler(withdraw_profit_callback, pattern="^withdraw_profit$"))
    application.add_handler(CallbackQueryHandler(reinvest_callback, pattern="^reinvest$"))
    application.add_handler(CallbackQueryHandler(confirm_reinvest_callback, pattern="^confirm_reinvest$"))