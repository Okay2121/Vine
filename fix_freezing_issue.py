#!/usr/bin/env python
"""
Emergency Fix Script for Bot Freezing Issue
-------------------------------------------
This script fixes the critical issue that causes the bot to freeze when an admin 
confirms a balance adjustment. It patches the admin_confirm_adjustment_handler function
in bot_v20_runner.py to use a non-blocking approach with background threads.
"""
import re
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_admin_confirm_handler(bot_runner_path='bot_v20_runner.py'):
    """
    Fix the admin_confirm_adjustment_handler function to prevent freezing
    
    Args:
        bot_runner_path (str): Path to the bot_v20_runner.py file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the bot_v20_runner.py file
        with open(bot_runner_path, 'r') as file:
            content = file.read()
            
        # Find the admin_confirm_adjustment_handler function
        pattern = r'def admin_confirm_adjustment_handler\(update, chat_id\):(.*?)def'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            logger.error(f"Could not find admin_confirm_adjustment_handler in {bot_runner_path}")
            return False
            
        # Get the current implementation and the function name that follows it
        current_impl = match.group(1)
        following_function = content[match.end() - 3:]  # Get the "def" and what follows
        next_func_name = following_function.split('(')[0].strip()
        
        # Create a fixed version of the function
        fixed_impl = """
    \"\"\"Confirm and process the balance adjustment without freezing the bot.\"\"\"
    # Import threading here to ensure it's available
    import threading
    import logging
    import traceback
    
    try:
        # Access global variables but copy them to local variables immediately
        global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
        global admin_adjustment_amount, admin_adjustment_reason
        
        # Store all values locally to avoid issues if globals are changed
        local_user_id = admin_target_user_id
        local_tg_id = admin_adjust_telegram_id
        local_current_balance = admin_adjust_current_balance
        local_amount = admin_adjustment_amount
        local_reason = admin_adjustment_reason or "Bonus"
        
        # Immediately reset global variables to prevent reuse
        admin_target_user_id = None
        admin_adjust_telegram_id = None
        admin_adjust_current_balance = None
        admin_adjustment_amount = None
        admin_adjustment_reason = None
        
        # Quick validation before continuing
        if local_user_id is None or local_amount is None:
            bot.send_message(
                chat_id,
                "⚠️ Balance adjustment data is missing. Please try again.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            return
            
        # Send immediate response to admin so they know the process has started
        bot.send_message(
            chat_id,
            "💰 *Processing Balance Adjustment*\\n\\nYour request is being processed. The bot will remain responsive.",
            parse_mode="Markdown"
        )
        
        # All the actual work will be done in a background thread
        def process_adjustment_in_background():
            try:
                # Import inside function to avoid any circular import issues
                import balance_manager
                
                # Log that we're starting the background process
                logging.info("Starting balance adjustment in background thread")
                
                # Get identifier to use for the adjustment
                identifier = local_tg_id  # Use the telegram ID directly if available
                
                # Only access database if we don't have a telegram ID
                if not identifier:
                    try:
                        with app.app_context():
                            user = User.query.get(local_user_id)
                            if user:
                                identifier = user.telegram_id
                    except Exception as db_error:
                        logging.error(f"Database error in background thread: {db_error}")
                        # If we can't get the telegram ID, use the user ID as fallback
                        identifier = local_user_id
                
                # Process the balance adjustment
                success, message = balance_manager.adjust_balance(
                    identifier, 
                    local_amount, 
                    local_reason
                )
                
                if success:
                    # Prepare success message
                    try:
                        with app.app_context():
                            # Try to get updated user details
                            fresh_user = User.query.get(local_user_id)
                            
                            if fresh_user:
                                # Full success message with all details
                                result_message = (
                                    f"✅ *Balance Updated Successfully*\\n\\n"
                                    f"User ID: `{fresh_user.telegram_id}`\\n"
                                    f"Username: @{fresh_user.username}\\n"
                                    f"Old Balance: {local_current_balance:.4f} SOL\\n"
                                    f"New Balance: {fresh_user.balance:.4f} SOL\\n"
                                    f"Change: {'➕' if local_amount > 0 else '➖'} {abs(local_amount):.4f} SOL\\n"
                                    f"Reason: {local_reason}\\n\\n"
                                    f"No notification was sent to the user."
                                )
                            else:
                                # Simplified message if user can't be found
                                result_message = (
                                    f"✅ *Balance Updated Successfully*\\n\\n"
                                    f"User ID: `{identifier}`\\n"
                                    f"Change: {'➕' if local_amount > 0 else '➖'} {abs(local_amount):.4f} SOL\\n"
                                    f"Reason: {local_reason}\\n\\n"
                                    f"No notification was sent to the user."
                                )
                    except Exception as db_error:
                        logging.error(f"Error getting updated user data: {db_error}")
                        # Basic fallback message if database access fails
                        result_message = (
                            f"✅ *Balance Updated Successfully*\\n\\n"
                            f"The adjustment of {'➕' if local_amount > 0 else '➖'} {abs(local_amount):.4f} SOL\\n"
                            f"has been applied to user ID: `{identifier}`\\n"
                            f"Reason: {local_reason}\\n\\n"
                            f"No notification was sent to the user."
                        )
                    
                    # Send success message to admin
                    bot.send_message(
                        chat_id,
                        result_message,
                        parse_mode="Markdown",
                        reply_markup=bot.create_inline_keyboard([
                            [
                                {"text": "Adjust Another User", "callback_data": "admin_adjust_balance"},
                                {"text": "Back to Admin", "callback_data": "admin_back"}
                            ]
                        ])
                    )
                    
                    # Log successful completion
                    logging.info(f"Balance adjustment completed in background thread: {message}")
                else:
                    # Handle error from the balance adjuster
                    bot.send_message(
                        chat_id,
                        f"❌ Error adjusting balance: {message}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
                    logging.error(f"Balance adjustment failed in background thread: {message}")
            
            except Exception as thread_error:
                # Log any errors that occur in the background thread
                logging.error(f"Unhandled error in balance adjustment thread: {thread_error}")
                logging.error(traceback.format_exc())
                
                # Try to notify the admin of the error
                try:
                    bot.send_message(
                        chat_id,
                        f"❌ An error occurred during balance adjustment: {str(thread_error)}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
                except Exception as msg_error:
                    # If sending the message fails, just log it
                    logging.error(f"Could not send error message to admin: {msg_error}")
        
        # Start the thread and return immediately
        adjustment_thread = threading.Thread(target=process_adjustment_in_background)
        adjustment_thread.daemon = True
        adjustment_thread.start()
        
        # Log that we're returning and keeping the bot responsive
        logging.info("Admin confirm adjustment handler is returning - bot remains responsive")
        return
                
    except Exception as e:
        # Handle any errors in setting up the background thread
        logging.error(f"Error in admin_confirm_adjustment_handler: {e}")
        logging.error(traceback.format_exc())
        
        try:
            # Double-check that global variables are reset
            admin_target_user_id = None
            admin_adjust_telegram_id = None
            admin_adjust_current_balance = None
            admin_adjustment_amount = None
            admin_adjustment_reason = None
            
            # Send error message
            bot.send_message(
                chat_id,
                f"Error starting adjustment process: {str(e)}",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
        except:
            # If sending the message fails, there's not much we can do
            pass
        
        return"""
        
        # Create the new content by replacing the old implementation
        new_function = f"def admin_confirm_adjustment_handler(update, chat_id):{fixed_impl}\n\ndef {next_func_name}"
        new_content = content.replace(f"def admin_confirm_adjustment_handler(update, chat_id):{current_impl}\ndef {next_func_name}", new_function)
        
        # Write the updated content back to the file
        with open(bot_runner_path, 'w') as file:
            file.write(new_content)
            
        logger.info(f"Successfully fixed admin_confirm_adjustment_handler in {bot_runner_path}")
        return True
        
    except Exception as e:
        # Handle any errors
        logger.error(f"Error fixing admin_confirm_adjustment_handler: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """
    Main function to apply the fix
    """
    logger.info("Starting emergency fix for bot freezing issue")
    
    bot_runner_path = 'bot_v20_runner.py'
    if len(sys.argv) > 1:
        bot_runner_path = sys.argv[1]
    
    success = fix_admin_confirm_handler(bot_runner_path)
    
    if success:
        logger.info("✅ Fix applied successfully! Please restart the bot for the changes to take effect.")
        print("✅ Fix applied successfully! Please restart the bot for the changes to take effect.")
    else:
        logger.error("❌ Failed to apply fix.")
        print("❌ Failed to apply fix.")

if __name__ == "__main__":
    main()