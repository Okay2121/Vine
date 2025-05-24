"""
Simple Trade Message Handler
---------------------------
Handles admin trade messages in the format:
Buy $TOKEN PRICE TX_LINK or Sell $TOKEN PRICE TX_LINK
"""

import logging
import re
from datetime import datetime
import traceback
from sqlalchemy import desc, text
from app import app, db
from models import User, Transaction, TradingPosition

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def handle_trade_message(message_text, user_id, bot=None):
    """
    Process an admin trade message in the format:
    Buy $TOKEN PRICE TX_LINK or Sell $TOKEN PRICE TX_LINK
    
    Args:
        message_text (str): The message text containing the trade
        user_id (str): The user ID who sent the message
        bot: The Telegram bot instance (optional)
        
    Returns:
        tuple: (success, message, details)
            - success (bool): Whether the trade was successful
            - message (str): The response message
            - details (dict): Details about the trade if successful
    """
    if not message_text:
        return False, "❌ Empty message", None
    
    # Parse the message
    trade_type, token, price, tx_link = parse_trade_message(message_text)
    
    if not trade_type or not token or not price or not tx_link:
        return False, "❌ Invalid trade format. Use: Buy/Sell $TOKEN PRICE TX_LINK", None
    
    # Validate token name and price
    if not token.startswith('$'):
        token = f"${token}"
    
    try:
        price = float(price)
        if price <= 0:
            return False, "❌ Price must be greater than zero", None
    except ValueError:
        return False, f"❌ Invalid price: {price}", None
    
    # Process based on trade type
    with app.app_context():
        if trade_type.lower() == 'buy':
            return process_buy_trade(token, price, tx_link, user_id, bot)
        elif trade_type.lower() == 'sell':
            return process_sell_trade(token, price, tx_link, user_id, bot)
        else:
            return False, f"❌ Unknown trade type: {trade_type}", None

def parse_trade_message(message_text):
    """
    Parse a trade message into its components
    
    Args:
        message_text (str): Message in the format "Buy/Sell $TOKEN PRICE TX_LINK"
        
    Returns:
        tuple: (trade_type, token, price, tx_link)
    """
    # Check for correct format
    pattern = r'(buy|sell)\s+(\$?\w+)\s+([\d.]+)\s+(https?://\S+)'
    match = re.search(pattern, message_text.lower())
    
    if match:
        trade_type = match.group(1).capitalize()
        token = match.group(2)
        price = match.group(3)
        tx_link = match.group(4)
        return trade_type, token, price, tx_link
    
    return None, None, None, None

def process_buy_trade(token, price, tx_link, admin_id, bot=None):
    """
    Process a BUY trade
    
    Args:
        token (str): Token name (with $ prefix)
        price (float): Purchase price
        tx_link (str): Transaction link
        admin_id (str): Admin ID who sent the message
        bot: Telegram bot instance (optional)
        
    Returns:
        tuple: (success, message, details)
    """
    try:
        # Check if this transaction has already been processed
        existing_position = TradingPosition.query.filter_by(
            buy_tx_hash=tx_link,
            token_name=token
        ).first()
        
        if existing_position:
            return False, f"❌ This {token} BUY transaction has already been recorded (ID: {existing_position.id})", None
        
        # Create a new trading position
        position = TradingPosition()
        position.token_name = token
        position.entry_price = price
        position.buy_tx_hash = tx_link
        position.buy_timestamp = datetime.utcnow()
        position.admin_id = admin_id
        position.status = 'open'  # New position, waiting for SELL
        
        # Add to database and commit
        db.session.add(position)
        db.session.commit()
        
        # Format confirmation message
        message = (
            f"✅ *BUY* position recorded\n\n"
            f"*Token:* {token}\n"
            f"*Entry Price:* {price}\n"
            f"*TX:* [View Transaction]({tx_link})\n"
            f"*Position ID:* {position.id}\n"
            f"*Status:* Waiting for SELL"
        )
        
        details = {
            'trade_type': 'buy',
            'token': token,
            'price': price,
            'tx_link': tx_link,
            'position_id': position.id
        }
        
        return True, message, details
        
    except Exception as e:
        logger.error(f"Error processing BUY trade: {e}")
        logger.error(traceback.format_exc())
        return False, f"❌ Error processing trade: {str(e)}", None

