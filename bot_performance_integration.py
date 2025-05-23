"""
Bot Performance Integration
--------------------------
Integrates the performance tracking and UI with the Telegram bot
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from models import User
from telegram_dashboard_generator import generate_performance_dashboard, refresh_user_data
from telegram_compact_performance import format_compact_performance

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /dashboard command to show performance dashboard
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Find the user in the database
    db_user = User.query.filter_by(telegram_id=str(user.id)).first()
    if not db_user:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Please start the bot with /start first."
        )
        return
    
    # Refresh and get latest performance data
    refresh_user_data(db_user.id)
    dashboard = generate_performance_dashboard(db_user.id)
    
    # Create keyboard with refresh button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_dashboard")],
        [InlineKeyboardButton("💼 Trading History", callback_data="trading_history")]
    ])
    
    # Send the dashboard
    await context.bot.send_message(
        chat_id=chat_id,
        text=dashboard,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def refresh_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the 'Refresh Dashboard' button click
    """
    query = update.callback_query
    await query.answer("Refreshing your dashboard...")
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Find the user in the database
    db_user = User.query.filter_by(telegram_id=str(user.id)).first()
    if not db_user:
        await query.edit_message_text("Please start the bot with /start first.")
        return
    
    # Refresh and get latest performance data
    refresh_user_data(db_user.id)
    dashboard = generate_performance_dashboard(db_user.id)
    
    # Create keyboard with refresh button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_dashboard")],
        [InlineKeyboardButton("💼 Trading History", callback_data="trading_history")]
    ])
    
    # Update the message
    await query.edit_message_text(
        text=dashboard,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def trading_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the 'Trading History' button click
    """
    query = update.callback_query
    await query.answer("Loading trading history...")
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Find the user in the database
    db_user = User.query.filter_by(telegram_id=str(user.id)).first()
    if not db_user:
        await query.edit_message_text("Please start the bot with /start first.")
        return
    
    # Get trading history (last 10 trades)
    from models import Transaction
    
    trades = Transaction.query.filter_by(
        user_id=db_user.id
    ).filter(
        Transaction.transaction_type.in_(['buy', 'sell'])
    ).order_by(
        Transaction.timestamp.desc()
    ).limit(10).all()
    
    # Format the history message
    if trades:
        history = "📜 *TRADING HISTORY*\n\n"
        
        for trade in trades:
            # Determine emoji and styling based on transaction type
            if trade.transaction_type == 'buy':
                action = "🟢 *BUY*"
            elif trade.transaction_type == 'sell':
                action = "🔴 *SELL*"
            else:
                action = "⚪ *TRADE*"
                
            date = trade.timestamp.strftime("%Y-%m-%d %H:%M")
            token = trade.token_name or "Unknown"
            amount = abs(trade.amount)
            
            # Enhanced display with more details
            history += f"{action} {token}\n"
            
            # Show price if available
            if hasattr(trade, 'price') and trade.price:
                history += f"Price: ${trade.price:.6f}\n"
                
            history += f"Amount: {amount:.4f} SOL\n"
            history += f"Date: {date}\n"
            
            # Add transaction link if available
            if hasattr(trade, 'tx_hash') and trade.tx_hash:
                # Create a Solana Explorer link for the transaction
                if trade.tx_hash.startswith('http'):
                    # Link is already provided
                    explorer_url = trade.tx_hash
                else:
                    # Create link from hash
                    explorer_url = f"https://solscan.io/tx/{trade.tx_hash}"
                history += f"[View Transaction]({explorer_url})\n"
            
            # Add separator between transactions
            history += "───────────────────\n\n"
    else:
        history = "📜 *TRADING HISTORY*\n\nNo trading activity found yet."
    
    # Create keyboard to go back to dashboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="refresh_dashboard")]
    ])
    
    # Update the message
    await query.edit_message_text(
        text=history,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


def register_handlers(application):
    """
    Register all performance-related handlers with the bot
    """
    from telegram.ext import CommandHandler, CallbackQueryHandler
    
    # Register command handlers
    application.add_handler(CommandHandler("dashboard", dashboard_command))
    
    # Register callback handlers
    application.add_handler(CallbackQueryHandler(refresh_dashboard_callback, pattern="^refresh_dashboard$"))
    application.add_handler(CallbackQueryHandler(trading_history_callback, pattern="^trading_history$"))
    
    print("Performance dashboard handlers registered successfully")


# Demo function for testing with sample data
def demo_compact_performance():
    """Generate a sample performance dashboard for demonstration"""
    return format_compact_performance(
        initial_deposit=10.0,
        current_balance=14.5,
        today_profit=1.2,
        today_percentage=12.0,
        total_profit=4.5,
        total_percentage=45.0,
        streak_days=3,
        current_day=8,
        total_days=30,
        milestone_target=10.0,
        milestone_current=4.5,
        goal_target=20.0,
        recent_trades=[
            {"token": "BONK", "time_ago": "1h"},
            {"token": "WIF", "time_ago": "3h"},
            {"token": "SAMO", "time_ago": "6h"}
        ]
    )