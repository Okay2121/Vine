"""
Position Results Display Handler
===============================
Displays authentic trade position results using DEX Screener data and enhanced position formatter
"""

import logging
from typing import List, Optional
from models import User, TradingPosition
from utils.enhanced_position_formatter import position_formatter

logger = logging.getLogger(__name__)

def position_results_handler(update, chat_id):
    """
    Display enhanced position results with DEX Screener market data
    
    Args:
        update: Telegram update object
        chat_id: Chat ID for response
    """
    try:
        from bot_v20_runner import bot
        
        # Get user
        user_telegram_id = str(update.get('from', {}).get('id', 0))
        user = User.query.filter_by(telegram_id=user_telegram_id).first()
        
        if not user:
            bot.send_message(chat_id, "❌ User not found. Please start the bot with /start first.")
            return
        
        # Get user's trading positions (both open and closed)
        positions = TradingPosition.query.filter_by(user_id=user.id).order_by(
            TradingPosition.timestamp.desc()
        ).limit(10).all()
        
        if not positions:
            no_positions_msg = (
                "📊 *Your Trading Positions*\n\n"
                "No trading positions found. Start trading to see your positions here!\n\n"
                "💡 *Tip:* Your positions will appear here automatically when trades are executed."
            )
            bot.send_message(chat_id, no_positions_msg, parse_mode="Markdown")
            return
        
        # Format positions using enhanced formatter
        formatted_positions = position_formatter.format_position_list(
            positions, show_live=True, show_exit=True
        )
        
        # Add header with user balance info
        header = (
            f"💰 *Current Balance:* {user.balance:.4f} SOL\n"
            f"📈 *Active Positions:* {len([p for p in positions if p.status == 'open'])}\n"
            f"✅ *Completed Trades:* {len([p for p in positions if p.status == 'closed'])}\n\n"
        )
        
        full_message = header + formatted_positions
        
        # Add navigation keyboard
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔄 Refresh", "callback_data": "position_results"}],
            [{"text": "📊 Performance Dashboard", "callback_data": "dashboard_performance"}],
            [{"text": "🔙 Back to Sniper", "callback_data": "start_sniper"}]
        ])
        
        bot.send_message(
            chat_id, 
            full_message, 
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in position_results_handler: {str(e)}")
        bot.send_message(chat_id, "❌ Error displaying positions. Please try again.")