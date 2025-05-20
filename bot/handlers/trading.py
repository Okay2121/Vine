"""
Trading handler module
Manages trading operations, settings and performance tracking
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
from services.trading_engine import get_trading_status, pause_trading, resume_trading
from services.roi_tracker import get_performance_stats

logger = logging.getLogger(__name__)

async def trading_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /trading command - shows trading status and controls"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Mock data for demonstration - would fetch from actual trading engine
        is_active = True
        current_trades = 2
        last_completed = "BONK @ +8.3% (2 hours ago)"
        daily_stats = {
            "completed": 12,
            "success_rate": 91.7,
            "avg_roi": 8.5
        }
        
        status_text = "✅ ACTIVE" if is_active else "⏸️ PAUSED"
        
        message = (
            "⚙️ *TRADING STATUS*\n\n"
            f"Status: {status_text}\n"
            f"Current trades: {current_trades}\n"
            f"Last completed: {last_completed}\n\n"
            f"*Today's Statistics:*\n"
            f"Completed trades: {daily_stats['completed']}\n"
            f"Success rate: {daily_stats['success_rate']}%\n"
            f"Average ROI: {daily_stats['avg_roi']}%\n\n"
            "You can control your trading activity below:"
        )
        
        # Control buttons depend on current status
        if is_active:
            controls = [
                [InlineKeyboardButton("⏸️ Pause Trading", callback_data="pause_trading")],
            ]
        else:
            controls = [
                [InlineKeyboardButton("▶️ Resume Trading", callback_data="resume_trading")],
            ]
            
        # Add common buttons
        controls.append([InlineKeyboardButton("📊 Performance History", callback_data="performance_history")])
        controls.append([InlineKeyboardButton("⚙️ Trading Settings", callback_data="trading_settings")])
        controls.append([InlineKeyboardButton("💼 Back to Dashboard", callback_data="dashboard")])
            
        keyboard = InlineKeyboardMarkup(controls)
        
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
        logger.error(f"Error in trading_command: {e}")
        error_message = "Sorry, there was an error accessing trading information. Please try again."
        
        if update.callback_query:
            await update.callback_query.answer("Error loading trading status")
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def pause_trading_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Pause Trading' button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Call service to pause trading - would actually update in database
        success = True  # Assume success for demonstration
        
        if success:
            message = (
                "⏸️ *Trading Paused*\n\n"
                "Your active trades will complete normally, but no new trades will be started.\n\n"
                "You can resume trading at any time."
            )
        else:
            message = "❌ There was an error pausing your trading. Please try again."
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Resume Trading", callback_data="resume_trading")],
            [InlineKeyboardButton("💼 Back to Dashboard", callback_data="dashboard")]
        ])
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in pause_trading_callback: {e}")
        await query.edit_message_text(
            "Sorry, there was an error pausing trading. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Trading", callback_data="trading")]
            ])
        )

async def resume_trading_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Resume Trading' button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Call service to resume trading - would actually update in database
        success = True  # Assume success for demonstration
        
        if success:
            message = (
                "▶️ *Trading Resumed*\n\n"
                "Your account is now actively trading again.\n\n"
                "New trade opportunities will be detected and executed automatically."
            )
        else:
            message = "❌ There was an error resuming your trading. Please try again."
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸️ Pause Trading", callback_data="pause_trading")],
            [InlineKeyboardButton("💼 Back to Dashboard", callback_data="dashboard")]
        ])
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in resume_trading_callback: {e}")
        await query.edit_message_text(
            "Sorry, there was an error resuming trading. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Trading", callback_data="trading")]
            ])
        )

async def performance_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Performance History' button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Mock performance history data
        weekly_performance = [
            {"period": "Past 24 hours", "trades": 12, "success_rate": 91.7, "roi": 8.5},
            {"period": "Past 7 days", "trades": 78, "success_rate": 93.2, "roi": 61.8},
            {"period": "Past 30 days", "trades": 302, "success_rate": 94.1, "roi": 244.7}
        ]
        
        message = "*📊 PERFORMANCE HISTORY*\n\n"
        
        for period in weekly_performance:
            message += (
                f"*{period['period']}*\n"
                f"Trades completed: {period['trades']}\n"
                f"Success rate: {period['success_rate']}%\n"
                f"Total ROI: {period['roi']}%\n\n"
            )
        
        message += "Our algorithm continuously improves by learning from market patterns."
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Trading", callback_data="trading")]
        ])
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in performance_history_callback: {e}")
        await query.edit_message_text(
            "Sorry, there was an error loading performance history. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Trading", callback_data="trading")]
            ])
        )

async def trading_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Trading Settings' button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Mock settings data
        settings = {
            "risk_level": "Medium",
            "auto_reinvest": "Off",
            "max_simultaneous_trades": 3,
            "profit_target": "12% daily"
        }
        
        message = (
            "⚙️ *TRADING SETTINGS*\n\n"
            f"Risk level: {settings['risk_level']}\n"
            f"Auto-reinvest: {settings['auto_reinvest']}\n"
            f"Max simultaneous trades: {settings['max_simultaneous_trades']}\n"
            f"Profit target: {settings['profit_target']}\n\n"
            "Select a setting to change:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Change Risk Level", callback_data="change_risk_level")],
            [InlineKeyboardButton("♻️ Toggle Auto-Reinvest", callback_data="toggle_auto_reinvest")],
            [InlineKeyboardButton("⬅️ Back to Trading", callback_data="trading")]
        ])
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in trading_settings_callback: {e}")
        await query.edit_message_text(
            "Sorry, there was an error loading trading settings. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Trading", callback_data="trading")]
            ])
        )

def register_trading_handlers(application: Application):
    """Register all handlers related to trading functionality"""
    # Trading command handler
    application.add_handler(CommandHandler("trading", trading_command))
    
    # Trading callback handlers
    application.add_handler(CallbackQueryHandler(trading_command, pattern="^trading$"))
    application.add_handler(CallbackQueryHandler(pause_trading_callback, pattern="^pause_trading$"))
    application.add_handler(CallbackQueryHandler(resume_trading_callback, pattern="^resume_trading$"))
    application.add_handler(CallbackQueryHandler(performance_history_callback, pattern="^performance_history$"))
    application.add_handler(CallbackQueryHandler(trading_settings_callback, pattern="^trading_settings$"))