def process_sell_trade(token, price, tx_link, admin_id, bot=None):
    """
    Process a SELL trade and match with a previous BUY
    
    Args:
        token (str): Token name (with $ prefix)
        price (float): Sell price
        tx_link (str): Transaction link
        admin_id (str): Admin ID who sent the message
        bot: Telegram bot instance (optional)
        
    Returns:
        tuple: (success, message, details)
    """
    try:
        # Check if this transaction has already been processed
        existing_position = TradingPosition.query.filter_by(
            sell_tx_hash=tx_link,
            token_name=token
        ).first()
        
        if existing_position:
            return False, f"❌ This {token} SELL transaction has already been recorded (ID: {existing_position.id})", None
        
        # Find the oldest open BUY position for this token
        buy_position = TradingPosition.query.filter_by(
            token_name=token,
            status='open'
        ).order_by(TradingPosition.buy_timestamp).first()
        
        if not buy_position:
            return False, f"❌ No open BUY position found for {token}", None
        
        # Update the BUY position with SELL details
        buy_position.exit_price = price
        buy_position.sell_tx_hash = tx_link
        buy_position.sell_timestamp = datetime.utcnow()
        buy_position.status = 'closed'
        
        # Calculate ROI
        entry_price = buy_position.entry_price
        exit_price = price
        roi_percentage = ((exit_price - entry_price) / entry_price) * 100
        buy_position.roi_percentage = roi_percentage
        
        # Update database
        db.session.commit()
        
        # Format confirmation message with ROI
        roi_display = f"+{roi_percentage:.2f}%" if roi_percentage >= 0 else f"{roi_percentage:.2f}%"
        roi_emoji = "📈" if roi_percentage >= 0 else "📉"
        
        message = (
            f"✅ *SELL* position matched\n\n"
            f"*Token:* {token}\n"
            f"*Entry Price:* {entry_price}\n"
            f"*Exit Price:* {exit_price}\n"
            f"*ROI:* {roi_emoji} {roi_display}\n"
            f"*TX:* [View Transaction]({tx_link})\n"
            f"*Position ID:* {buy_position.id}\n"
            f"*Status:* Closed"
        )
        
        details = {
            'trade_type': 'sell',
            'token': token,
            'price': price,
            'tx_link': tx_link,
            'position_id': buy_position.id,
            'entry_price': entry_price,
            'roi_percentage': roi_percentage
        }
        
        # Apply profit/loss to all users (run in the background)
        apply_trade_to_users(buy_position, roi_percentage, bot)
        
        return True, message, details
        
    except Exception as e:
        logger.error(f"Error processing SELL trade: {e}")
        logger.error(traceback.format_exc())
        return False, f"❌ Error processing trade: {str(e)}", None

def apply_trade_to_users(position, roi_percentage, bot=None):
    """
    Apply the trade profit/loss to all active users
    
    Args:
        position (TradingPosition): The completed trade position
        roi_percentage (float): The ROI percentage
        bot: Telegram bot instance (optional)
    """
    try:
        # Get all active users
        users = User.query.filter(User.balance > 0).all()
        
        for user in users:
            try:
                # Calculate profit/loss for this user
                user_profit = (user.balance * roi_percentage) / 100
                
                # Skip very small profits/losses
                if abs(user_profit) < 0.000001:
                    continue
                
                # Update user balance using direct SQL for reliability
                original_balance = user.balance
                
                # Use direct SQL update to ensure reliable balance updates
                sql = text("UPDATE user SET balance = balance + :amount WHERE id = :user_id")
                db.session.execute(sql, {"amount": user_profit, "user_id": user.id})
                
                # Create transaction record
                transaction = Transaction()
                transaction.user_id = user.id
                transaction.transaction_type = 'trade_profit' if user_profit >= 0 else 'trade_loss'
                transaction.amount = abs(user_profit)
                transaction.token_name = "SOL"
                transaction.timestamp = datetime.utcnow()
                transaction.status = 'completed'
                transaction.notes = f"Trade {position.token_name} - ROI: {roi_percentage:.2f}%"
                transaction.related_trade_id = position.id
                
                # Add to database
                db.session.add(transaction)
                
                # Notify user if bot is provided
                if bot and user.telegram_id:
                    try:
                        action = "added to" if user_profit >= 0 else "deducted from"
                        emoji = "📈" if user_profit >= 0 else "📉"
                        
                        notification = (
                            f"{emoji} *Trade Completed*\n\n"
                            f"*Token:* {position.token_name}\n"
                            f"*ROI:* {roi_percentage:.2f}%\n"
                            f"*Impact:* {abs(user_profit):.6f} SOL {action} your balance\n"
                            f"*Previous Balance:* {original_balance:.6f} SOL\n"
                            f"*New Balance:* {user.balance:.6f} SOL"
                        )
                        
                        bot.send_message(
                            user.telegram_id,
                            notification,
                            parse_mode="Markdown"
                        )
                    except Exception as notify_error:
                        logger.error(f"Error notifying user {user.id}: {notify_error}")
                
            except Exception as user_error:
                logger.error(f"Error processing trade for user {user.id}: {user_error}")
                continue
        
        # Commit all changes
        db.session.commit()
        logger.info(f"Trade applied to {len(users)} users. Token: {position.token_name}, ROI: {roi_percentage:.2f}%")
        
    except Exception as e:
        logger.error(f"Error applying trade to users: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback()

# Testing function
def test_trade_handler():
    """Test the trade handler with sample messages"""
    test_messages = [
        "Buy $SOL 123.45 https://solscan.io/tx/abc123",
        "Sell $SOL 150.00 https://solscan.io/tx/def456",
        "Buy $MEME 0.0041 https://solscan.io/tx/ghi789",
        "Sell $MEME 0.0065 https://solscan.io/tx/jkl012",
        "Invalid message"
    ]
    
    for msg in test_messages:
        success, response, details = handle_trade_message(msg, "12345")
        print(f"\nMessage: {msg}")
        print(f"Success: {success}")
        print(f"Response: {response}")
        print(f"Details: {details}")

if __name__ == "__main__":
    test_trade_handler()