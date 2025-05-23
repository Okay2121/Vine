"""
Trade Broadcast Handler for Admin Messages
------------------------------------------
This module handles the processing of trade broadcast messages in the format:
Buy $TOKEN PRICE TX_HASH or Sell $TOKEN PRICE TX_HASH
Example: Buy $ZING 0.0041 https://solscan.io/tx/abc123
"""

import re
import logging
import traceback
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, Profit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pattern to match trade broadcast format (Buy/Sell $TOKEN PRICE TX_LINK)
BUY_PATTERN = re.compile(r'^Buy\s+\$([A-Z0-9_]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)
SELL_PATTERN = re.compile(r'^Sell\s+\$([A-Z0-9_]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)

def extract_trade_details(text):
    """
    Extract trade details from the format:
    Buy $TOKEN PRICE TX_HASH
    Sell $TOKEN PRICE TX_HASH
    
    Args:
        text (str): Text message to parse
        
    Returns:
        dict or None: Extracted trade details or None if format doesn't match
    """
    # Check if it's a buy message
    buy_match = BUY_PATTERN.match(text.strip())
    if buy_match:
        token_name, price, tx_hash = buy_match.groups()
        
        # Convert price to float
        price_float = float(price)
        
        return {
            'trade_type': 'buy',
            'token_name': token_name,
            'price': price_float,
            'tx_hash': tx_hash,
            'trade_subtype': 'scalp'  # Default trade type
        }
    
    # Check if it's a sell message
    sell_match = SELL_PATTERN.match(text.strip())
    if sell_match:
        token_name, price, tx_hash = sell_match.groups()
        
        # Convert price to float
        price_float = float(price)
        
        return {
            'trade_type': 'sell',
            'token_name': token_name,
            'price': price_float,
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
            
            # Check trade type
            trade_type = details['trade_type'].lower()
            
            if trade_type == 'buy':
                # For buy transactions, just store the pending trade for future matching
                # Check if this transaction has already been processed
                existing = TradingPosition.query.filter_by(
                    buy_tx_hash=tx_hash
                ).first()
                
                if existing:
                    return False, f"This BUY transaction has already been processed", 0
                    
                # Create a new buy position (template for future matching)
                position = TradingPosition()
                position.user_id = 1  # Placeholder - will be updated when matched with SELL
                position.token_name = details['token_name']
                position.amount = 1.0  # Placeholder
                position.entry_price = details['price']
                position.current_price = details['price']
                position.timestamp = datetime.utcnow()
                position.status = 'open'
                position.trade_type = details['trade_subtype']
                position.buy_tx_hash = tx_hash
                position.buy_timestamp = datetime.utcnow()
                
                db.session.add(position)
                
                # Also create Buy transactions for all active users
                users = User.query.filter(User.balance > 0).all()
                update_count = 0
                
                for user in users:
                    try:
                        # Create a Buy transaction record
                        transaction = Transaction()
                        transaction.user_id = user.id
                        transaction.transaction_type = 'buy'
                        transaction.amount = user.balance * 0.1  # Use 10% of balance as placeholder amount
                        transaction.token_name = details['token_name']
                        transaction.price = details['price']
                        transaction.timestamp = datetime.utcnow()
                        transaction.notes = f"Buy ${details['token_name']} at ${details['price']:.6f}"
                        transaction.tx_hash = tx_hash
                        transaction.status = 'completed'
                        
                        db.session.add(transaction)
                        update_count += 1
                    except Exception as user_error:
                        logger.error(f"Error creating Buy transaction for user {user.id}: {str(user_error)}")
                        continue
                
                db.session.commit()
                
                return True, f"BUY order recorded for ${details['token_name']} at {details['price']} for {update_count} users", update_count
                
            elif trade_type == 'sell':
                # For sell transactions, match with a previous buy and apply profit/loss
                # Check if this transaction has already been processed
                existing = TradingPosition.query.filter_by(
                    sell_tx_hash=tx_hash
                ).first()
                
                if existing:
                    return False, f"This SELL transaction has already been processed", 0
                
                # Find a matching buy position
                buy_position = TradingPosition.query.filter_by(
                    token_name=details['token_name'],
                    status='open'
                ).order_by(TradingPosition.buy_timestamp.asc()).first()
                
                if not buy_position:
                    return False, f"No matching BUY order found for ${details['token_name']}", 0
                
                # Calculate ROI percentage
                entry_price = buy_position.entry_price
                exit_price = details['price']
                roi_percent = ((exit_price - entry_price) / entry_price) * 100
                
                # Update the buy position
                buy_position.current_price = exit_price
                buy_position.sell_tx_hash = tx_hash
                buy_position.sell_timestamp = datetime.utcnow()
                buy_position.status = 'closed'
                buy_position.roi_percentage = roi_percent
                
                # Get active users
                users = User.query.filter(User.balance > 0).all()
                if not users:
                    return False, "No active users found to process trade for", 0
                    
                # Convert ROI to decimal
                roi_decimal = roi_percent / 100
                
                # Apply trade to each user
                updated_count = 0
                
                for user in users:
                    try:
                        # Calculate profit amount based on user balance
                        profit_amount = user.balance * roi_decimal
                        
                        # Update user balance
                        previous_balance = user.balance
                        user.balance += profit_amount
                        
                        # Create a completed trade position for this user
                        position = TradingPosition()
                        position.user_id = user.id
                        position.token_name = details['token_name']
                        position.amount = abs(profit_amount / (exit_price - entry_price)) if exit_price != entry_price else 1.0
                        position.entry_price = entry_price
                        position.current_price = exit_price
                        position.timestamp = datetime.utcnow()
                        position.status = 'closed'
                        position.trade_type = buy_position.trade_type
                        position.buy_tx_hash = buy_position.buy_tx_hash
                        position.sell_tx_hash = tx_hash
                        position.buy_timestamp = buy_position.buy_timestamp
                        position.sell_timestamp = datetime.utcnow()
                        position.roi_percentage = roi_percent
                        position.paired_position_id = buy_position.id
                        
                        db.session.add(position)
                        
                        # Record transaction in the history
                        transaction = Transaction()
                        transaction.user_id = user.id
                        transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                        transaction.amount = profit_amount
                        transaction.token_name = details['token_name']
                        transaction.price = exit_price  # Store the token price
                        transaction.timestamp = datetime.utcnow()
                        # Use notes instead of description if that's what your model has
                        transaction.notes = f"${details['token_name']} trade: {roi_percent:.2f}% ROI"
                        transaction.tx_hash = tx_hash
                        transaction.status = 'completed'
                        
                        db.session.add(transaction)
                        
                        # Record profit separately for analytics
                        profit_record = Profit()
                        profit_record.user_id = user.id
                        profit_record.amount = profit_amount
                        # Set additional fields if your model has them
                        if hasattr(profit_record, 'roi_percentage'):
                            profit_record.roi_percentage = roi_percent
                        if hasattr(profit_record, 'timestamp'):
                            profit_record.timestamp = datetime.utcnow()
                        if hasattr(profit_record, 'source'):
                            profit_record.source = 'trading'
                        
                        db.session.add(profit_record)
                        
                        # Track the success
                        updated_count += 1
                        
                        logger.info(f"Applied trade profit to user {user.id}: ${profit_amount:.6f} ({roi_percent:.2f}%)")
                        
                    except Exception as user_error:
                        logger.error(f"Error applying trade to user {user.id}: {str(user_error)}")
                        logger.error(traceback.format_exc())
                        continue  # Skip this user but continue with others
                
                # Save all the changes
                db.session.commit()
                
                return True, f"Applied {details['token_name']} trade to {updated_count} users: {roi_percent:.2f}% ROI", updated_count
            
            else:
                return False, f"Unknown trade type: {trade_type}", 0
                
    except Exception as e:
        logger.error(f"Error processing trade broadcast: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error processing trade: {str(e)}", 0

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
        return False, "❌ Invalid trade format. Please use:\nBuy $TOKEN PRICE TX_LINK\nor\nSell $TOKEN PRICE TX_LINK"
    
    # Process the trade
    success, message, count = process_trade_broadcast(details)
    
    if success:
        # Format a nice success message
        if details['trade_type'].lower() == 'buy':
            return True, f"✅ {message}"
        else:
            return True, f"✅ {message}"
    else:
        return False, f"❌ {message}"

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
    if not bot:
        return 0
        
    sent_count = 0
    
    for user in users:
        try:
            # Skip users with no Telegram ID
            if not user.telegram_id:
                continue
                
            # Calculate user's profit
            profit = user.balance * (details['roi_percent'] / 100)
            
            # Format notification
            message = (
                f"🚀 *Trade Alert: ${details['token_name']}*\n\n"
                f"Buy: ${details['entry_price']:.6f}\n"
                f"Sell: ${details['exit_price']:.6f}\n"
                f"ROI: {details['roi_percent']:.2f}%\n\n"
                f"💰 Your profit: {profit:.6f} SOL\n"
                f"💵 New balance: {user.balance:.6f} SOL"
            )
            
            # Send the message
            bot.send_message(
                user.telegram_id,
                message,
                parse_mode="Markdown"
            )
            
            sent_count += 1
            
        except Exception as e:
            logger.error(f"Error sending notification to user {user.id}: {str(e)}")
            continue
            
    return sent_count