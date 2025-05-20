"""
Non-Blocking Balance Manager Fix
This script patches the admin_confirm_adjustment_handler to prevent freezing
when adjusting user balances.
"""

import logging
import threading
import time
from datetime import datetime
import os
import sys
import traceback

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def find_user(identifier):
    """
    Find a user by username (case-insensitive) or telegram_id
    
    Args:
        identifier (str): Username (with or without @) or telegram_id
        
    Returns:
        User object or None if not found
    """
    from app import app
    from models import User
    
    with app.app_context():
        # Try to parse as numeric ID first
        try:
            user_id = int(identifier)
            # Try as telegram_id
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            if user:
                return user
            
            # Try as database ID
            user = User.query.filter_by(id=user_id).first()
            if user:
                return user
        except (ValueError, TypeError):
            pass
        
        # Try as username
        username = identifier
        if username.startswith('@'):
            username = username[1:]
        
        user = User.query.filter(User.username.ilike(username)).first()
        return user

def adjust_balance_in_background(identifier, amount, reason="Admin balance adjustment", skip_trading=False):
    """
    Adjust a user's balance in a background thread to prevent bot freezing
    
    Args:
        identifier (str): Username or telegram_id of the user
        amount (float): Amount to adjust (positive to add, negative to deduct)
        reason (str): Reason for the adjustment
        skip_trading (bool): If True, don't trigger auto trading
        
    Returns:
        None - this runs in the background
    """
    thread = threading.Thread(
        target=_process_balance_adjustment,
        args=(identifier, amount, reason, skip_trading),
        daemon=True
    )
    thread.start()
    
    # Return immediately to prevent freezing
    return f"Processing balance adjustment for {identifier} in the background."

def _process_balance_adjustment(identifier, amount, reason, skip_trading):
    """Background processor for balance adjustments"""
    from app import app, db
    from models import User, Transaction, TransactionType
    
    try:
        with app.app_context():
            # Find the user
            user = find_user(identifier)
            
            if not user:
                logger.error(f"User not found: {identifier}")
                return
            
            # Begin transaction safely with retries
            retry_count = 0
            max_retries = 3
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    # Get current balance
                    current_balance = user.balance or 0
                    
                    # Update balance
                    user.balance = current_balance + amount
                    
                    # Create transaction record
                    transaction_type = TransactionType.DEPOSIT if amount > 0 else TransactionType.WITHDRAWAL
                    transaction = Transaction(
                        user_id=user.id,
                        amount=abs(amount),
                        type=transaction_type,
                        status='completed',
                        description=reason,
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(transaction)
                    db.session.commit()
                    success = True
                    
                    logger.info(f"Successfully adjusted balance for {user.username} (ID: {user.id}): {current_balance} → {user.balance}")
                    
                    # Start trading in background if positive adjustment and not skipped
                    if amount > 0 and not skip_trading:
                        _start_trading(user.id, amount)
                        
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Retry {retry_count}/{max_retries} - Error adjusting balance: {e}")
                    db.session.rollback()
                    time.sleep(0.5)  # Brief pause before retry
            
            if not success:
                logger.error(f"Failed to adjust balance after {max_retries} attempts")
                
    except Exception as e:
        logger.error(f"Error in balance adjustment background task: {e}")
        logger.error(traceback.format_exc())

def _start_trading(user_id, amount):
    """Start trading for a user with the given amount - placeholder for actual implementation"""
    logger.info(f"Would start trading for user {user_id} with amount {amount}")
    # Implement actual trading logic here
    pass

def fix_bot_file():
    """
    Fix the admin_confirm_adjustment_handler in bot_v20_runner.py to use the non-blocking
    balance adjustment to prevent freezing.
    """
    bot_file = 'bot_v20_runner.py'
    
    if not os.path.exists(bot_file):
        logger.error(f"Bot file {bot_file} not found")
        return False
    
    try:
        with open(bot_file, 'r') as file:
            content = file.read()
        
        # Find admin_confirm_adjustment_handler
        if 'def admin_confirm_adjustment_handler(update, context):' not in content:
            logger.error("admin_confirm_adjustment_handler not found in bot file")
            return False
        
        # Create the replacement function that uses non-blocking adjustment
        replacement = """
def admin_confirm_adjustment_handler(update, context):
    \"\"\"Handle admin confirmation of balance adjustment.\"\"\"
    try:
        from fix_balance_manager import adjust_balance_in_background
        
        chat_id = update.callback_query.message.chat_id
        update.callback_query.answer()
        
        admin_id = update.callback_query.from_user.id
        
        # Check if the user is admin
        if str(admin_id) not in ADMIN_IDS:
            update.callback_query.message.reply_text("You are not authorized to perform this action.")
            return

        # Get adjustment details from context
        admin_data = context.user_data.get('admin_state', {}).get('adjustment_data', {})
        target_user = admin_data.get('target_user')
        amount = admin_data.get('amount')
        amount_str = admin_data.get('amount_str', '')
        reason = admin_data.get('reason', 'Admin balance adjustment')
        
        if not target_user or amount is None:
            update.callback_query.message.reply_text("Invalid adjustment data. Please try again.")
            return
        
        # Process adjustment in background to prevent freezing
        adjustment_msg = adjust_balance_in_background(
            target_user, 
            amount,
            reason=reason
        )
        
        # Update the message
        action = "added to" if amount > 0 else "deducted from"
        abs_amount = abs(amount)
        
        update.callback_query.message.edit_text(
            f"✅ {abs_amount:.6f} SOL {action} {target_user}'s balance\\n\\n"
            f"Balance adjustment is being processed in the background.\\n"
            f"Reason: {reason}"
        )
        
        # Clear admin state
        if 'admin_state' in context.user_data:
            if 'adjustment_data' in context.user_data['admin_state']:
                del context.user_data['admin_state']['adjustment_data']

    except Exception as e:
        error_msg = f"Error confirming adjustment: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        try:
            update.callback_query.message.reply_text(f"⚠️ {error_msg}")
        except Exception:
            pass
"""

        # Replace the function in the content
        import re
        pattern = r'def admin_confirm_adjustment_handler\(update, context\):.*?(?=def |$)'
        replacement = replacement.strip()
        
        # Use re.DOTALL to match across multiple lines
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Write the updated content back to the file
        with open(bot_file, 'w') as file:
            file.write(new_content)
        
        logger.info(f"Successfully updated {bot_file} with non-blocking balance adjustment")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing bot file: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if fix_bot_file():
        print("✅ Successfully fixed admin_confirm_adjustment_handler to prevent freezing")
    else:
        print("❌ Failed to fix admin_confirm_adjustment_handler")