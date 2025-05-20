#!/usr/bin/env python
"""
Fix for admin balance adjustment confirmation handling
This script updates the admin_confirm_adjustment_handler function in the bot
"""
import sys
import re

def fix_admin_confirm_adjustment():
    """Fix the admin_confirm_adjustment_handler function to prevent freezing"""
    try:
        # Read the bot_v20_runner.py file
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
            
        # Find the admin_confirm_adjustment_handler function
        pattern = r'def admin_confirm_adjustment_handler\(update, chat_id\):(.*?)def admin_referral_overview_handler'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            print("Could not find admin_confirm_adjustment_handler in bot_v20_runner.py")
            return False
            
        # Get the current implementation
        current_impl = match.group(1)
        
        # Create a fixed version of the function
        fixed_impl = """
    \"\"\"Confirm and process the balance adjustment.\"\"\"
    try:
        # Access global variables with balance adjustment info
        global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
        global admin_adjustment_amount, admin_adjustment_reason
        
        if admin_target_user_id is None or admin_adjustment_amount is None:
            bot.send_message(
                chat_id,
                "⚠️ Balance adjustment data is missing. Please try again.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            return
            
        with app.app_context():
            from models import User, Transaction
            import logging
            from datetime import datetime
            
            # Get user from database
            user = User.query.get(admin_target_user_id)
            
            if not user:
                bot.send_message(
                    chat_id,
                    "Error: User not found. The user may have been deleted. Please try again.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
                # Reset global variables
                admin_target_user_id = None
                admin_adjust_telegram_id = None
                admin_adjust_current_balance = None
                admin_adjustment_amount = None
                admin_adjustment_reason = None
                return
                
            try:
                # Use the improved admin_balance_manager system for adjustments
                try:
                    # Check if we have the admin_balance_manager module
                    import admin_balance_manager
                    
                    # Use the module to adjust balance safely
                    identifier = user.telegram_id
                    amount = admin_adjustment_amount
                    reason = admin_adjustment_reason
                    
                    # Default reason if none provided
                    if not reason:
                        reason = "Bonus"
                    
                    success, message = admin_balance_manager.adjust_balance(identifier, amount, reason)
                    
                    if success:
                        # Extract the new balance from the user (it's already updated in the database)
                        with app.app_context():
                            # Refresh user from database to get updated balance
                            fresh_user = User.query.get(admin_target_user_id)
                            
                            if fresh_user:
                                # Show success message to admin
                                result_message = (
                                    f"✅ *Balance Updated Successfully*\\n\\n"
                                    f"User ID: `{fresh_user.telegram_id}`\\n"
                                    f"Username: @{fresh_user.username}\\n"
                                    f"Old Balance: {admin_adjust_current_balance:.4f} SOL\\n"
                                    f"New Balance: {fresh_user.balance:.4f} SOL\\n"
                                    f"Change: {'➕' if amount > 0 else '➖'} {abs(amount):.4f} SOL\\n"
                                    f"Reason: {reason}\\n\\n"
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
                                
                                # Reset globals to prevent reuse
                                admin_target_user_id = None
                                admin_adjust_telegram_id = None
                                admin_adjust_current_balance = None
                                admin_adjustment_amount = None
                                admin_adjustment_reason = None
                                return
                    else:
                        # Handle error from the balance adjuster
                        bot.send_message(
                            chat_id,
                            f"❌ Error adjusting balance: {message}",
                            reply_markup=bot.create_inline_keyboard([
                                [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                            ])
                        )
                        
                        # Reset global variables
                        admin_target_user_id = None
                        admin_adjust_telegram_id = None
                        admin_adjust_current_balance = None
                        admin_adjustment_amount = None
                        admin_adjustment_reason = None
                        return
                    
                except ImportError:
                    # Fall back to the built-in adjustment logic if module not found
                    logging.warning("admin_balance_manager not found, using built-in adjustment logic")
                    
                    # Begin transaction
                    old_balance = user.balance
                    
                    # Update user balance
                    user.balance += admin_adjustment_amount
                    
                    # Create transaction record
                    transaction_type = 'admin_credit' if admin_adjustment_amount > 0 else 'admin_debit'
                    
                    # Create the transaction record with the notes field for the reason
                    new_transaction = Transaction()
                    new_transaction.user_id = user.id
                    new_transaction.transaction_type = transaction_type
                    new_transaction.amount = abs(admin_adjustment_amount)
                    new_transaction.token_name = "SOL"  # Default token
                    new_transaction.status = 'completed'
                    new_transaction.notes = admin_adjustment_reason or "Bonus"  # Store the reason in the database
                    
                    # Also log the adjustment for monitoring
                    logging.info(f"Balance adjustment for User ID {user.id}: {admin_adjustment_reason or 'Bonus'}")
                    
                    # Add and commit transaction
                    db.session.add(new_transaction)
                    db.session.commit()
                    
                    # Start auto trading if this is a positive balance adjustment
                    if admin_adjustment_amount > 0:
                        try:
                            # Import the auto trading module
                            from utils.auto_trading_history import handle_admin_balance_adjustment
                            
                            # Trigger auto trading based on the balance adjustment
                            handle_admin_balance_adjustment(user.id, admin_adjustment_amount)
                            logging.info(f"Auto trading history started for user {user.id} after admin balance adjustment")
                        except Exception as trading_error:
                            logging.error(f"Failed to start auto trading history for user {user.id}: {trading_error}")
                            # Don't fail the balance adjustment process if auto trading fails
                    
                    # Show success message to admin
                    result_message = (
                        f"✅ *Balance Updated Successfully*\\n\\n"
                        f"User ID: `{user.telegram_id}`\\n"
                        f"Old Balance: {old_balance:.4f} SOL\\n"
                        f"New Balance: {user.balance:.4f} SOL\\n"
                        f"Change: {'➕' if admin_adjustment_amount > 0 else '➖'} {abs(admin_adjustment_amount):.4f} SOL\\n"
                        f"Transaction ID: {new_transaction.id}\\n\\n"
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
                    
                    # Reset global variables
                    admin_target_user_id = None
                    admin_adjust_telegram_id = None
                    admin_adjust_current_balance = None
                    admin_adjustment_amount = None
                    admin_adjustment_reason = None
                    return
                
            except Exception as db_error:
                # Handle database errors
                db.session.rollback()
                logging.error(f"Database error during balance adjustment: {db_error}")
                import traceback
                logging.error(traceback.format_exc())
                
                bot.send_message(
                    chat_id,
                    f"❌ Error adjusting balance: {str(db_error)}",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
                
                # Reset global variables
                admin_target_user_id = None
                admin_adjust_telegram_id = None
                admin_adjust_current_balance = None
                admin_adjustment_amount = None
                admin_adjustment_reason = None
                return
                
    except Exception as e:
        import logging
        logging.error(f"Error in admin_confirm_adjustment_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        try:
            # Reset global variables
            global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
            global admin_adjustment_amount, admin_adjustment_reason
            admin_target_user_id = None
            admin_adjust_telegram_id = None
            admin_adjust_current_balance = None
            admin_adjustment_amount = None
            admin_adjustment_reason = None
            
            # Send error message
            bot.send_message(
                chat_id,
                f"Error processing adjustment: {str(e)}",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
        except:
            pass
        
        return
"""
        
        # Replace the old implementation with the fixed one
        new_content = content.replace(current_impl, fixed_impl)
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(new_content)
            
        print("Successfully fixed admin_confirm_adjustment_handler")
        return True
        
    except Exception as e:
        print(f"Error fixing admin_confirm_adjustment_handler: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_admin_confirm_adjustment()
    sys.exit(0 if success else 1)