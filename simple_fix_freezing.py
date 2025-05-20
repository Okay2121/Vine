"""
Simple Fix for Command Freezing in Solana Memecoin Bot
This simple script adds non-blocking functionality to critical operations.
"""

import os
import logging
import threading
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_admin_confirm_handler(bot_file='bot_v20_runner.py'):
    """
    Fix admin_confirm_adjustment_handler to use non-blocking operations
    """
    try:
        # Read the file
        with open(bot_file, 'r') as file:
            content = file.read()
        
        # Check if the function exists
        if 'def admin_confirm_adjustment_handler(' not in content:
            logger.error(f"admin_confirm_adjustment_handler not found in {bot_file}")
            return False
        
        # Add non-blocking imports at top of file
        if 'import threading' not in content:
            # Find end of imports section
            import_position = content.find('\n\n', content.find('import'))
            if import_position > 0:
                content = content[:import_position] + '\nimport threading\n' + content[import_position:]
        
        # Identify the admin_confirm_adjustment_handler function
        start_marker = 'def admin_confirm_adjustment_handler(update, context):'
        start_pos = content.find(start_marker)
        
        if start_pos == -1:
            logger.error("admin_confirm_adjustment_handler function not found")
            return False
        
        # Find the end of the function
        next_def_pos = content.find('\ndef ', start_pos + 1)
        if next_def_pos == -1:
            next_def_pos = len(content)
        
        # Extract the function content
        func_end = next_def_pos
        function_body = content[start_pos:func_end]
        
        # Replace blocking balance updates with non-blocking ones
        if 'with app.app_context():' in function_body:
            # Find the balance update section
            balance_update_start = function_body.find('with app.app_context():')
            if balance_update_start > 0:
                # Find all indented lines after with statement
                lines = function_body[balance_update_start:].split('\n')
                indentation = '        '  # Base indentation for the handler function
                
                # Create a non-blocking version
                non_blocking_func = f"""
def admin_confirm_adjustment_handler(update, context):
    \"\"\"Handle admin confirmation of balance adjustment.\"\"\"
    try:
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
        
        # Run the actual balance adjustment in a background thread to prevent freezing
        def process_adjustment_in_background():
            try:
                with app.app_context():
                    # Find the user
                    if target_user.isdigit():
                        user = User.query.filter_by(telegram_id=target_user).first()
                    else:
                        username = target_user
                        if username.startswith('@'):
                            username = username[1:]
                        user = User.query.filter(User.username.ilike(username)).first()
                    
                    if not user:
                        logger.error(f"User not found: {target_user}")
                        return
                    
                    # Update the balance
                    current_balance = user.balance or 0
                    user.balance = current_balance + amount
                    
                    # Create transaction record
                    transaction_type = 'deposit' if amount > 0 else 'withdrawal'
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
                    
                    logger.info(f"Successfully adjusted balance for {user.username} (ID: {user.id}): {current_balance} → {user.balance}")
                    
                    # If this is a deposit and auto trading is enabled, start it
                    if amount > 0:
                        # This part would trigger auto trading if available
                        pass
            except Exception as e:
                logger.error(f"Error in background balance adjustment: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Start the background thread
        thread = threading.Thread(target=process_adjustment_in_background, daemon=True)
        thread.start()
        
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
        logger.error(f"Error confirming adjustment: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        try:
            update.callback_query.message.reply_text(f"⚠️ Error confirming adjustment: {str(e)}")
        except Exception:
            pass
"""
                
                # Replace the old function with the new one
                new_content = content[:start_pos] + non_blocking_func + content[func_end:]
                
                # Write back to file
                with open(bot_file, 'w') as file:
                    file.write(new_content)
                
                logger.info(f"Successfully updated {bot_file} with non-blocking balance adjustment")
                return True
        
        logger.error("Could not find the balance update section in the function")
        return False
        
    except Exception as e:
        logger.error(f"Error fixing admin confirm handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Fixing command freezing issues in Solana Memecoin Bot...")
    
    if fix_admin_confirm_handler():
        print("✅ Successfully fixed admin_confirm_adjustment_handler to prevent freezing")
        print("Restart your bot for the changes to take effect")
    else:
        print("❌ Failed to fix admin_confirm_adjustment_handler")