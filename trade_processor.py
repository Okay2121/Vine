"""
Trade Processor for Admin-Formatted Messages
-------------------------------------------
This module implements simple parsing and processing for admin trade messages
with the format: Buy/Sell $TOKEN PRICE TX_LINK
"""

import re
import logging
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Regular expression patterns for trade messages
BUY_PATTERN = r'^buy\s+(\$[a-zA-Z0-9]+)\s+([0-9.]+)\s+(https?://[^\s]+)$'
SELL_PATTERN = r'^sell\s+(\$[a-zA-Z0-9]+)\s+([0-9.]+)\s+(https?://[^\s]+)$'


def parse_trade_message(message_text):
    """
    Parse an admin trade message with the format: Buy/Sell $TOKEN PRICE TX_LINK
    
    Args:
        message_text (str): The message text to parse
        
    Returns:
        dict: Parsed trade data or None if not a valid trade message
    """
    # Convert to lowercase for case-insensitive matching
    text = message_text.lower().strip()
    
    # Try to match buy pattern
    buy_match = re.match(BUY_PATTERN, text)
    if buy_match:
        token_name, price_str, tx_link = buy_match.groups()
        return {
            'trade_type': 'buy',
            'token_name': token_name.upper(),  # Normalize token name to uppercase
            'price': float(price_str),
            'tx_link': tx_link
        }
    
    # Try to match sell pattern
    sell_match = re.match(SELL_PATTERN, text)
    if sell_match:
        token_name, price_str, tx_link = sell_match.groups()
        return {
            'trade_type': 'sell',
            'token_name': token_name.upper(),  # Normalize token name to uppercase
            'price': float(price_str),
            'tx_link': tx_link
        }
    
    # No match found
    return None


def process_buy_trade(token_name, entry_price, tx_hash, admin_user=None):
    """
    Process a BUY trade and store it for future SELL matching.
    
    Args:
        token_name (str): Token symbol (e.g. $ZING)
        entry_price (float): Entry price for the token
        tx_hash (str): Transaction hash or link
        admin_user (str, optional): Admin user who executed the trade
        
    Returns:
        tuple: (success, message, position)
    """
    try:
        # Extract just the transaction hash if a full URL was provided
        if '/' in tx_hash:
            tx_hash = tx_hash.split('/')[-1]
        
        # Check if this transaction has already been processed
        existing_position = TradingPosition.query.filter_by(
            buy_tx_hash=tx_hash
        ).first()
        
        if existing_position:
            return (False, f"This BUY transaction has already been processed for {existing_position.token_name}", None)
        
        # Clean token name (remove $ if present)
        token_name = token_name.replace('$', '')
        
        # Create a new open trading position
        now = datetime.utcnow()
        position = TradingPosition()
        position.user_id = 1  # Placeholder - will be updated when matched with users on SELL
        position.token_name = token_name
        position.amount = 1.0  # Placeholder - will be calculated during SELL
        position.entry_price = entry_price
        position.current_price = entry_price  # Same as entry price initially
        position.timestamp = now
        position.status = 'open'
        position.buy_tx_hash = tx_hash
        position.buy_timestamp = now
        
        db.session.add(position)
        db.session.commit()
        
        logger.info(f"Stored BUY position for {token_name} at {entry_price} (TX: {tx_hash})")
        return (True, f"BUY position for {token_name} at {entry_price} stored successfully", position)
        
    except Exception as e:
        logger.error(f"Error processing BUY trade: {str(e)}")
        db.session.rollback()
        return (False, f"Error processing BUY trade: {str(e)}", None)


def process_sell_trade(token_name, sell_price, tx_hash, admin_user=None):
    """
    Process a SELL trade and match it with a pending BUY for profit calculation.
    
    Args:
        token_name (str): Token symbol (e.g. $ZING)
        sell_price (float): Exit/sell price for the token
        tx_hash (str): Transaction hash or link
        admin_user (str, optional): Admin user who executed the trade
        
    Returns:
        tuple: (success, message, matched_position, roi_percentage)
    """
    try:
        # Extract just the transaction hash if a full URL was provided
        if '/' in tx_hash:
            tx_hash = tx_hash.split('/')[-1]
        
        # Check if this transaction has already been processed
        existing_position = TradingPosition.query.filter_by(
            sell_tx_hash=tx_hash
        ).first()
        
        if existing_position:
            return (False, f"This SELL transaction has already been processed", None, 0)
        
        # Clean token name (remove $ if present)
        token_name = token_name.replace('$', '')
        
        # Find the oldest unmatched BUY order for this token
        buy_position = TradingPosition.query.filter_by(
            token_name=token_name,
            status='open',
            sell_tx_hash=None
        ).order_by(TradingPosition.buy_timestamp.asc()).first()
        
        if not buy_position:
            return (False, f"No matching BUY position found for {token_name}", None, 0)
        
        # Calculate ROI percentage
        entry_price = buy_position.entry_price
        roi_percentage = ((sell_price - entry_price) / entry_price) * 100
        
        # Update the position with sell information
        now = datetime.utcnow()
        buy_position.current_price = sell_price
        buy_position.sell_tx_hash = tx_hash
        buy_position.sell_timestamp = now
        buy_position.status = 'closed'
        buy_position.roi_percentage = roi_percentage
        
        db.session.commit()
        
        logger.info(f"Matched SELL for {token_name} at {sell_price}. ROI: {roi_percentage:.2f}%")
        return (True, f"SELL matched with BUY. ROI: {roi_percentage:.2f}%", buy_position, roi_percentage)
        
    except Exception as e:
        logger.error(f"Error processing SELL trade: {str(e)}")
        db.session.rollback()
        return (False, f"Error processing SELL trade: {str(e)}", None, 0)


