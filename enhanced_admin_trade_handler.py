"""
Enhanced Admin Trade Handler with Smart Balance Allocation
=========================================================
This integrates the smart balance allocation system with the existing admin trade commands,
replacing the simple broadcast with personalized, balance-based trade allocation.

Features:
- Parses "Buy $TOKEN PRICE AMOUNT TX_LINK" and "Sell $TOKEN PRICE AMOUNT TX_LINK" 
- Calculates unique spending amounts per user based on their balance
- Creates personalized position entries that feel authentic
- Sends customized notifications to users
"""

import re
import logging
from datetime import datetime
from smart_balance_allocator import (
    process_smart_buy_broadcast, 
    process_smart_sell_broadcast,
    generate_personalized_position_message
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_admin_trade_command(message_text):
    """
    Parse admin trade message in the enhanced format:
    Buy $TOKEN PRICE AMOUNT TX_LINK
    Sell $TOKEN PRICE AMOUNT TX_LINK
    
    Args:
        message_text (str): The admin message text
        
    Returns:
        dict: Parsed trade data or None if invalid
    """
    try:
        # Clean up the message
        message = message_text.strip()
        
        # Pattern to match: Buy/Sell $TOKEN PRICE AMOUNT TX_LINK
        pattern = r'(Buy|Sell)\s+\$(\w+)\s+([\d.]+)\s+([\d.]+)\s+(https?://[^\s]+)'
        
        match = re.match(pattern, message, re.IGNORECASE)
        
        if not match:
            # Try alternate pattern without https (just tx hash)
            pattern2 = r'(Buy|Sell)\s+\$(\w+)\s+([\d.]+)\s+([\d.]+)\s+(\w+)'
            match = re.match(pattern2, message, re.IGNORECASE)
            
            if match:
                tx_identifier = match.group(5)
                # If it's just a hash, create a solscan link
                if not tx_identifier.startswith('http'):
                    tx_link = f"https://solscan.io/tx/{tx_identifier}"
                else:
                    tx_link = tx_identifier
            else:
                return None
        else:
            tx_link = match.group(5)
        
        if not match:
            return None
            
        trade_type = match.group(1).lower()
        token_symbol = match.group(2).upper()
        price = float(match.group(3))
        amount = float(match.group(4))
        
        return {
            'trade_type': trade_type,
            'token_symbol': token_symbol,
            'price': price,
            'amount': amount,
            'tx_link': tx_link,
            'original_message': message_text
        }
        
    except Exception as e:
        logger.error(f"Error parsing trade command: {e}")
        return None


def handle_enhanced_admin_trade_message(update, chat_id, bot):
    """
    Process an enhanced admin trade message with smart balance allocation.
    
    Args:
        update (dict): Telegram update object
        chat_id (str): Chat ID to reply to
        bot: Telegram bot instance
        
    Returns:
        bool: True if the message was handled, False otherwise
    """
    try:
        # Get message text
        if 'message' in update and 'text' in update['message']:
            message_text = update['message']['text']
        elif 'callback_query' in update and 'message' in update['callback_query']:
            # Handle callback messages (if sent via admin panel)
            return False
        else:
            return False
        
        # Check if this looks like a trade command
        if not any(word in message_text.lower() for word in ['buy', 'sell']):
            return False
            
        if not '$' in message_text:
            return False
        
        # Parse the trade command
        trade_data = parse_admin_trade_command(message_text)
        
        if not trade_data:
            # Send format help if parsing failed
            help_message = (
                "❌ Invalid trade format detected!\n\n"
                "Use this format:\n"
                "`Buy $TOKEN PRICE AMOUNT TX_LINK`\n"
                "`Sell $TOKEN PRICE AMOUNT TX_LINK`\n\n"
                "Example:\n"
                "`Buy $ZING 0.004107 812345 https://solscan.io/tx/abc123`"
            )
            bot.send_message(chat_id, help_message, parse_mode="Markdown")
            return True
        
        # Send processing message
        processing_msg = bot.send_message(
            chat_id, 
            f"🔄 Processing {trade_data['trade_type'].upper()} command for ${trade_data['token_symbol']}..."
        )
        
        # Process the trade based on type
        if trade_data['trade_type'] == 'buy':
            success, message, affected_count, summary = process_smart_buy_broadcast(
                token_symbol=trade_data['token_symbol'],
                entry_price=trade_data['price'],
                admin_amount=trade_data['amount'],
                tx_link=trade_data['tx_link'],
                target_users="active"
            )
        else:  # sell
            success, message, affected_count, summary = process_smart_sell_broadcast(
                token_symbol=trade_data['token_symbol'],
                exit_price=trade_data['price'],
                admin_amount=trade_data['amount'],
                tx_link=trade_data['tx_link'],
                target_users="active"
            )
        
        # Delete processing message
        try:
            bot.delete_message(chat_id, processing_msg['message_id'])
        except:
            pass
        
        # Send result message
        if success:
            result_message = (
                f"✅ **Enhanced Trade Broadcast Complete**\n\n"
                f"**Command:** {trade_data['trade_type'].title()} ${trade_data['token_symbol']}\n"
                f"**Price:** {trade_data['price']:.8f}\n"
                f"**Users Affected:** {affected_count}\n\n"
                f"{message}\n\n"
                f"💡 Each user received a personalized trade amount based on their balance!"
            )
            
            # Add specific details based on trade type
            if trade_data['trade_type'] == 'buy' and 'conservative' in summary:
                result_message += f"\n\n📊 **Allocation Strategy Applied Successfully**"
            elif trade_data['trade_type'] == 'sell' and 'avg_profit_percent' in summary:
                result_message += f"\n\n📈 **Profit Distribution Complete**"
                
        else:
            result_message = f"❌ Failed to process trade: {message}"
        
        bot.send_message(chat_id, result_message, parse_mode="Markdown")
        
        # If successful, broadcast personalized notifications to users
        if success and affected_count > 0:
            broadcast_personalized_notifications(trade_data, bot)
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling enhanced admin trade message: {e}")
        error_message = f"❌ Error processing trade command: {str(e)}"
        bot.send_message(chat_id, error_message)
        return True


def broadcast_personalized_notifications(trade_data, bot):
    """
    Send personalized notifications to users about their new positions
    
    Args:
        trade_data (dict): Parsed trade data
        bot: Telegram bot instance
    """
    try:
        from app import app, db
        from models import User, TradingPosition, UserStatus
        from sqlalchemy import desc
        
        with app.app_context():
            # Get users who were affected by this trade
            recent_positions = TradingPosition.query.filter_by(
                token_name=trade_data['token_symbol']
            ).filter(
                TradingPosition.timestamp >= datetime.utcnow().replace(minute=datetime.utcnow().minute-1)  # Last minute
            ).all()
            
            notification_count = 0
            
            for position in recent_positions:
                try:
                    user = User.query.get(position.user_id)
                    
                    if not user or not user.telegram_id:
                        continue
                    
                    # Generate personalized message
                    message = generate_personalized_position_message(
                        user, 
                        position, 
                        trade_data['trade_type']
                    )
                    
                    # Send notification to user
                    bot.send_message(
                        user.telegram_id, 
                        message, 
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                    
                    notification_count += 1
                    
                except Exception as user_error:
                    logger.warning(f"Failed to notify user {position.user_id}: {user_error}")
                    continue
            
            logger.info(f"Sent {notification_count} personalized notifications for ${trade_data['token_symbol']} {trade_data['trade_type']}")
            
    except Exception as e:
        logger.error(f"Error broadcasting personalized notifications: {e}")


def add_enhanced_handler_to_bot():
    """
    Integration function to add the enhanced trade handler to the bot
    This replaces the existing simple trade broadcast with smart allocation
    """
    integration_code = '''
# Enhanced Admin Trade Handler Integration
from enhanced_admin_trade_handler import handle_enhanced_admin_trade_message

# Add this to your message handler in bot_v20_runner.py
def enhanced_message_handler(update, context):
    """Enhanced message handler that processes smart trade allocation"""
    try:
        chat_id = str(update.effective_chat.id)
        
        # Check if this is an admin trade message
        if handle_enhanced_admin_trade_message(update, chat_id, bot):
            return  # Message was handled
            
        # Continue with existing message handlers...
        
    except Exception as e:
        logger.error(f"Error in enhanced message handler: {e}")

# Add this handler to your application
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_message_handler))
'''
    
    print("Integration Code for bot_v20_runner.py:")
    print("=" * 50)
    print(integration_code)
    print("=" * 50)
    print("\nThis code should be added to your bot_v20_runner.py file to enable")
    print("smart balance allocation for admin trade commands.")


def test_enhanced_handler():
    """Test the enhanced handler with sample commands"""
    print("Testing Enhanced Admin Trade Handler")
    print("=" * 50)
    
    test_commands = [
        "Buy $ZING 0.004107 812345 https://solscan.io/tx/abc123",
        "Sell $ZING 0.006834 812345 https://solscan.io/tx/def456",
        "Buy $PEPE 0.000001 1000000 abc123",
        "Invalid command format"
    ]
    
    for command in test_commands:
        print(f"\nTesting: {command}")
        result = parse_admin_trade_command(command)
        if result:
            print(f"✅ Parsed successfully:")
            print(f"   Type: {result['trade_type']}")
            print(f"   Token: ${result['token_symbol']}")
            print(f"   Price: {result['price']}")
            print(f"   Amount: {result['amount']}")
            print(f"   TX: {result['tx_link']}")
        else:
            print("❌ Failed to parse")


if __name__ == "__main__":
    test_enhanced_handler()
    print("\n")
    add_enhanced_handler_to_bot()