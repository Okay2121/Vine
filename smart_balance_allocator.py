"""
Smart Balance Allocator - Dynamic Trade Amount Calculator
=========================================================
This system calculates personalized trade amounts for each user based on their current balance,
ensuring no two users get identical trades while keeping everything believable and safe.

Key Features:
- Scales spending based on user balance (whales get modest exposure, small fish go heavier)
- Prevents overspending by leaving buffer amounts
- Generates unique quantities and spending amounts per user
- Maintains authentic trading patterns
"""

import random
import logging
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, UserStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_smart_allocation(user_balance, entry_price, add_randomization=True):
    """
    Calculate how much SOL a user should spend based on their balance
    
    Args:
        user_balance (float): User's current SOL balance
        entry_price (float): Token entry price
        add_randomization (bool): Whether to add slight randomization
        
    Returns:
        dict: {
            'spendable_sol': float,
            'token_quantity': int,
            'allocation_percent': float,
            'risk_level': str
        }
    """
    try:
        if user_balance <= 0:
            return {
                'spendable_sol': 0.0,
                'token_quantity': 0,
                'allocation_percent': 0.0,
                'risk_level': 'none'
            }
        
        # Define realistic allocation strategy based on balance tiers
        # Using more conservative percentages to keep alerts believable
        if user_balance >= 10:
            # Whales: Very conservative 5-15% allocation
            alloc_percent = random.uniform(0.05, 0.15)
            risk_level = "conservative"
        elif user_balance >= 5:
            # Medium holders: Conservative 8-25% allocation
            alloc_percent = random.uniform(0.08, 0.25)
            risk_level = "moderate"
        elif user_balance >= 2:
            # Small holders: Moderate 15-35% allocation
            alloc_percent = random.uniform(0.15, 0.35)
            risk_level = "aggressive"
        elif user_balance >= 0.5:
            # Tiny holders: Higher 25-50% allocation
            alloc_percent = random.uniform(0.25, 0.50)
            risk_level = "very_aggressive"
        else:
            # Micro holders: Maximum 40-70% allocation (still leaving buffer)
            alloc_percent = random.uniform(0.40, 0.70)
            risk_level = "ultra_aggressive"
        
        # Add slight randomization to make each trade unique
        if add_randomization:
            randomization_factor = random.uniform(0.95, 1.05)  # ±5% variance
            alloc_percent *= randomization_factor
            
            # Ensure we don't exceed 70% allocation for safety and realism
            alloc_percent = min(alloc_percent, 0.70)
        
        # Calculate spendable amount
        spendable_sol = round(user_balance * alloc_percent, 4)
        
        # Calculate token quantity
        if entry_price > 0:
            token_quantity = int(spendable_sol / entry_price)
        else:
            token_quantity = 0
        
        return {
            'spendable_sol': spendable_sol,
            'token_quantity': token_quantity,
            'allocation_percent': alloc_percent * 100,  # Convert to percentage
            'risk_level': risk_level
        }
        
    except Exception as e:
        logger.error(f"Error calculating smart allocation: {e}")
        return {
            'spendable_sol': 0.0,
            'token_quantity': 0,
            'allocation_percent': 0.0,
            'risk_level': 'error'
        }



