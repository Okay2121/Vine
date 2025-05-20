#!/usr/bin/env python
"""
Absolute Emergency Fix Script for Bot Freezing Issue
-----------------------------------------------------------------
This script applies a radical solution to the critical freezing issue
by completely replacing the admin_confirm_adjustment_handler with a
minimal version that runs entirely in a background thread.
"""
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_handler():
    try:
        # Read the bot file
        with open("bot_v20_runner.py", "r") as f:
            content = f.read()
        
        # Find the problematic handler by looking for its signature
        target_function = "def admin_confirm_adjustment_handler(update, chat_id):"
        if target_function not in content:
            logger.error("Could not find the target function in bot_v20_runner.py")
            return False
        
        # Create an absolutely minimal emergency handler
        # This handler does almost nothing in the main thread to prevent freezing
        emergency_handler = """def admin_confirm_adjustment_handler(update, chat_id):
    \"\"\"Emergency non-blocking balance adjustment handler.\"\"\"
    import threading
    import logging
    
    try:
        # Capture all global variables locally
        global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
        global admin_adjustment_amount, admin_adjustment_reason
        
        # Store values locally
        target_id = admin_target_user_id
        tg_id = admin_adjust_telegram_id
        current_balance = admin_adjust_current_balance
        amount = admin_adjustment_amount
        reason = admin_adjustment_reason or "Admin adjustment"
        
        # Reset globals immediately
        admin_target_user_id = None
        admin_adjust_telegram_id = None
        admin_adjust_current_balance = None
        admin_adjustment_amount = None
        admin_adjustment_reason = None
        
        # Send immediate acknowledgment
        bot.send_message(
            chat_id, 
            "✅ Processing your balance adjustment request...",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
            ])
        )
        
        # Define background worker function
        def process_adjustment():
            try:
                logging.info("Starting balance adjustment in background thread")
                
                # Process the adjustment using enhanced_balance_manager if available
                try:
                    import enhanced_balance_manager as manager
                except ImportError:
                    import balance_manager as manager
                
                # Use telegram_id as identifier
                identifier = tg_id
                
                # Process adjustment
                success, message = manager.adjust_balance(identifier, amount, reason)
                
                # Send minimal response to admin
                if success:
                    bot.send_message(
                        chat_id,
                        f"✅ Balance adjustment completed: {abs(amount):.4f} SOL {'added' if amount > 0 else 'deducted'}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ Error adjusting balance: {message}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
            except Exception as e:
                logging.error(f"Error in adjustment thread: {e}")
                try:
                    bot.send_message(
                        chat_id,
                        f"❌ Error processing adjustment: {str(e)}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
                except:
                    pass
        
        # Start a daemon thread to process the adjustment
        thread = threading.Thread(target=process_adjustment)
        thread.daemon = True
        thread.start()
        
        logging.info("Balance adjustment handler completed - thread started")
        return
    
    except Exception as e:
        logging.error(f"Error in emergency handler: {e}")
        # Reset globals if there's an error
        admin_target_user_id = None
        admin_adjust_telegram_id = None
        admin_adjust_current_balance = None
        admin_adjustment_amount = None
        admin_adjustment_reason = None
        
        try:
            bot.send_message(
                chat_id,
                f"Error processing request: {str(e)}",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
        except:
            pass
        return
"""
        
        # Find the start and end of the current handler
        start_idx = content.find(target_function)
        next_def_idx = content.find("def ", start_idx + len(target_function))
        
        if start_idx == -1 or next_def_idx == -1:
            logger.error("Could not locate the function boundaries")
            return False
        
        # Replace the handler with our emergency version
        new_content = content[:start_idx] + emergency_handler + content[next_def_idx:]
        
        # Create a backup
        with open("bot_v20_runner.py.bak", "w") as f:
            f.write(content)
            
        # Write the new version
        with open("bot_v20_runner.py", "w") as f:
            f.write(new_content)
            
        logger.info("Emergency fix applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error applying emergency fix: {e}")
        return False

if __name__ == "__main__":
    print("Applying emergency fix for freezing issue...")
    if fix_handler():
        print("✅ Emergency fix applied successfully!")
        print("Please restart the bot to apply changes")
    else:
        print("❌ Failed to apply emergency fix")