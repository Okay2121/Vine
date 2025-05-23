"""
Trade Broadcast Handler for Admin Messages
------------------------------------------
This module handles the processing of trade broadcast messages in the format:
$TOKEN_NAME ENTRY_PRICE EXIT_PRICE ROI_PERCENT TX_HASH [OPTIONAL:TRADE_TYPE]
"""

import re
import logging
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, Profit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pattern to match trade broadcast format (Buy/Sell $TOKEN PRICE TX_LINK)
BUY_PATTERN = re.compile(r'^Buy\s+\$([A-Z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)
SELL_PATTERN = re.compile(r'^Sell\s+\$([A-Z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)

def extract_trade_details(text):
    """
    Extract trade details from the format:
    Buy $TOKEN ENTRY_PRICE EXIT_PRICE TX_HASH
    Sell $TOKEN ENTRY_PRICE EXIT_PRICE TX_HASH
    
    Args:
        text (str): Text message to parse
        
    Returns:
        dict or None: Extracted trade details or None if format doesn't match
    """
    # Check if it's a buy message
    buy_match = BUY_PATTERN.match(text.strip())
    if buy_match:
        token_name, entry_price, exit_price, tx_hash = buy_match.groups()
        
        # Calculate ROI percentage
        entry_price_float = float(entry_price)
        exit_price_float = float(exit_price)
        roi_percent = ((exit_price_float - entry_price_float) / entry_price_float) * 100
        
        return {
            'trade_type': 'buy',
            'token_name': token_name,
            'entry_price': entry_price_float,
            'exit_price': exit_price_float,
            'roi_percent': roi_percent,
            'tx_hash': tx_hash,
            'trade_subtype': 'scalp'  # Default trade type
        }
    
    # Check if it's a sell message
    sell_match = SELL_PATTERN.match(text.strip())
    if sell_match:
        token_name, entry_price, exit_price, tx_hash = sell_match.groups()
        
        # Calculate ROI percentage
        entry_price_float = float(entry_price)
        exit_price_float = float(exit_price)
        roi_percent = ((exit_price_float - entry_price_float) / entry_price_float) * 100
        
        return {
            'trade_type': 'sell',
            'token_name': token_name,
            'entry_price': entry_price_float,
            'exit_price': exit_price_float,
            'roi_percent': roi_percent,
            'tx_hash': tx_hash,
            'trade_subtype': 'scalp'  # Default trade type
        }
    
    return None

def process_trade_broadcast(details):
    """
    Process a trade broadcast and apply it to all active users
    
    Args:
        details (dict): Trade details
        
    Returns:
        tuple: (success, message, updated_count)
    """
    try:
        with app.app_context():
            # Extract transaction hash from URL if needed
            tx_hash = details['tx_hash'].split('/')[-1] if '/' in details['tx_hash'] else details['tx_hash']
            
            # Check if this transaction has already been processed
            existing = TradingPosition.query.filter_by(
                tx_hash=tx_hash
            ).first()
            
            if existing:
                return False, f"This transaction has already been processed", 0
                
            # Get active users
            users = User.query.filter(User.balance > 0).all()
            if not users:
                return False, "No active users found to process trade for", 0
                
            # Convert ROI to decimal
            roi_decimal = details['roi_percent'] / 100
            
            # Apply trade to each user
            updated_count = 0
            
            for user in users:
                try:
                    # Calculate profit amount based on user balance
                    profit_amount = user.balance * roi_decimal
                    
                    # Update user balance
                    previous_balance = user.balance
                    user.balance += profit_amount
                    
                    # Create a trade position record
                    position = TradingPosition()
                    position.user_id = user.id
                    position.token_name = details['token_name']
                    position.amount = abs(profit_amount / (details['exit_price'] - details['entry_price'])) if details['exit_price'] != details['entry_price'] else 1.0
                    position.entry_price = details['entry_price']
                    position.current_price = details['exit_price']
                    position.timestamp = datetime.utcnow()
                    position.status = 'closed'
                    position.trade_type = details['trade_type']
                    position.tx_hash = tx_hash
                    position.roi_percentage = details['roi_percent']
                    
                    # Record transaction
                    transaction = Transaction()
                    transaction.user_id = user.id
                    transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                    transaction.amount = profit_amount
                    transaction.token_name = details['token_name']
                    transaction.status = 'completed'
                    transaction.notes = f"Trade ROI: {details['roi_percent']}% - {details['token_name']}"
                    transaction.tx_hash = tx_hash
                    transaction.processed_at = datetime.utcnow()
                    
                    # Add profit record
                    profit_record = Profit()
                    profit_record.user_id = user.id
                    profit_record.amount = profit_amount
                    profit_record.percentage = details['roi_percent']
                    profit_record.date = datetime.utcnow().date()
                    
                    db.session.add(position)
                    db.session.add(transaction)
                    db.session.add(profit_record)
                    
                    updated_count += 1
                except Exception as user_error:
                    logger.error(f"Error processing trade for user {user.id}: {str(user_error)}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            return True, f"Trade processed successfully for {updated_count} users", updated_count
    except Exception as e:
        logger.error(f"Error processing trade broadcast: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}", 0

def send_trade_notifications(bot, details, users):
    """
    Send trade notifications to users
    
    Args:
        bot: Bot instance to send messages
        details (dict): Trade details
        users (list): List of users to notify
        
    Returns:
        int: Number of notifications sent
    """
    notification_count = 0
    
    for user in users:
        try:
            if not user.telegram_id:
                continue
                
            # Calculate profit for this user
            profit_amount = user.balance * (details['roi_percent'] / 100)
            
            # Create notification message
            emoji = "📈" if details['roi_percent'] >= 0 else "📉"
            trade_type_text = f" [{details['trade_type']}]" if details['trade_type'] else ""
            
            message = (
                f"{emoji} *Trade Alert{trade_type_text}*\n\n"
                f"• *Token:* ${details['token_name']}\n"
                f"• *Entry:* {details['entry_price']:.8f}\n"
                f"• *Exit:* {details['exit_price']:.8f}\n"
                f"• *ROI:* {details['roi_percent']:.2f}%\n"
                f"• *Your Profit:* {profit_amount:.4f} SOL\n"
                f"• *New Balance:* {user.balance:.4f} SOL\n\n"
                f"_Your dashboard has been updated with this trade._"
            )
            
            bot.send_message(user.telegram_id, message, parse_mode="Markdown")
            notification_count += 1
        except Exception as e:
            logger.error(f"Error sending notification to user {user.id}: {str(e)}")
            continue
            
    return notification_count

def handle_broadcast_message(text, bot=None, chat_id=None):
    """
    Process a trade broadcast message and return the result
    
    Args:
        text (str): Message text
        bot: Optional bot instance for sending notifications
        chat_id: Optional chat ID for sending response
        
    Returns:
        tuple: (success, response_message)
    """
    # Extract trade details
    details = extract_trade_details(text)
    if not details:
        response = (
            "⚠️ *Invalid Trade Format*\n\n"
            "Expected format:\n"
            "`$TOKEN_NAME ENTRY_PRICE EXIT_PRICE ROI_PERCENT TX_HASH [TRADE_TYPE]`\n\n"
            "Example:\n"
            "`$ZING 0.0041 0.0074 80.5 https://solscan.io/tx/abc123 scalp`"
        )
        return False, response
    
    # Process the trade
    success, message, updated_count = process_trade_broadcast(details)
    
    if success:
        # Get users for notifications if bot provided
        if bot and updated_count > 0:
            with app.app_context():
                users = User.query.filter(User.balance > 0).all()
                notification_count = send_trade_notifications(bot, details, users)
        else:
            notification_count = 0
        
        response = (
            f"✅ *Trade Broadcast Successful*\n\n"
            f"• *Token:* ${details['token_name']}\n"
            f"• *Entry Price:* {details['entry_price']}\n"
            f"• *Exit Price:* {details['exit_price']}\n"
            f"• *ROI:* {details['roi_percent']}%\n"
            f"• *Type:* {details['trade_type']}\n"
            f"• *Users Updated:* {updated_count}\n"
            f"• *Notifications Sent:* {notification_count if bot else 'N/A'}\n\n"
            f"_The trade has been applied to all active users' balances._"
        )
    else:
        response = f"⚠️ *Trade Broadcast Failed*\n\n{message}"
    
    return success, response