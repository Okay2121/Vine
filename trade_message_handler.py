"""
Trade Message Handler for Telegram Bot
---------------------------------------
This module handles the processing of trade messages in the format:
Buy $TOKEN PRICE TX_LINK or Sell $TOKEN PRICE TX_LINK
"""

import re
import logging
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, Profit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regular expressions for matching buy/sell messages
BUY_PATTERN = re.compile(r'^buy\s+(\$[a-zA-Z0-9]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)
SELL_PATTERN = re.compile(r'^sell\s+(\$[a-zA-Z0-9]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)

def handle_buy(token, price, tx_link):
    """Process a BUY trade message"""
    try:
        with app.app_context():
            # Clean token name (remove $ if present)
            clean_token = token.replace('$', '')
            
            # Extract TX hash from link
            tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
            
            # Check if this transaction was already processed
            existing = TradingPosition.query.filter_by(buy_tx_hash=tx_hash).first()
            if existing:
                return False, f"This BUY transaction has already been processed for {existing.token_name}"
            
            # Create a new position
            position = TradingPosition()
            position.user_id = 1  # Placeholder - will be updated when matched with SELL
            position.token_name = clean_token
            position.amount = 1.0  # Placeholder - will be calculated during SELL
            position.entry_price = float(price)
            position.current_price = float(price)
            position.timestamp = datetime.utcnow()
            position.status = 'open'
            position.trade_type = 'scalp'  # Default trade type
            position.buy_tx_hash = tx_hash
            position.buy_timestamp = datetime.utcnow()
            
            db.session.add(position)
            db.session.commit()
            
            return True, f"BUY position for {token} at {price} recorded successfully (ID: {position.id})"
    except Exception as e:
        logger.error(f"Error processing BUY: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

def handle_sell(token, price, tx_link):
    """Process a SELL trade message"""
    try:
        with app.app_context():
            # Clean token name
            clean_token = token.replace('$', '')
            
            # Extract TX hash from link
            tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
            
            # Check if this transaction was already processed
            existing = TradingPosition.query.filter_by(sell_tx_hash=tx_hash).first()
            if existing:
                return False, f"This SELL transaction has already been processed"
            
            # Find the matching BUY position (oldest open position for this token)
            position = TradingPosition.query.filter_by(
                token_name=clean_token,
                status='open'
            ).order_by(TradingPosition.buy_timestamp.asc()).first()
            
            if not position:
                return False, f"No open BUY position found for {token}"
            
            # Calculate ROI percentage
            sell_price = float(price)
            entry_price = position.entry_price
            roi_percentage = ((sell_price - entry_price) / entry_price) * 100
            
            # Update the position
            position.current_price = sell_price
            position.sell_tx_hash = tx_hash
            position.sell_timestamp = datetime.utcnow()
            position.status = 'closed'
            position.roi_percentage = roi_percentage
            
            # Apply profit to all active users
            users = User.query.filter(User.balance > 0).all()
            updated_count = 0
            
            for user in users:
                try:
                    # Calculate profit for this user
                    profit_amount = user.balance * (roi_percentage / 100)
                    
                    # Update user balance
                    previous_balance = user.balance
                    user.balance += profit_amount
                    
                    # Record transaction
                    transaction = Transaction()
                    transaction.user_id = user.id
                    transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                    transaction.amount = profit_amount
                    transaction.token_name = clean_token
                    transaction.status = 'completed'
                    transaction.notes = f"Trade ROI: {roi_percentage:.2f}% - {clean_token}"
                    transaction.tx_hash = tx_hash
                    transaction.processed_at = datetime.utcnow()
                    
                    # Create user position record
                    user_position = TradingPosition()
                    user_position.user_id = user.id
                    user_position.token_name = clean_token
                    user_position.amount = abs(profit_amount / (sell_price - entry_price)) if sell_price != entry_price else 1.0
                    user_position.entry_price = entry_price
                    user_position.current_price = sell_price
                    user_position.timestamp = datetime.utcnow()
                    user_position.status = 'closed'
                    user_position.trade_type = position.trade_type if position.trade_type else 'scalp'
                    user_position.buy_tx_hash = position.buy_tx_hash
                    user_position.sell_tx_hash = tx_hash
                    user_position.buy_timestamp = position.buy_timestamp
                    user_position.sell_timestamp = datetime.utcnow()
                    user_position.roi_percentage = roi_percentage
                    user_position.paired_position_id = position.id
                    
                    # Add profit record
                    profit_record = Profit()
                    profit_record.user_id = user.id
                    profit_record.amount = profit_amount
                    profit_record.percentage = roi_percentage
                    profit_record.date = datetime.utcnow().date()
                    
                    db.session.add(transaction)
                    db.session.add(user_position)
                    db.session.add(profit_record)
                    
                    updated_count += 1
                except Exception as user_error:
                    logger.error(f"Error updating user {user.id}: {str(user_error)}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            return True, f"SELL processed for {token}. ROI: {roi_percentage:.2f}%. Updated {updated_count} users."
    except Exception as e:
        logger.error(f"Error processing SELL: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

def process_trade_message(message_text, is_admin=False):
    """
    Process a trade message and return the result
    
    Args:
        message_text (str): The message text to process
        is_admin (bool): Whether the message is from an admin
        
    Returns:
        tuple: (is_trade_message, success, response_text)
    """
    # Skip processing if not an admin message
    if not is_admin:
        return False, False, ""
    
    # Clean message text
    text = message_text.strip()
    
    # Check for buy message
    buy_match = BUY_PATTERN.match(text)
    if buy_match:
        token, price, tx_link = buy_match.groups()
        success, message = handle_buy(token, price, tx_link)
        
        if success:
            response = (
                f"✅ *BUY Order Recorded*\n\n"
                f"• *Token:* {token}\n"
                f"• *Entry Price:* {price}\n"
                f"• *Transaction:* [View on Explorer]({tx_link})\n"
                f"• *Timestamp:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"_This BUY will be matched with a future SELL order._"
            )
        else:
            response = f"⚠️ *Error Recording BUY*\n\n{message}"
            
        return True, success, response
    
    # Check for sell message
    sell_match = SELL_PATTERN.match(text)
    if sell_match:
        token, price, tx_link = sell_match.groups()
        success, message = handle_sell(token, price, tx_link)
        
        if success:
            response = (
                f"✅ *SELL Order Processed*\n\n"
                f"• *Token:* {token}\n"
                f"• *Exit Price:* {price}\n"
                f"• *Transaction:* [View on Explorer]({tx_link})\n\n"
                f"{message}"
            )
        else:
            response = f"⚠️ *Error Processing SELL*\n\n{message}"
            
        return True, success, response
    
    # Not a trade message
    return False, False, ""