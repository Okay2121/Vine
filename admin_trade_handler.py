"""
Admin Trade Handler for Telegram Bot
-------------------------------------------
This module handles admin trade messages in the new simplified format:
Buy $TOKEN PRICE TX_LINK or Sell $TOKEN PRICE TX_LINK
"""

import logging
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction
from trade_processor import parse_trade_message, process_buy_trade, process_sell_trade, apply_trade_to_users

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def handle_admin_trade_message(update, chat_id, bot):
    """
    Process an admin trade message in the Buy/Sell format.
    
    Args:
        update (dict): Telegram update object
        chat_id (str): Chat ID to reply to
        bot: Telegram bot instance
        
    Returns:
        bool: True if the message was handled, False otherwise
    """
    try:
        # Get message text
        message_text = update.get('message', {}).get('text', '')
        
        # Skip if not a message with text
        if not message_text:
            return False
            
        # Check if this is an admin user
        from bot_v20_runner import is_admin
        if not is_admin(update['message']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return True
        
        # Parse the trade message
        parsed_data = parse_trade_message(message_text)
        
        # If not a valid trade message, don't handle it
        if not parsed_data:
            return False
        
        logger.info(f"Processing trade message: {parsed_data}")
        
        # Process based on trade type
        if parsed_data['trade_type'] == 'buy':
            # Process BUY trade
            success, message, position = process_buy_trade(
                parsed_data['token_name'],
                parsed_data['price'],
                parsed_data['tx_link']
            )
            
            if success:
                response = (
                    f"✅ *BUY Order Recorded*\n\n"
                    f"• *Token:* {parsed_data['token_name']}\n"
                    f"• *Entry Price:* {parsed_data['price']}\n"
                    f"• *Transaction:* [View on Explorer]({parsed_data['tx_link']})\n"
                    f"• *Timestamp:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"_This BUY will be matched with a future SELL order._"
                )
            else:
                response = f"⚠️ *Error Recording BUY*\n\n{message}"
                
            bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)
            return True
            
        elif parsed_data['trade_type'] == 'sell':
            # Process SELL trade
            success, message, position, roi = process_sell_trade(
                parsed_data['token_name'],
                parsed_data['price'],
                parsed_data['tx_link']
            )
            
            if success and position:
                # Apply the trade to all active users
                apply_success, apply_message, updated_count = apply_trade_to_users(position)
                
                response = (
                    f"✅ *SELL Order Processed*\n\n"
                    f"• *Token:* {parsed_data['token_name']}\n"
                    f"• *Exit Price:* {parsed_data['price']}\n"
                    f"• *Transaction:* [View on Explorer]({parsed_data['tx_link']})\n"
                    f"• *Entry Price:* {position.entry_price}\n"
                    f"• *ROI:* {roi:.2f}%\n"
                    f"• *Users Updated:* {updated_count}\n\n"
                    f"_Trade has been applied to all active users' balances._"
                )
            else:
                response = f"⚠️ *Error Processing SELL*\n\n{message}"
                
            bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error in handle_admin_trade_message: {e}")
        bot.send_message(chat_id, f"⚠️ Error processing trade message: {str(e)}")
        return True


def broadcast_trade_to_users(position, bot):
    """
    Broadcast a completed trade to all affected users.
    
    Args:
        position (TradingPosition): The completed trade position
        bot: Telegram bot instance
        
    Returns:
        tuple: (success, message, count)
    """
    try:
        # Get all users with this position (paired positions)
        user_positions = TradingPosition.query.filter_by(
            paired_position_id=position.id
        ).all()
        
        if not user_positions:
            # Get all users with matching buy and sell tx hashes
            user_positions = TradingPosition.query.filter_by(
                buy_tx_hash=position.buy_tx_hash,
                sell_tx_hash=position.sell_tx_hash,
                status='closed'
            ).all()
        
        if not user_positions:
            return (False, "No user positions found for this trade", 0)
        
        # Keep track of how many messages were sent
        broadcast_count = 0
        
        # Send personalized messages to users
        for user_position in user_positions:
            try:
                # Get the user
                user = User.query.filter_by(id=user_position.user_id).first()
                
                if not user or not user.telegram_id:
                    continue
                    
                # Calculate profit amount for this user
                profit_percentage = position.roi_percentage / 100  # Convert to decimal
                profit_amount = user.balance * profit_percentage
                
                # Create personalized message
                emoji = "📈" if position.roi_percentage >= 0 else "📉"
                message = (
                    f"{emoji} *Trade Notification*\n\n"
                    f"• *Token:* {position.token_name}\n"
                    f"• *Entry:* {position.entry_price:.8f}\n"
                    f"• *Exit:* {position.current_price:.8f}\n"
                    f"• *ROI:* {position.roi_percentage:.2f}%\n"
                    f"• *Your Profit:* {profit_amount:.4f} SOL\n"
                    f"• *New Balance:* {user.balance:.4f} SOL\n\n"
                    f"_Your dashboard has been updated automatically with this trade._"
                )
                
                # Send message to user
                bot.send_message(user.telegram_id, message, parse_mode="Markdown")
                broadcast_count += 1
                
            except Exception as user_error:
                logger.error(f"Error broadcasting to user {user_position.user_id}: {str(user_error)}")
                continue
        
        return (True, f"Trade broadcast to {broadcast_count} users", broadcast_count)
        
    except Exception as e:
        logger.error(f"Error broadcasting trade: {str(e)}")
        return (False, f"Error broadcasting trade: {str(e)}", 0)