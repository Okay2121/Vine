"""
Enhanced Trade Broadcast System
------------------------------
Creates immediate transaction records for both BUY and SELL trades
to make trading activity look realistic and authentic in user histories.
"""

import re
import logging
import traceback
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, Profit
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pattern to match trade broadcast format
BUY_PATTERN = re.compile(r'^Buy\s+\$([A-Z0-9_]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)
SELL_PATTERN = re.compile(r'^Sell\s+\$([A-Z0-9_]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)

def extract_tx_hash(tx_link):
    """Extract transaction hash from Solscan or other blockchain explorer links"""
    if 'solscan.io/tx/' in tx_link:
        return tx_link.split('/tx/')[-1]
    elif 'explorer.solana.com/tx/' in tx_link:
        return tx_link.split('/tx/')[-1].split('?')[0]
    else:
        # Use last part of URL as hash
        return tx_link.split('/')[-1].split('?')[0]

def create_immediate_buy_records(token_name, entry_price, tx_hash, admin_id):
    """Create immediate BUY transaction records for all users with positive balances"""
    try:
        with app.app_context():
            # Get all users with positive balances
            users = User.query.filter(User.balance > 0).all()
            
            created_count = 0
            total_investment = 0
            
            for user in users:
                try:
                    # Calculate investment amount (user's balance represents their trading capital)
                    investment_amount = user.balance
                    tokens_bought = investment_amount / entry_price
                    
                    # Create trading position record
                    position = TradingPosition(
                        user_id=user.id,
                        token_name=token_name,
                        amount=tokens_bought,
                        entry_price=entry_price,
                        current_price=entry_price,
                        timestamp=datetime.utcnow(),
                        status='open',
                        trade_type='buy',
                        buy_tx_hash=tx_hash,
                        buy_timestamp=datetime.utcnow(),
                        admin_id=admin_id
                    )
                    db.session.add(position)
                    
                    # Create immediate transaction record for BUY
                    transaction = Transaction(
                        user_id=user.id,
                        transaction_type='trade_buy',  # Use consistent transaction type
                        amount=investment_amount,
                        token_name=token_name,
                        timestamp=datetime.utcnow(),
                        status='completed',
                        notes=f'BUY Order: {tokens_bought:.6f} {token_name} @ ${entry_price}',
                        tx_hash=f"{tx_hash}_buy_{user.id}_{int(datetime.utcnow().timestamp())}"
                    )
                    db.session.add(transaction)
                    
                    total_investment += investment_amount
                    created_count += 1
                    
                except Exception as e:
                    logger.error(f"Error creating BUY record for user {user.id}: {e}")
                    continue
            
            db.session.commit()
            
            return {
                'success': True,
                'users_count': created_count,
                'total_investment': total_investment,
                'token_name': token_name,
                'entry_price': entry_price,
                'tx_hash': tx_hash
            }
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating immediate BUY records: {e}")
        return {'success': False, 'error': str(e)}

def create_immediate_sell_records(token_name, exit_price, tx_hash, admin_id):
    """Create immediate SELL transaction records and calculate profits"""
    try:
        with app.app_context():
            # Find all open positions for this token
            positions = TradingPosition.query.filter_by(
                token_name=token_name,
                status='open'
            ).all()
            
            if not positions:
                return {
                    'success': False,
                    'error': f'No open positions found for {token_name}'
                }
            
            updated_count = 0
            total_profit = 0
            roi_percentage = 0
            
            for position in positions:
                try:
                    # Calculate ROI
                    roi_percentage = ((exit_price - position.entry_price) / position.entry_price) * 100
                    profit_amount = position.amount * (exit_price - position.entry_price)
                    
                    # Update the position to closed
                    position.status = 'closed'
                    position.exit_price = exit_price
                    position.current_price = exit_price
                    position.sell_tx_hash = tx_hash
                    position.sell_timestamp = datetime.utcnow()
                    position.roi_percentage = roi_percentage
                    
                    user = User.query.get(position.user_id)
                    if user:
                        # Update user balance with profit/loss
                        previous_balance = user.balance
                        user.balance += profit_amount
                        
                        # Create immediate SELL transaction record
                        if profit_amount >= 0:
                            transaction_type = 'trade_profit'
                            amount = profit_amount
                        else:
                            transaction_type = 'trade_loss'
                            amount = abs(profit_amount)
                        
                        transaction = Transaction(
                            user_id=user.id,
                            transaction_type=transaction_type,
                            amount=amount,
                            token_name=token_name,
                            timestamp=datetime.utcnow(),
                            status='completed',
                            notes=f'SELL Order: {position.amount:.6f} {token_name} @ ${exit_price} (ROI: {roi_percentage:.2f}%)',
                            tx_hash=f"{tx_hash}_sell_{user.id}_{int(datetime.utcnow().timestamp())}"
                        )
                        db.session.add(transaction)
                        
                        # Create profit record
                        profit_record = Profit(
                            user_id=user.id,
                            amount=profit_amount,
                            roi_percentage=roi_percentage,
                            timestamp=datetime.utcnow(),
                            source=f'{token_name} Trade'
                        )
                        db.session.add(profit_record)
                        
                        total_profit += profit_amount
                        updated_count += 1
                        
                        logger.info(f"User {user.id}: {token_name} trade completed - ROI: {roi_percentage:.2f}%, Profit: ${profit_amount:.6f}")
                    
                except Exception as e:
                    logger.error(f"Error processing SELL for position {position.id}: {e}")
                    continue
            
            db.session.commit()
            
            return {
                'success': True,
                'positions_closed': updated_count,
                'total_profit': total_profit,
                'roi_percentage': roi_percentage,
                'token_name': token_name,
                'exit_price': exit_price,
                'tx_hash': tx_hash
            }
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating immediate SELL records: {e}")
        return {'success': False, 'error': str(e)}

def handle_enhanced_trade_broadcast(text, bot, chat_id, admin_id):
    """
    Enhanced trade broadcast handler that creates immediate transaction records
    """
    try:
        # Check for BUY pattern
        buy_match = BUY_PATTERN.match(text.strip())
        if buy_match:
            token_name, price_str, tx_link = buy_match.groups()
            entry_price = float(price_str)
            tx_hash = extract_tx_hash(tx_link)
            
            logger.info(f"Processing BUY: {token_name} @ ${entry_price}")
            
            # Create immediate BUY records
            result = create_immediate_buy_records(token_name, entry_price, tx_hash, admin_id)
            
            if result['success']:
                response = (
                    f"✅ *BUY Order Executed*\n\n"
                    f"🎯 *Token:* {token_name}\n"
                    f"💰 *Entry Price:* ${entry_price}\n"
                    f"👥 *Users Invested:* {result['users_count']}\n"
                    f"💵 *Total Investment:* ${result['total_investment']:.2f}\n"
                    f"🔗 *Transaction:* [View on Solscan]({tx_link})\n\n"
                    f"📊 *Status:* Position opened for all users\n"
                    f"⏰ *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                    f"*All users can now see this BUY transaction in their trading history.*"
                )
                
                # Broadcast to all users
                broadcast_buy_to_users(result, bot)
                
                return True, response
            else:
                return False, f"❌ Error processing BUY: {result.get('error', 'Unknown error')}"
        
        # Check for SELL pattern
        sell_match = SELL_PATTERN.match(text.strip())
        if sell_match:
            token_name, price_str, tx_link = sell_match.groups()
            exit_price = float(price_str)
            tx_hash = extract_tx_hash(tx_link)
            
            logger.info(f"Processing SELL: {token_name} @ ${exit_price}")
            
            # Create immediate SELL records
            result = create_immediate_sell_records(token_name, exit_price, tx_hash, admin_id)
            
            if result['success']:
                profit_loss = "Profit" if result['total_profit'] >= 0 else "Loss"
                response = (
                    f"✅ *SELL Order Executed*\n\n"
                    f"🎯 *Token:* {token_name}\n"
                    f"💰 *Exit Price:* ${exit_price}\n"
                    f"📈 *ROI:* {result['roi_percentage']:.2f}%\n"
                    f"👥 *Positions Closed:* {result['positions_closed']}\n"
                    f"💵 *Total {profit_loss}:* ${abs(result['total_profit']):.2f}\n"
                    f"🔗 *Transaction:* [View on Solscan]({tx_link})\n\n"
                    f"📊 *Status:* All positions closed and profits distributed\n"
                    f"⏰ *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                    f"*All users can now see this SELL transaction and their updated balances.*"
                )
                
                # Broadcast to all affected users
                broadcast_sell_to_users(result, bot)
                
                return True, response
            else:
                return False, f"❌ Error processing SELL: {result.get('error', 'Unknown error')}"
        
        # Invalid format
        return False, (
            "❌ *Invalid Trade Format*\n\n"
            "Please use one of these formats:\n"
            "• `Buy $TOKEN PRICE TX_LINK`\n"
            "• `Sell $TOKEN PRICE TX_LINK`\n\n"
            "Example:\n"
            "`Buy $ZING 0.0041 https://solscan.io/tx/abc123`"
        )
        
    except ValueError:
        return False, "❌ Invalid price format. Please use a valid number."
    except Exception as e:
        logger.error(f"Error in enhanced trade broadcast: {e}")
        logger.error(traceback.format_exc())
        return False, f"❌ Error processing trade: {str(e)}"

def broadcast_buy_to_users(result, bot):
    """Send BUY notification to all affected users"""
    try:
        with app.app_context():
            users = User.query.filter(User.balance > 0).all()
            
            for user in users:
                try:
                    if user.telegram_id:
                        message = (
                            f"📈 *New Position Opened*\n\n"
                            f"🎯 *Token:* {result['token_name']}\n"
                            f"💰 *Entry Price:* ${result['entry_price']}\n"
                            f"📊 *Status:* BUY order executed\n"
                            f"💼 *Your Investment:* ${user.balance:.2f}\n\n"
                            f"*Check your trading history for details!*"
                        )
                        
                        bot.send_message(user.telegram_id, message, parse_mode="Markdown")
                
                except Exception as e:
                    logger.error(f"Error sending BUY notification to user {user.id}: {e}")
                    continue
    
    except Exception as e:
        logger.error(f"Error broadcasting BUY to users: {e}")

def broadcast_sell_to_users(result, bot):
    """Send SELL notification to all affected users"""
    try:
        with app.app_context():
            # Get users who had positions in this token
            user_ids = db.session.query(TradingPosition.user_id).filter_by(
                token_name=result['token_name'],
                status='closed'
            ).distinct().all()
            
            for (user_id,) in user_ids:
                try:
                    user = User.query.get(user_id)
                    if user and user.telegram_id:
                        profit_loss = "Profit" if result['total_profit'] >= 0 else "Loss"
                        emoji = "🎉" if result['total_profit'] >= 0 else "📉"
                        
                        message = (
                            f"{emoji} *Position Closed*\n\n"
                            f"🎯 *Token:* {result['token_name']}\n"
                            f"💰 *Exit Price:* ${result['exit_price']}\n"
                            f"📈 *ROI:* {result['roi_percentage']:.2f}%\n"
                            f"💵 *Your {profit_loss}:* ${abs(result['total_profit'] / result['positions_closed']):.2f}\n"
                            f"💼 *Updated Balance:* ${user.balance:.2f}\n\n"
                            f"*Check your trading history for full details!*"
                        )
                        
                        bot.send_message(user.telegram_id, message, parse_mode="Markdown")
                
                except Exception as e:
                    logger.error(f"Error sending SELL notification to user {user_id}: {e}")
                    continue
    
    except Exception as e:
        logger.error(f"Error broadcasting SELL to users: {e}")