def apply_trade_to_users(position, user_filter=None):
    """
    Apply a completed trade (matched BUY+SELL) to all active users or filtered subset.
    
    Args:
        position (TradingPosition): The matched trading position
        user_filter (list, optional): List of user IDs to apply the trade to
        
    Returns:
        tuple: (success, message, updated_users_count)
    """
    try:
        # Get the query for active users
        query = User.query.filter(User.balance > 0)
        
        # Apply user filter if provided
        if user_filter:
            query = query.filter(User.id.in_(user_filter))
        
        # Get all users to update
        users = query.all()
        
        if not users:
            return (False, "No active users found to apply trade", 0)
        
        # Calculate ROI percentage
        roi_percentage = position.roi_percentage
        if not roi_percentage:
            roi_percentage = ((position.current_price - position.entry_price) / position.entry_price) * 100
        
        # Track users updated
        updated_count = 0
        
        # Apply the ROI to each user's balance
        for user in users:
            try:
                # Calculate profit amount based on user's balance
                profit_percentage = roi_percentage / 100  # Convert to decimal
                profit_amount = user.balance * profit_percentage
                
                # Update user balance
                previous_balance = user.balance
                user.balance += profit_amount
                
                # Create transaction record with unique identifier
                transaction = Transaction()
                transaction.user_id = user.id
                transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                transaction.amount = profit_amount
                transaction.token_name = position.token_name
                transaction.status = 'completed'
                transaction.notes = f"Trade ROI: {roi_percentage:.2f}% - {position.token_name}"
                # Create unique tx_hash by combining sell hash with user ID
                transaction.tx_hash = f"{position.sell_tx_hash}_u{user.id}"
                transaction.processed_at = datetime.utcnow()
                
                # Create a completed trading position linked to this user
                user_position = TradingPosition()
                user_position.user_id = user.id
                user_position.token_name = position.token_name
                user_position.amount = abs(profit_amount / (position.current_price - position.entry_price)) if position.current_price != position.entry_price else 1.0
                user_position.entry_price = position.entry_price
                user_position.current_price = position.current_price
                user_position.timestamp = datetime.utcnow()
                user_position.status = 'closed'
                user_position.buy_tx_hash = position.buy_tx_hash
                user_position.sell_tx_hash = position.sell_tx_hash
                user_position.buy_timestamp = position.buy_timestamp
                user_position.sell_timestamp = position.sell_timestamp
                user_position.roi_percentage = roi_percentage
                user_position.paired_position_id = position.id
                
                db.session.add(transaction)
                db.session.add(user_position)
                updated_count += 1
                
            except Exception as user_error:
                logger.error(f"Error updating user {user.id}: {str(user_error)}")
                continue
        
        # Commit all changes
        db.session.commit()
        
        return (True, f"Applied trade to {updated_count} users", updated_count)
        
    except Exception as e:
        logger.error(f"Error applying trade to users: {str(e)}")
        db.session.rollback()
        return (False, f"Error applying trade to users: {str(e)}", 0)


def handle_trade_message(message_text):
    """
    Process an admin trade message and execute the appropriate actions.
    
    Args:
        message_text (str): The admin trade message text
        
    Returns:
        tuple: (success, message, details)
    """
    parsed_data = parse_trade_message(message_text)
    
    if not parsed_data:
        return (False, "Invalid trade message format. Expected: Buy/Sell $TOKEN PRICE TX_LINK", None)
    
    # Process based on trade type
    if parsed_data['trade_type'] == 'buy':
        success, message, position = process_buy_trade(
            parsed_data['token_name'],
            parsed_data['price'],
            parsed_data['tx_link']
        )
        
        return (success, message, {
            'trade_type': 'buy',
            'token': parsed_data['token_name'],
            'price': parsed_data['price'],
            'position_id': position.id if position else None
        })
        
    elif parsed_data['trade_type'] == 'sell':
        success, message, position, roi = process_sell_trade(
            parsed_data['token_name'],
            parsed_data['price'],
            parsed_data['tx_link']
        )
        
        if success and position:
            # Apply the trade to all active users
            apply_success, apply_message, updated_count = apply_trade_to_users(position)
            
            if not apply_success:
                message += f"\nWarning: {apply_message}"
            else:
                message += f"\nApplied to {updated_count} users"
        
        return (success, message, {
            'trade_type': 'sell',
            'token': parsed_data['token_name'],
            'price': parsed_data['price'],
            'roi_percentage': roi,
            'position_id': position.id if position else None,
        })
        
    return (False, "Unknown trade type", None)