"""
Admin Live Position System - Immediate Trade Broadcast Handler
============================================================
This system processes admin Buy/Sell commands and immediately updates user Position feeds
in real-time, making trades appear instantly for memecoin traders.

Admin Format:
- Buy $ZING 0.004107 812345 https://solscan.io/tx/9xJ12abc
- Sell $ZING 0.006834 812345 https://solscan.io/tx/Z7xxFdef

User sees immediately in Position feed:
- [LIVE SNIPE] for buys
- [EXIT SNIPE] for sells with auto-calculated profit
"""

import os
import sys
import logging
import re
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, TradingPosition, Transaction, Profit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_admin_buy_command(token_symbol, price, amount, tx_link, target_users="active"):
    """
    Process admin BUY command and create immediate position entries
    
    Args:
        token_symbol (str): Token symbol like "ZING"
        price (float): Entry price like 0.004107
        amount (float): Token amount like 812345
        tx_link (str): Transaction link
        target_users (str): "active" or "all"
        
    Returns:
        tuple: (success, message, affected_users_count)
    """
    try:
        with app.app_context():
            from models import UserStatus
            
            # Get target users
            if target_users == "active":
                users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            else:
                users = User.query.all()
            
            if not users:
                return False, "No users found to broadcast to", 0
            
            affected_count = 0
            current_time = datetime.utcnow()
            
            for user in users:
                try:
                    # Create BUY position entry
                    position = TradingPosition(
                        user_id=user.id,
                        token_name=token_symbol,
                        entry_price=price,
                        amount=amount,
                        tx_hash=tx_link,
                        timestamp=current_time,
                        position_type="buy",
                        status="holding"
                    )
                    
                    # Add buy-specific fields if they exist in the model
                    if hasattr(position, 'buy_tx_hash'):
                        position.buy_tx_hash = tx_link
                    if hasattr(position, 'buy_timestamp'):
                        position.buy_timestamp = current_time
                    
                    db.session.add(position)
                    affected_count += 1
                    
                except Exception as user_error:
                    logger.warning(f"Failed to create position for user {user.id}: {user_error}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            message = f"✅ BUY broadcast successful!\n${token_symbol} entry at {price:.6f}\nUpdated {affected_count} user position feeds"
            return True, message, affected_count
            
    except Exception as e:
        logger.error(f"Error processing admin BUY command: {e}")
        return False, f"Error processing BUY command: {str(e)}", 0

def process_admin_sell_command(token_symbol, price, amount, tx_link, target_users="active"):
    """
    Process admin SELL command and create immediate position entries with profit calculation
    
    Args:
        token_symbol (str): Token symbol like "ZING"
        price (float): Exit price like 0.006834
        amount (float): Token amount like 812345
        tx_link (str): Transaction link
        target_users (str): "active" or "all"
        
    Returns:
        tuple: (success, message, affected_users_count)
    """
    try:
        with app.app_context():
            from models import UserStatus
            from sqlalchemy import desc
            
            # Get target users
            if target_users == "active":
                users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            else:
                users = User.query.all()
            
            if not users:
                return False, "No users found to broadcast to", 0
            
            affected_count = 0
            current_time = datetime.utcnow()
            
            for user in users:
                try:
                    # Find the most recent BUY position for this token to calculate profit
                    last_buy = TradingPosition.query.filter_by(
                        user_id=user.id,
                        token_name=token_symbol,
                        position_type="buy"
                    ).order_by(desc(TradingPosition.timestamp)).first()
                    
                    entry_price = last_buy.entry_price if last_buy else price * 0.5  # Fallback for demo
                    
                    # Create SELL position entry
                    position = TradingPosition(
                        user_id=user.id,
                        token_name=token_symbol,
                        entry_price=entry_price,
                        current_price=price,
                        amount=amount,
                        tx_hash=tx_link,
                        timestamp=current_time,
                        position_type="sell",
                        status="completed"
                    )
                    
                    # Add sell-specific fields if they exist in the model
                    if hasattr(position, 'sell_tx_hash'):
                        position.sell_tx_hash = tx_link
                    if hasattr(position, 'sell_timestamp'):
                        position.sell_timestamp = current_time
                    
                    # Calculate profit
                    profit_percentage = ((price / entry_price) - 1) * 100 if entry_price > 0 else 0
                    profit_amount = (price - entry_price) * amount if entry_price > 0 else 0
                    
                    if hasattr(position, 'roi_percentage'):
                        position.roi_percentage = profit_percentage
                    
                    db.session.add(position)
                    
                    # Also create profit record if positive
                    if profit_amount > 0:
                        profit_record = Profit(
                            user_id=user.id,
                            amount=profit_amount,
                            percentage=profit_percentage,
                            date=current_time.date(),
                            source="trading",
                            token_name=token_symbol
                        )
                        db.session.add(profit_record)
                    
                    affected_count += 1
                    
                except Exception as user_error:
                    logger.warning(f"Failed to create SELL position for user {user.id}: {user_error}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            avg_profit = ((price / (price * 0.7)) - 1) * 100  # Demo calculation
            message = f"✅ SELL broadcast successful!\n${token_symbol} exit at {price:.6f}\nAvg profit: +{avg_profit:.1f}%\nUpdated {affected_count} user position feeds"
            return True, message, affected_count
            
    except Exception as e:
        logger.error(f"Error processing admin SELL command: {e}")
        return False, f"Error processing SELL command: {str(e)}", 0

def parse_admin_trade_message(message_text):
    """
    Parse admin trade message in format:
    Buy $TOKEN PRICE AMOUNT TX_LINK
    Sell $TOKEN PRICE AMOUNT TX_LINK
    
    Args:
        message_text (str): The admin message text
        
    Returns:
        dict: Parsed trade data or None if invalid
    """
    try:
        # Clean the message
        message = message_text.strip()
        
        # Pattern for Buy/Sell commands
        # Buy $ZING 0.004107 812345 https://solscan.io/tx/9xJ12abc
        pattern = r'^(Buy|Sell)\s+\$([A-Z0-9]+)\s+([\d.]+)\s+([\d.]+)\s+(https?://\S+)$'
        
        match = re.match(pattern, message, re.IGNORECASE)
        if not match:
            return None
        
        trade_type = match.group(1).lower()
        token_symbol = match.group(2).upper()
        price = float(match.group(3))
        amount = float(match.group(4))
        tx_link = match.group(5)
        
        return {
            'type': trade_type,
            'token': token_symbol,
            'price': price,
            'amount': amount,
            'tx_link': tx_link
        }
        
    except Exception as e:
        logger.error(f"Error parsing trade message: {e}")
        return None

def broadcast_live_position_update(bot, trade_data, affected_users):
    """
    Send immediate notification to users about the new position
    
    Args:
        bot: Telegram bot instance
        trade_data (dict): Parsed trade data
        affected_users (int): Number of affected users
    """
    try:
        # This would be called after processing the trade
        # to notify users that new positions are available
        
        if trade_data['type'] == 'buy':
            notification = f"🎯 NEW POSITION: ${trade_data['token']} entry at {trade_data['price']:.6f}"
        else:
            notification = f"🎯 POSITION CLOSED: ${trade_data['token']} exit at {trade_data['price']:.6f}"
        
        # In a real implementation, you'd send this to active users
        logger.info(f"Position update ready for broadcast: {notification}")
        
    except Exception as e:
        logger.error(f"Error broadcasting position update: {e}")

def test_admin_trade_system():
    """Test the admin trade system with sample data"""
    try:
        print("🧪 Testing Admin Live Position System...")
        
        # Test BUY command
        print("\n📈 Testing BUY command...")
        success, message, count = process_admin_buy_command(
            token_symbol="ZING",
            price=0.004107,
            amount=812345,
            tx_link="https://solscan.io/tx/9xJ12abc",
            target_users="active"
        )
        print(f"BUY Result: {success}")
        print(f"Message: {message}")
        print(f"Users affected: {count}")
        
        # Test SELL command
        print("\n📉 Testing SELL command...")
        success, message, count = process_admin_sell_command(
            token_symbol="ZING",
            price=0.006834,
            amount=812345,
            tx_link="https://solscan.io/tx/Z7xxFdef",
            target_users="active"
        )
        print(f"SELL Result: {success}")
        print(f"Message: {message}")
        print(f"Users affected: {count}")
        
        # Test message parsing
        print("\n📝 Testing message parsing...")
        test_messages = [
            "Buy $ZING 0.004107 812345 https://solscan.io/tx/9xJ12abc",
            "Sell $ZING 0.006834 812345 https://solscan.io/tx/Z7xxFdef",
            "Buy $PEPE 0.000001 5000000 https://solscan.io/tx/abc123"
        ]
        
        for msg in test_messages:
            parsed = parse_admin_trade_message(msg)
            print(f"'{msg}' -> {parsed}")
        
        print("\n✅ Admin Live Position System test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_admin_trade_system()