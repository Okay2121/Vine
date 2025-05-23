"""
Simple Trade Handler for Admin Messages
----------------------------------------
This module implements a simple handler for admin trade messages
with the format: Buy/Sell $TOKEN PRICE TX_LINK
"""

import logging
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, Profit

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def extract_trade_details(text):
    """
    Extract trade details from a message with format:
    Buy/Sell $TOKEN PRICE TX_LINK
    
    Args:
        text (str): The message text
        
    Returns:
        dict: Trade details or None if format is invalid
    """
    # Clean and normalize the text
    if not text:
        return None
        
    parts = text.strip().split()
    if len(parts) < 4:
        return None
        
    # Extract components
    trade_type = parts[0].lower()
    if trade_type not in ['buy', 'sell']:
        return None
        
    token = parts[1]
    # Ensure token starts with $
    if not token.startswith('$'):
        return None
        
    # Try to parse price
    try:
        price = float(parts[2])
    except ValueError:
        return None
        
    # Extract transaction link (can contain multiple parts if URL has parameters)
    tx_link = ' '.join(parts[3:])
    
    return {
        'trade_type': trade_type,
        'token': token,
        'price': price,
        'tx_link': tx_link
    }

def process_buy_trade(token, price, tx_link, admin_id=None):
    """
    Process a BUY trade
    
    Args:
        token (str): Token name with $ prefix
        price (float): Entry price
        tx_link (str): Transaction link
        admin_id (str, optional): Admin ID who initiated the trade
        
    Returns:
        tuple: (success, message, position object or None)
    """
    try:
        with app.app_context():
            # Clean token name (remove $ if needed for db storage)
            clean_token = token.replace('$', '')
            
            # Extract tx hash from link if it's a URL
            tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
            
            # Check if this transaction was already processed
            existing = TradingPosition.query.filter_by(buy_tx_hash=tx_hash).first()
            if existing:
                return (False, f"This transaction was already processed for {existing.token_name}", None)
            
            # Create a new position
            position = TradingPosition()
            position.user_id = 1  # Placeholder - will link to specific users on SELL
            position.token_name = clean_token
            position.amount = 1.0  # Placeholder amount
            position.entry_price = price
            position.current_price = price
            position.timestamp = datetime.utcnow()
            position.status = 'open'
            position.trade_type = 'scalp'  # Default trade type
            position.buy_tx_hash = tx_hash
            position.buy_timestamp = datetime.utcnow()
            
            db.session.add(position)
            db.session.commit()
            
            logger.info(f"Recorded BUY position for {token} at {price}")
            return (True, f"BUY position for {token} at {price} recorded successfully", position)
    except Exception as e:
        logger.error(f"Error processing BUY trade: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return (False, f"Error processing BUY trade: {str(e)}", None)

def process_sell_trade(token, price, tx_link, admin_id=None):
    """
    Process a SELL trade and match with previous BUY
    
    Args:
        token (str): Token name with $ prefix
        price (float): Exit price
        tx_link (str): Transaction link
        admin_id (str, optional): Admin ID who initiated the trade
        
    Returns:
        tuple: (success, message, matched position, roi percentage)
    """
    try:
        with app.app_context():
            # Clean token name (remove $ if needed for db storage)
            clean_token = token.replace('$', '')
            
            # Extract tx hash from link if it's a URL
            tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
            
            # Check if this transaction was already processed
            existing = TradingPosition.query.filter_by(sell_tx_hash=tx_hash).first()
            if existing:
                return (False, f"This SELL transaction was already processed", None, 0)
            
            # Find the matching BUY position
            position = TradingPosition.query.filter_by(
                token_name=clean_token,
                status='open'
            ).order_by(TradingPosition.buy_timestamp.asc()).first()
            
            if not position:
                return (False, f"No open BUY position found for {token}", None, 0)
            
            # Calculate ROI
            roi_percentage = ((price - position.entry_price) / position.entry_price) * 100
            
            # Update the position
            position.current_price = price
            position.status = 'closed'
            position.sell_tx_hash = tx_hash
            position.sell_timestamp = datetime.utcnow()
            position.roi_percentage = roi_percentage
            
            db.session.commit()
            
            logger.info(f"Processed SELL for {token} at {price}, ROI: {roi_percentage:.2f}%")
            return (True, f"SELL processed for {token}, ROI: {roi_percentage:.2f}%", position, roi_percentage)
    except Exception as e:
        logger.error(f"Error processing SELL trade: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return (False, f"Error processing SELL trade: {str(e)}", None, 0)

def apply_trade_profit_to_users(position, bot=None):
    """
    Apply the profit from a closed trade to all active users
    
    Args:
        position (TradingPosition): The closed trade position
        bot: Optional bot instance for sending notifications
        
    Returns:
        tuple: (success, message, number of users updated)
    """
    try:
        with app.app_context():
            # Get all active users with positive balance
            users = User.query.filter(User.balance > 0).all()
            
            if not users:
                return (False, "No active users found to apply profit to", 0)
            
            # Calculate ROI percentage and convert to decimal
            roi_decimal = position.roi_percentage / 100
            
            # Apply profit to each user
            updated_count = 0
            for user in users:
                try:
                    # Calculate profit amount for this user
                    profit_amount = user.balance * roi_decimal
                    
                    # Update user balance
                    old_balance = user.balance
                    user.balance += profit_amount
                    
                    # Create transaction record
                    transaction = Transaction()
                    transaction.user_id = user.id
                    transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                    transaction.amount = profit_amount
                    transaction.token_name = position.token_name
                    transaction.status = 'completed'
                    transaction.notes = f"Trade ROI: {position.roi_percentage:.2f}% for {position.token_name}"
                    transaction.tx_hash = position.sell_tx_hash
                    transaction.processed_at = datetime.utcnow()
                    
                    # Create a user-specific trading position record
                    user_position = TradingPosition()
                    user_position.user_id = user.id
                    user_position.token_name = position.token_name
                    user_position.amount = abs(profit_amount / (position.current_price - position.entry_price)) if position.current_price != position.entry_price else 1.0
                    user_position.entry_price = position.entry_price
                    user_position.current_price = position.current_price
                    user_position.timestamp = datetime.utcnow()
                    user_position.status = 'closed'
                    user_position.trade_type = position.trade_type if position.trade_type else 'scalp'
                    user_position.buy_tx_hash = position.buy_tx_hash
                    user_position.sell_tx_hash = position.sell_tx_hash
                    user_position.buy_timestamp = position.buy_timestamp
                    user_position.sell_timestamp = position.sell_timestamp
                    user_position.roi_percentage = position.roi_percentage
                    user_position.paired_position_id = position.id
                    
                    # Add profit record
                    profit_record = Profit()
                    profit_record.user_id = user.id
                    profit_record.amount = profit_amount
                    profit_record.percentage = position.roi_percentage
                    profit_record.date = datetime.utcnow().date()
                    
                    db.session.add(transaction)
                    db.session.add(user_position)
                    db.session.add(profit_record)
                    
                    # Send notification to user if bot is provided
                    if bot and user.telegram_id:
                        try:
                            emoji = "📈" if position.roi_percentage >= 0 else "📉"
                            message = (
                                f"{emoji} *Trade Alert*\n\n"
                                f"• *Token:* {position.token_name}\n"
                                f"• *Entry:* {position.entry_price:.8f}\n"
                                f"• *Exit:* {position.current_price:.8f}\n"
                                f"• *ROI:* {position.roi_percentage:.2f}%\n"
                                f"• *Your Profit:* {profit_amount:.4f} SOL\n"
                                f"• *New Balance:* {user.balance:.4f} SOL\n\n"
                                f"_Your dashboard has been updated with this trade._"
                            )
                            bot.send_message(user.telegram_id, message, parse_mode="Markdown")
                        except Exception as notify_error:
                            logger.error(f"Error notifying user {user.id}: {str(notify_error)}")
                    
                    updated_count += 1
                except Exception as user_error:
                    logger.error(f"Error applying profit to user {user.id}: {str(user_error)}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            return (True, f"Applied profit to {updated_count} users", updated_count)
    except Exception as e:
        logger.error(f"Error applying trade profit: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.session.rollback()
        return (False, f"Error applying trade profit: {str(e)}", 0)

def handle_trade_message(message_text, admin_id=None, bot=None):
    """
    Process a trade message and execute the appropriate actions
    
    Args:
        message_text (str): Message text with the trade details
        admin_id (str, optional): Admin ID who sent the message
        bot: Optional bot instance for sending notifications
        
    Returns:
        tuple: (success, response_message, details_dict)
    """
    # Extract trade details
    details = extract_trade_details(message_text)
    if not details:
        return (False, "Invalid trade format. Expected: Buy/Sell $TOKEN PRICE TX_LINK", None)
    
    # Process based on trade type
    if details['trade_type'] == 'buy':
        success, message, position = process_buy_trade(
            details['token'], 
            details['price'], 
            details['tx_link'],
            admin_id
        )
        
        if success:
            response = (
                f"✅ *BUY Order Recorded*\n\n"
                f"• *Token:* {details['token']}\n"
                f"• *Entry Price:* {details['price']}\n"
                f"• *Transaction:* [View on Explorer]({details['tx_link']})\n"
                f"• *Timestamp:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"_This BUY will be matched with a future SELL order._"
            )
        else:
            response = f"⚠️ *Error Recording BUY*\n\n{message}"
            
        return (success, response, {
            'trade_type': 'buy',
            'token': details['token'],
            'price': details['price'],
            'position_id': position.id if position else None
        })
    
    elif details['trade_type'] == 'sell':
        success, message, position, roi = process_sell_trade(
            details['token'],
            details['price'],
            details['tx_link'],
            admin_id
        )
        
        if success and position:
            # Apply profit to all active users
            apply_success, apply_message, user_count = apply_trade_profit_to_users(position, bot)
            
            if apply_success:
                response = (
                    f"✅ *SELL Order Processed*\n\n"
                    f"• *Token:* {details['token']}\n"
                    f"• *Exit Price:* {details['price']}\n"
                    f"• *Entry Price:* {position.entry_price}\n"
                    f"• *ROI:* {roi:.2f}%\n"
                    f"• *Users Updated:* {user_count}\n"
                    f"• *Transaction:* [View on Explorer]({details['tx_link']})\n\n"
                    f"_Trade profit has been applied to all active users._"
                )
            else:
                response = (
                    f"⚠️ *SELL Processed with Warnings*\n\n"
                    f"• *Token:* {details['token']}\n"
                    f"• *Exit Price:* {details['price']}\n"
                    f"• *ROI:* {roi:.2f}%\n"
                    f"• *Warning:* {apply_message}\n\n"
                    f"_Please check user accounts manually._"
                )
        else:
            response = f"⚠️ *Error Processing SELL*\n\n{message}"
            
        return (success, response, {
            'trade_type': 'sell',
            'token': details['token'],
            'price': details['price'],
            'roi_percentage': roi if success else 0,
            'position_id': position.id if position else None
        })
    
    return (False, "Unknown trade type", None)