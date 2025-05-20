"""
Fix Start Command Freezing Issues
This script patches the bot_v20_runner.py file to reduce freezing issues with the /start command.
"""

import logging
import os
import re
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def patch_bot_file():
    """
    Patch bot_v20_runner.py to fix freezing issues
    """
    bot_file = 'bot_v20_runner.py'
    
    if not os.path.exists(bot_file):
        logger.error(f"Bot file {bot_file} not found")
        return False
    
    try:
        with open(bot_file, 'r') as file:
            content = file.read()
        
        # 1. Fix admin_confirm_adjustment_handler to use non-blocking balance manager
        if 'admin_confirm_adjustment_handler' in content:
            # Insert import for non_blocking_balance_manager
            if 'import non_blocking_balance_manager' not in content:
                # Add import at the beginning of the file after other imports
                import_match = re.search(r'import.*?\n\n', content, re.DOTALL)
                if import_match:
                    end_of_imports = import_match.end()
                    content = content[:end_of_imports] + "import non_blocking_balance_manager\n\n" + content[end_of_imports:]
            
            # Find admin_confirm_adjustment_handler function
            adjustment_handler_match = re.search(r'def admin_confirm_adjustment_handler\(.*?\).*?(?=def|\Z)', content, re.DOTALL)
            
            if adjustment_handler_match:
                # Replace the function with a version that uses non_blocking_balance_manager
                old_handler = adjustment_handler_match.group(0)
                
                new_handler = """def admin_confirm_adjustment_handler(update, context):
    # Handle admin confirmation of balance adjustment."""
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
        
        # Process adjustment in background to prevent freezing
        success, message = non_blocking_balance_manager.adjust_balance(
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
        logger.error(f"Error confirming adjustment: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        try:
            update.callback_query.message.reply_text(f"⚠️ Error confirming adjustment: {str(e)}")
        except Exception:
            pass
"""
                # Replace the function
                content = content.replace(old_handler, new_handler)
        
        # 2. Fix start command to avoid blocking operations
        start_handler_match = re.search(r'def start_command\(.*?\).*?(?=def|\Z)', content, re.DOTALL)
        
        if start_handler_match:
            old_start = start_handler_match.group(0)
            
            # Make the start command more efficient
            # 1. Avoid unnecessary database queries
            # 2. Defer some processing to background threads
            # 3. Don't block on operations that aren't immediately needed
            new_start = old_start.replace(
                "user.last_active = datetime.utcnow()",
                """# Update last active in background to avoid blocking
                import threading
                def update_last_active(user_id):
                    with app.app_context():
                        try:
                            from models import User
                            user = User.query.filter_by(id=user_id).first()
                            if user:
                                user.last_active = datetime.utcnow()
                                db.session.commit()
                        except Exception as e:
                            logger.error(f"Error updating last_active: {e}")
                
                # Run update in background
                if user and user.id:
                    threading.Thread(target=update_last_active, args=(user.id,), daemon=True).start()"""
            )
        
            # Update the content
            content = content.replace(old_start, new_start)
        
        # Write the modified content back to file
        with open(bot_file, 'w') as file:
            file.write(content)
        
        logger.info(f"Successfully patched {bot_file} to reduce freezing issues")
        return True
        
    except Exception as e:
        logger.error(f"Error patching bot file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Fixing freezing issues with the Solana Memecoin Trading Bot...")
    if patch_bot_file():
        print("✅ Successfully patched bot_v20_runner.py to reduce freezing issues")
        print("Restart the bot for changes to take effect")
    else:
        print("❌ Failed to patch bot_v20_runner.py - see log for details")