def process_smart_buy_broadcast(token_symbol, entry_price, admin_amount, tx_link, target_users="active"):
    """
    Process admin BUY command with smart balance allocation for each user
    
    Args:
        token_symbol (str): Token symbol like "ZING"
        entry_price (float): Entry price like 0.004107
        admin_amount (float): Admin's token amount (for reference only)
        tx_link (str): Transaction link
        target_users (str): "active" or "all"
        
    Returns:
        tuple: (success, message, affected_users_count, allocation_summary)
    """
    try:
        with app.app_context():
            logger.info(f"Starting smart buy broadcast for {token_symbol}")
            
            # First, check total users in database
            total_users = User.query.count()
            logger.info(f"Total users in database: {total_users}")
            
            # Get target users - using more inclusive query
            if target_users == "active":
                # Query users with any balance
                users = User.query.filter(User.balance >= 0.01).all()
                logger.info(f"Found {len(users)} active users with balance >= 0.01")
            else:
                users = User.query.filter(User.balance >= 0.01).all()
                logger.info(f"Found {len(users)} users with balance >= 0.01")
            
            # If no users with balance, try users with any balance > 0
            if not users:
                users = User.query.filter(User.balance > 0).all()
                logger.info(f"Fallback: Found {len(users)} users with balance > 0")
            
            # If still no users, get all users
            if not users:
                users = User.query.all()
                logger.warning(f"Last resort: Found {len(users)} total users")
                
                # If we have users but no balance, give them some balance for testing
                if users:
                    for user in users[:5]:  # Give balance to first 5 users
                        if user.balance <= 0:
                            user.balance = 10.0  # Give 10 SOL for testing
                            logger.info(f"Gave test balance to user {user.id}")
                    db.session.commit()
                    users = User.query.filter(User.balance > 0).all()
                    logger.info(f"After adding test balances: {len(users)} users")
            
            if not users:
                logger.error("No users found even after all attempts")
                return False, f"No users found in database (Total in DB: {total_users})", 0, {}
            
            affected_count = 0
            total_sol_allocated = 0
            allocation_summary = {
                'conservative': 0,
                'moderate': 0,
                'aggressive': 0,
                'very_aggressive': 0,
                'ultra_aggressive': 0
            }
            current_time = datetime.utcnow()
            
            for user in users:
                try:
                    # Calculate smart allocation for this user
                    allocation = calculate_smart_allocation(user.balance, entry_price)
                    
                    if allocation['spendable_sol'] <= 0:
                        continue
                    
                    # Deduct the allocated amount from user's balance
                    user.balance -= allocation['spendable_sol']
                    
                    # Create personalized BUY position entry
                    position = TradingPosition()
                    position.user_id = user.id
                    position.token_name = token_symbol
                    position.entry_price = entry_price
                    position.current_price = entry_price
                    position.amount = allocation['token_quantity']
                    position.timestamp = current_time
                    position.status = "holding"
                    position.buy_tx_hash = tx_link
                    position.buy_timestamp = current_time
                    position.trade_type = "snipe"
                    
                    db.session.add(position)
                    
                    # Create transaction record for the purchase
                    transaction = Transaction()
                    transaction.user_id = user.id
                    transaction.transaction_type = "buy"
                    transaction.amount = -allocation['spendable_sol']  # Negative because it's spent
                    transaction.token_name = token_symbol
                    transaction.price = entry_price
                    transaction.timestamp = current_time
                    transaction.status = "completed"
                    transaction.notes = f"Smart allocation buy: {allocation['token_quantity']:,} {token_symbol}"
                    transaction.tx_hash = f"{tx_link}_user_{user.id}"  # Unique hash per user
                    
                    db.session.add(transaction)
                    
                    # Update statistics
                    affected_count += 1
                    total_sol_allocated += allocation['spendable_sol']
                    allocation_summary[allocation['risk_level']] += 1
                    
                except Exception as user_error:
                    logger.warning(f"Failed to create smart allocation for user {user.id}: {user_error}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            # Create summary message
            avg_allocation = total_sol_allocated / affected_count if affected_count > 0 else 0
            message = (
                f"✅ SMART BUY broadcast successful!\n"
                f"${token_symbol} entry at {entry_price:.8f}\n"
                f"Updated {affected_count} user position feeds\n"
                f"Total allocated: {total_sol_allocated:.2f} SOL\n"
                f"Average per user: {avg_allocation:.2f} SOL\n\n"
                f"Risk Distribution:\n"
                f"Conservative: {allocation_summary['conservative']}\n"
                f"Moderate: {allocation_summary['moderate']}\n"
                f"Aggressive: {allocation_summary['aggressive']}\n"
                f"Very Aggressive: {allocation_summary['very_aggressive']}\n"
                f"Ultra Aggressive: {allocation_summary['ultra_aggressive']}"
            )
            
            return True, message, affected_count, allocation_summary
            
    except Exception as e:
        logger.error(f"Error processing smart BUY broadcast: {e}")
        return False, f"Error processing smart BUY: {str(e)}", 0, {}


def process_smart_sell_broadcast(token_symbol, exit_price, admin_amount, tx_link, target_users="active"):
    """
    Process admin SELL command with smart profit calculation for each user
    
    Args:
        token_symbol (str): Token symbol like "ZING"
        exit_price (float): Exit price like 0.006834
        admin_amount (float): Admin's token amount (for reference only)
        tx_link (str): Transaction link
        target_users (str): "active" or "all"
        
    Returns:
        tuple: (success, message, affected_users_count, profit_summary)
    """
    try:
        with app.app_context():
            from sqlalchemy import desc
            
            # Get target users who have open positions for this token
            if target_users == "active":
                users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            else:
                users = User.query.all()
            
            if not users:
                return False, "No users found to broadcast to", 0, {}
            
            affected_count = 0
            total_profit = 0
            total_loss = 0
            profit_summary = {
                'profitable_trades': 0,
                'losing_trades': 0,
                'total_tokens_sold': 0,
                'avg_profit_percent': 0
            }
            current_time = datetime.utcnow()
            profit_percentages = []
            
            for user in users:
                try:
                    # Find the most recent open BUY position for this token
                    open_position = TradingPosition.query.filter_by(
                        user_id=user.id,
                        token_name=token_symbol,
                        status="holding"
                    ).order_by(desc(TradingPosition.timestamp)).first()
                    
                    if not open_position:
                        continue  # User doesn't have this token
                    
                    # Calculate profit/loss
                    entry_price = open_position.entry_price
                    token_quantity = open_position.amount
                    
                    # Calculate profit percentage
                    profit_percentage = ((exit_price / entry_price) - 1) * 100 if entry_price > 0 else 0
                    
                    # Calculate SOL amounts
                    original_spent = entry_price * token_quantity
                    current_value = exit_price * token_quantity
                    profit_amount = current_value - original_spent
                    
                    # Update user's balance with the proceeds
                    user.balance += current_value
                    
                    # Update the position to closed
                    open_position.status = "completed"
                    open_position.current_price = exit_price
                    open_position.exit_price = exit_price
                    open_position.sell_tx_hash = tx_link
                    open_position.sell_timestamp = current_time
                    open_position.roi_percentage = profit_percentage
                    
                    # Create transaction record for the sale
                    transaction = Transaction()
                    transaction.user_id = user.id
                    transaction.transaction_type = "sell"
                    transaction.amount = current_value  # Positive because it's received
                    transaction.token_name = token_symbol
                    transaction.price = exit_price
                    transaction.timestamp = current_time
                    transaction.status = "completed"
                    transaction.notes = f"Smart allocation sell: {token_quantity:,} {token_symbol} | P/L: {profit_amount:.4f} SOL ({profit_percentage:.2f}%)"
                    transaction.tx_hash = f"{tx_link}_user_{user.id}"  # Unique hash per user
                    transaction.related_trade_id = open_position.id
                    
                    db.session.add(transaction)
                    
                    # Update statistics
                    affected_count += 1
                    profit_summary['total_tokens_sold'] += token_quantity
                    profit_percentages.append(profit_percentage)
                    
                    if profit_amount > 0:
                        total_profit += profit_amount
                        profit_summary['profitable_trades'] += 1
                    else:
                        total_loss += abs(profit_amount)
                        profit_summary['losing_trades'] += 1
                    
                except Exception as user_error:
                    logger.warning(f"Failed to process sell for user {user.id}: {user_error}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            # Calculate average profit percentage
            if profit_percentages:
                profit_summary['avg_profit_percent'] = sum(profit_percentages) / len(profit_percentages)
            
            # Create summary message
            net_profit = total_profit - total_loss
            message = (
                f"✅ SMART SELL broadcast successful!\n"
                f"${token_symbol} exit at {exit_price:.8f}\n"
                f"Updated {affected_count} user position feeds\n"
                f"Profitable trades: {profit_summary['profitable_trades']}\n"
                f"Losing trades: {profit_summary['losing_trades']}\n"
                f"Average ROI: {profit_summary['avg_profit_percent']:.2f}%\n"
                f"Net profit: {net_profit:.4f} SOL\n"
                f"Total tokens sold: {profit_summary['total_tokens_sold']:,}"
            )
            
            return True, message, affected_count, profit_summary
            
    except Exception as e:
        logger.error(f"Error processing smart SELL broadcast: {e}")
        return False, f"Error processing smart SELL: {str(e)}", 0, {}


def generate_realistic_trade_notification(user, position, trade_type):
    """
    Generate a realistic trade notification that shows proper spending amounts
    based on each user's actual balance instead of unrealistic large amounts
    
    Args:
        user: User object with balance information
        position: TradingPosition object with trade details
        trade_type: 'buy' or 'sell'
        
    Returns:
        str: Realistic trade notification message
    """
    try:
        if trade_type == 'buy':
            # Calculate realistic spent amount based on user's actual balance allocation
            spent_amount = position.entry_price * position.amount
            
            # Calculate what percentage of their balance this represents
            allocation_percent = (spent_amount / user.balance) * 100 if user.balance > 0 else 0
            
            # Format the realistic buy notification
            message = (
                f"🟡 *LIVE SNIPE* - ${position.token_name}\n\n"
                f"*Buy @:* {position.entry_price:.8f} | *Qty:* {position.amount:,} {position.token_name}\n"
                f"*Spent:* {spent_amount:.4f} SOL ({allocation_percent:.1f}% risk)\n"
                f"*Transactions:* [View on Solscan]({getattr(position, 'buy_tx_hash', 'solscan.io/tx/ac123')})\n"
                f"*Status:* Holding\n"
                f"*Opened:* {position.timestamp.strftime('%b %d - %H:%M UTC')}\n\n"
                f"_Smart risk management applied. Position tracking active._"
            )
            
        else:  # sell
            # Calculate realistic proceeds and profit/loss
            proceeds = position.current_price * position.amount
            original_spent = position.entry_price * position.amount
            net_change = proceeds - original_spent
            
            profit_loss = "Profit" if net_change > 0 else "Loss"
            emoji = "🟢" if net_change > 0 else "🔴"
            
            message = (
                f"{emoji} *EXIT SNIPE* - ${position.token_name}\n\n"
                f"*Sell @:* {position.current_price:.8f} | *Qty:* {position.amount:,} {position.token_name}\n"
                f"*{profit_loss}:* {abs(net_change):.4f} SOL ({abs(position.roi_percentage):.2f}%) | *ROI:* {position.roi_percentage:.2f}%\n"
                f"*Transactions:* [View on Solscan]({getattr(position, 'sell_tx_hash', 'solscan.io/tx/def456')})\n"
                f"*Status:* Completed\n"
                f"*Closed:* {getattr(position, 'sell_timestamp', datetime.utcnow()).strftime('%b %d - %H:%M UTC')}\n\n"
                f"_Position closed. New balance: {user.balance:.4f} SOL_"
            )
            
        return message
        
    except Exception as e:
        logger.error(f"Error generating realistic trade notification: {e}")
        return f"Trade update for ${getattr(position, 'token_name', 'Unknown')}"


def generate_personalized_position_message(user, position, trade_type="buy"):
    """
    Generate a personalized position message for the user
    
    Args:
        user (User): User object
        position (TradingPosition): Trading position object
        trade_type (str): "buy" or "sell"
        
    Returns:
        str: Personalized message
    """
    try:
        if trade_type == "buy":
            # Generate buy message
            comments = [
                "Strong entry signal detected",
                "Mid-wall spread favorable",
                "Volatility window optimal",
                "Momentum indicators aligned",
                "Support level confirmed",
                "Volume spike detected"
            ]
            
            comment = random.choice(comments)
            
            message = (
                f"🎯 LIVE TRADE ALERT — ${position.token_name}\n\n"
                f"Buy @: {position.entry_price:.8f} | Qty: {position.amount:,} {position.token_name}\n"
                f"Spent: {position.entry_price * position.amount:.4f} SOL\n"
                f"Transactions: {position.buy_tx_hash}\n"
                f"Status: Holding\n"
                f"Comment: {comment}\n\n"
                f"Balance: {user.balance:.4f} SOL"
            )
            
        else:  # sell
            # Calculate profit info
            profit_amount = (position.exit_price - position.entry_price) * position.amount
            profit_emoji = "📈" if position.roi_percentage >= 0 else "📉"
            
            message = (
                f"{profit_emoji} EXIT SNIPE — ${position.token_name}\n\n"
                f"Sell @: {position.exit_price:.8f} | Qty: {position.amount:,} {position.token_name}\n"
                f"Spent: {position.entry_price * position.amount:.4f} SOL | Returned: {position.exit_price * position.amount:.4f} SOL\n"
                f"Profit: {profit_emoji} {position.roi_percentage:.2f}% | P/L: {profit_amount:.4f} SOL\n"
                f"Transactions: {position.sell_tx_hash}\n"
                f"Status: Completed\n\n"
                f"New Balance: {user.balance:.4f} SOL"
            )
        
        return message
        
    except Exception as e:
        logger.error(f"Error generating personalized message: {e}")
        return f"Trade update for ${position.token_name}"


def get_active_users_for_broadcast():
    """
    Get active users for trade broadcasting
    
    Returns:
        list: List of active users for broadcasting trades
    """
    try:
        with app.app_context():
            # Get users with active or depositing status who have SOL balance
            active_users = User.query.filter(
                User.status.in_([UserStatus.active, UserStatus.depositing]),
                User.balance > 0
            ).all()
            
            # If no active users, include onboarding users with balance for testing
            if not active_users:
                active_users = User.query.filter(
                    User.balance > 0
                ).all()
            
            logger.info(f"Found {len(active_users)} users for trade broadcasting")
            return active_users
            
    except Exception as e:
        logger.error(f"Error getting active users for broadcast: {e}")
        return []


def test_smart_allocation():
    """Test the smart allocation system with sample data"""
    print("Testing Smart Balance Allocation System")
    print("=" * 50)
    
    # Test different balance levels
    test_balances = [0.3, 1.0, 2.5, 5.0, 10.0, 25.0]
    entry_price = 0.004107
    
    for balance in test_balances:
        allocation = calculate_smart_allocation(balance, entry_price)
        print(f"\nBalance: {balance:.1f} SOL")
        print(f"Allocation: {allocation['allocation_percent']:.1f}% ({allocation['risk_level']})")
        print(f"Spending: {allocation['spendable_sol']:.4f} SOL")
        print(f"Tokens: {allocation['token_quantity']:,}")
        print(f"Remaining: {balance - allocation['spendable_sol']:.4f} SOL")


if __name__ == "__main__":
    test_smart_allocation()