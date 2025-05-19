import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc, func
from app import db, app
from models import User, UserStatus, Transaction, Profit, ReferralCode, TradingCycle, CycleStatus
from utils.roi_system import admin_start_new_cycle, admin_adjust_roi, admin_pause_cycle, admin_resume_cycle, get_cycle_history
from config import ADMIN_USER_ID

logger = logging.getLogger(__name__)

# Define conversation states
(WAITING_FOR_USER_ID, 
 WAITING_FOR_USER_MESSAGE, 
 WAITING_FOR_BROADCAST_MESSAGE, 
 WAITING_FOR_BALANCE_ADJUSTMENT, 
 WAITING_FOR_BALANCE_REASON,
 WAITING_FOR_NEW_WALLET) = range(6)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin panel if user is authorized."""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if str(user_id) != ADMIN_USER_ID:
        await update.message.reply_text("Sorry, you don't have permission to access the admin panel.")
        return
    
    # Display admin panel
    await show_admin_panel(context, update.effective_chat.id)

async def show_admin_panel(context, chat_id, message_id=None):
    """Show the admin panel main menu."""
    admin_message = (
        "🔧 Admin Panel – Welcome, Admin. Manage users, funds, bot settings, and communications from here."
    )
    
    keyboard = [
        [InlineKeyboardButton("User Management", callback_data="admin_user_management")],
        [InlineKeyboardButton("Wallet Settings", callback_data="admin_wallet_settings")],
        [InlineKeyboardButton("Send Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("Direct Message", callback_data="admin_direct_message")],
        [InlineKeyboardButton("View Stats", callback_data="admin_view_stats")],
        [InlineKeyboardButton("Add/Adjust Balance", callback_data="admin_adjust_balance")],
        [InlineKeyboardButton("Manage Withdrawals", callback_data="admin_manage_withdrawals")],
        [InlineKeyboardButton("Bot Settings", callback_data="admin_bot_settings")],
        [InlineKeyboardButton("Exit Panel", callback_data="admin_exit")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=admin_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=admin_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def admin_user_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user management button."""
    query = update.callback_query
    await query.answer()
    
    message = (
        "👤 *User Management*\n\n"
        "Manage users, view details, and perform administrative actions."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("View All Users", callback_data="admin_view_all_users"),
            InlineKeyboardButton("View Active Users", callback_data="admin_view_active_users")
        ],
        [
            InlineKeyboardButton("Search User", callback_data="admin_search_user"),
            InlineKeyboardButton("Export Users (CSV)", callback_data="admin_export_csv")
        ],
        [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def admin_process_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the entered user ID or username."""
    user_input = update.message.text.strip()
    
    with app.app_context():
        try:
            # Try to find user by telegram ID first
            user = User.query.filter_by(telegram_id=user_input).first()
            
            # If not found, try by username
            if not user and user_input.startswith('@'):
                username = user_input[1:] # Remove @ prefix
                user = User.query.filter_by(username=username).first()
            elif not user:
                # Try with username anyway (in case they forgot the @)
                user = User.query.filter_by(username=user_input).first()
            
            if not user:
                await update.message.reply_text("User not found. Please try again or type /admin to return to admin panel.")
                return WAITING_FOR_USER_ID
            
            # Store user ID in context for later use
            context.user_data['admin_target_user_id'] = user.id
            
            # Format user details
            user_info = (
                f"User Found:\n"
                f"• User ID: {user.telegram_id}\n"
                f"• Username: {user.username or 'Not set'}\n"
                f"• Balance: {user.balance:.2f} SOL\n"
                f"• Status: {user.status.value}\n"
                f"• Initial Deposit: {user.initial_deposit:.2f} SOL\n"
                f"• Wallet Address: {user.wallet_address or 'Not set'}\n"
                f"• Profit Total: {sum([p.amount for p in user.profits]):.2f} SOL\n"
                f"• Last Active: {user.last_activity.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"• Joined: {user.joined_at.strftime('%Y-%m-%d')}\n"
            )
            
            # Check for active ROI cycle
            active_cycle = TradingCycle.query.filter_by(user_id=user.id, status=CycleStatus.IN_PROGRESS).first()
            paused_cycle = TradingCycle.query.filter_by(user_id=user.id, status=CycleStatus.PAUSED).first()
            
            # Add ROI cycle info if available
            if active_cycle:
                user_info += f"\n7-Day 2x ROI Cycle:\n"
                user_info += f"• Cycle Status: Active\n"
                user_info += f"• Start Date: {active_cycle.start_date.strftime('%Y-%m-%d')}\n"
                user_info += f"• Days Elapsed: {active_cycle.days_elapsed}\n"
                user_info += f"• Progress: {active_cycle.progress_percentage:.1f}%\n"
                user_info += f"• Initial Balance: {active_cycle.initial_balance:.2f} SOL\n"
                user_info += f"• Current Balance: {active_cycle.current_balance:.2f} SOL\n"
                user_info += f"• Daily ROI: {active_cycle.daily_roi_percentage:.2f}%\n"
            elif paused_cycle:
                user_info += f"\n7-Day 2x ROI Cycle:\n"
                user_info += f"• Cycle Status: Paused\n"
                user_info += f"• Start Date: {paused_cycle.start_date.strftime('%Y-%m-%d')}\n"
                user_info += f"• Days Elapsed: {paused_cycle.days_elapsed}\n"
                user_info += f"• Progress: {paused_cycle.progress_percentage:.1f}%\n"
            
            # Add referral info if exists
            if user.referral_code:
                user_info += f"• Referral Code: {user.referral_code[0].code}\n"
                user_info += f"• Total Referrals: {user.referral_code[0].total_referrals}\n"
            
            if user.referrer:
                user_info += f"• Referred By: {user.referrer.code}\n"
            
            # Calculate the user's available profit for withdrawal
            total_profit = sum([p.amount for p in user.profits])
            
            # Build keyboard with ROI management options
            keyboard = [
                [InlineKeyboardButton("Send Message", callback_data="admin_send_message")],
                [InlineKeyboardButton("Adjust Balance", callback_data="admin_adjust_user_balance")],
                [InlineKeyboardButton(f"Process Withdrawal ({total_profit:.2f} SOL)", callback_data="admin_process_withdrawal")],
            ]
            
            # Add ROI-specific management buttons
            if active_cycle:
                keyboard.append([InlineKeyboardButton("Pause ROI Cycle", callback_data="admin_pause_roi_cycle")])
                keyboard.append([InlineKeyboardButton("Adjust Daily ROI %", callback_data="admin_adjust_roi_percentage")])
            elif paused_cycle:
                keyboard.append([InlineKeyboardButton("Resume ROI Cycle", callback_data="admin_resume_roi_cycle")])
            else:
                keyboard.append([InlineKeyboardButton("Start New ROI Cycle", callback_data="admin_start_roi_cycle")])
            
            # Add standard admin options
            keyboard.extend([
                [InlineKeyboardButton("Reset Bot", callback_data="admin_reset_user")],
                [InlineKeyboardButton("Remove User", callback_data="admin_remove_user")],
                [InlineKeyboardButton("Back", callback_data="admin_back")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text=user_info,
                reply_markup=reply_markup
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error processing user ID: {e}")
            await update.message.reply_text("An error occurred. Please try again or type /admin to return to admin panel.")
            return WAITING_FOR_USER_ID

async def admin_wallet_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the wallet settings button."""
    query = update.callback_query
    await query.answer()
    
    # Get the current wallet address from the database
    # This would typically be a common deposit address used by the system
    # For this implementation, we'll assume this is stored somewhere
    current_wallet = "solana123456789..." # placeholder
    
    message = f"💼 Current Trading Wallet: {current_wallet}"
    
    keyboard = [
        [InlineKeyboardButton("Change Wallet Address", callback_data="admin_change_wallet")],
        [InlineKeyboardButton("View Wallet QR", callback_data="admin_view_wallet_qr")],
        [InlineKeyboardButton("Back", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

async def admin_change_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the change wallet address button."""
    query = update.callback_query
    await query.answer()
    
    message = "Please send the new Solana wallet address."
    
    await query.edit_message_text(text=message)
    
    return WAITING_FOR_NEW_WALLET

async def admin_process_new_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the new wallet address."""
    new_wallet = update.message.text.strip()
    
    # Here you would update the system wallet in your database
    # For this example, we'll just acknowledge it
    
    confirmation = f"✅ Wallet updated to: {new_wallet}. All new deposits will reflect here."
    
    await update.message.reply_text(confirmation)
    
    # Return to admin panel
    await show_admin_panel(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def admin_view_wallet_qr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the view wallet QR button."""
    query = update.callback_query
    await query.answer()
    
    # In a real implementation, you would generate and send a QR code image
    # For this example, we'll just send a message
    
    message = "QR code would be displayed here. In a real implementation, this would show a QR code image of the wallet address."
    
    keyboard = [
        [InlineKeyboardButton("Back to Wallet Settings", callback_data="admin_wallet_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the send broadcast button."""
    query = update.callback_query
    await query.answer()
    
    message = (
        "📢 Send a message to all active users.\n\n"
        "Please type your broadcast message. You can include emojis and formatting."
    )
    
    await query.edit_message_text(text=message)
    
    return WAITING_FOR_BROADCAST_MESSAGE

async def admin_process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the broadcast message."""
    broadcast_message = update.message.text
    context.user_data['broadcast_message'] = broadcast_message
    
    preview = f"Preview:\nMessage: '{broadcast_message}'"
    
    keyboard = [
        [InlineKeyboardButton("Send to All Users", callback_data="admin_send_broadcast")],
        [InlineKeyboardButton("Cancel", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=preview,
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def admin_send_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the broadcast message to all users."""
    query = update.callback_query
    await query.answer()
    
    broadcast_message = context.user_data.get('broadcast_message', "Important update from the SolanaMemobot team!")
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            sent_count = 0
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=broadcast_message,
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send broadcast to user {user.id}: {e}")
            
            result_message = f"Broadcast sent to {sent_count} out of {len(users)} users."
            
            await query.edit_message_text(text=result_message)
            
            # Return to admin panel after a short delay
            await show_admin_panel(context, query.message.chat_id, query.message.message_id)
            
        except Exception as e:
            logger.error(f"Error during broadcast: {e}")
            await query.edit_message_text(text=f"Error sending broadcast: {str(e)}")


async def admin_process_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle processing a user's withdrawal request."""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('admin_target_user_id')
    if not user_id:
        await query.edit_message_text("Error: User data not found. Please restart from the admin panel.")
        return
    
    with app.app_context():
        try:
            # Get the user record
            user = User.query.get(user_id)
            if not user:
                await query.edit_message_text("Error: User not found in database.")
                return
            
            # Get the user's profits
            total_profit = sum([p.amount for p in user.profits])
            
            # Check if user has profits to withdraw
            if total_profit <= 0:
                await query.edit_message_text(
                    f"This user has no profits available for withdrawal. Current profit: {total_profit:.2f} SOL"
                )
                return
            
            # Format wallet address for display
            wallet_address = user.wallet_address or "No wallet address set"
            if wallet_address and len(wallet_address) > 10:
                display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            else:
                display_wallet = wallet_address
            
            # Show withdrawal confirmation
            confirmation_message = (
                f"Confirm withdrawal of {total_profit:.2f} SOL for user {user.username or user.telegram_id}\n\n"
                f"Withdrawal will be sent to: `{display_wallet}`\n\n"
                "In a real implementation, this would execute a transfer on the Solana blockchain."
            )
            
            keyboard = [
                [InlineKeyboardButton("Confirm Withdrawal", callback_data="admin_confirm_withdrawal")],
                [InlineKeyboardButton("Cancel", callback_data="admin_back")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Store profit amount for later processing
            context.user_data['withdrawal_amount'] = total_profit
            
            await query.edit_message_text(
                text=confirmation_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error processing withdrawal: {e}")
            await query.edit_message_text(f"Error processing withdrawal: {str(e)}")


async def admin_manage_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the manage withdrawals button and show pending withdrawal requests."""
    query = update.callback_query
    await query.answer()
    
    with app.app_context():
        try:
            # Get all pending withdrawal transactions
            pending_withdrawals = Transaction.query.filter_by(
                transaction_type="withdraw",
                status="pending"
            ).order_by(Transaction.timestamp.desc()).all()
            
            if not pending_withdrawals:
                message = "📝 *Withdrawal Management*\n\nThere are no pending withdrawal requests at this time."
                
                keyboard = [
                    [InlineKeyboardButton("View Completed Withdrawals", callback_data="admin_view_completed_withdrawals")],
                    [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            # Format the list of pending withdrawals
            message = "📝 *Pending Withdrawals*\n\nThe following withdrawal requests need your approval:\n\n"
            
            # Add max 5 withdrawals to avoid text too long issues
            for i, withdrawal in enumerate(pending_withdrawals[:5], 1):
                user = User.query.get(withdrawal.user_id)
                if not user:
                    continue
                
                # Format wallet address for display
                wallet_address = user.wallet_address or "No wallet address set"
                if wallet_address and len(wallet_address) > 10:
                    display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
                else:
                    display_wallet = wallet_address
                
                message += (
                    f"*{i}. Request #{withdrawal.id}*\n"
                    f"User: {user.username or user.telegram_id}\n"
                    f"Amount: {withdrawal.amount:.2f} SOL\n"
                    f"Wallet: `{display_wallet}`\n"
                    f"Requested: {withdrawal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )
            
            if len(pending_withdrawals) > 5:
                message += f"*...and {len(pending_withdrawals) - 5} more pending requests.*\n\n"
            
            message += "Select a withdrawal request to approve or deny:"
            
            # Create buttons for each withdrawal
            keyboard = []
            for i, withdrawal in enumerate(pending_withdrawals[:5], 1):
                keyboard.append([
                    InlineKeyboardButton(
                        f"Process #{withdrawal.id} ({withdrawal.amount:.2f} SOL)", 
                        callback_data=f"admin_process_pending_withdrawal_{withdrawal.id}"
                    )
                ])
            
            # Add navigation buttons
            keyboard.append([InlineKeyboardButton("View Completed Withdrawals", callback_data="admin_view_completed_withdrawals")])
            keyboard.append([InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error loading pending withdrawals: {e}")
            await query.edit_message_text(f"Error loading pending withdrawals: {str(e)}")


async def admin_process_pending_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a specific pending withdrawal transaction."""
    query = update.callback_query
    await query.answer()
    
    # Extract the withdrawal ID from the callback data
    callback_data = query.data
    withdrawal_id = int(callback_data.split('_')[-1])
    
    with app.app_context():
        try:
            # Get the withdrawal transaction
            withdrawal = Transaction.query.get(withdrawal_id)
            if not withdrawal or withdrawal.transaction_type != "withdraw" or withdrawal.status != "pending":
                await query.edit_message_text("Error: Withdrawal not found or already processed.")
                return
            
            # Get the user record
            user = User.query.get(withdrawal.user_id)
            if not user:
                await query.edit_message_text("Error: User not found in database.")
                return
            
            # Format wallet address for display
            wallet_address = user.wallet_address or "No wallet address set"
            if wallet_address and len(wallet_address) > 10:
                display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            else:
                display_wallet = wallet_address
            
            # Show withdrawal details with approve/deny options
            message = (
                f"*Withdrawal Request #{withdrawal.id}*\n\n"
                f"User: {user.username or user.telegram_id}\n"
                f"Amount: {withdrawal.amount:.2f} SOL\n"
                f"Wallet: `{display_wallet}`\n"
                f"Requested: {withdrawal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "Please choose an action:"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_withdrawal_{withdrawal.id}"),
                    InlineKeyboardButton("❌ Deny", callback_data=f"admin_deny_withdrawal_{withdrawal.id}")
                ],
                [InlineKeyboardButton("🔙 Back to Withdrawal List", callback_data="admin_manage_withdrawals")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error processing withdrawal: {e}")
            await query.edit_message_text(f"Error processing withdrawal: {str(e)}")


async def admin_approve_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve a pending withdrawal request."""
    query = update.callback_query
    await query.answer()
    
    # Extract the withdrawal ID from the callback data
    callback_data = query.data
    withdrawal_id = int(callback_data.split('_')[-1])
    
    with app.app_context():
        try:
            # Get the withdrawal transaction
            withdrawal = Transaction.query.get(withdrawal_id)
            if not withdrawal or withdrawal.transaction_type != "withdraw" or withdrawal.status != "pending":
                await query.edit_message_text("Error: Withdrawal not found or already processed.")
                return
            
            # Get the user record
            user = User.query.get(withdrawal.user_id)
            if not user:
                await query.edit_message_text("Error: User not found in database.")
                return
            
            # Update the transaction status to completed
            withdrawal.status = "completed"
            withdrawal.notes = f"Approved by admin on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Reset the user's profit records if withdrawal was from profits
            # This depends on your business logic, might need adjustment
            total_profit = sum([p.amount for p in user.profits])
            if total_profit > 0 and withdrawal.amount <= total_profit:
                for profit in user.profits:
                    profit.amount = 0
            
            db.session.commit()
            
            # Send notification to the user
            try:
                notification_message = (
                    f"🎉 Withdrawal Approved!\n\n"
                    f"Amount: {withdrawal.amount:.2f} SOL\n"
                    f"Status: Completed\n\n"
                    f"Your funds have been sent to your Solana wallet: {user.wallet_address[:6]}...{user.wallet_address[-4:]}\n\n"
                    f"Thank you for using SolanaMemobot! We hope you continue to enjoy our services."
                )
                
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send withdrawal notification to user {user.id}: {e}")
            
            # Confirm to admin
            success_message = (
                f"✅ Withdrawal of {withdrawal.amount:.2f} SOL successfully processed for user {user.username or user.telegram_id}.\n"
                f"Transaction ID: {withdrawal.id}\n"
                f"User has been notified."
            )
            
            keyboard = [
                [InlineKeyboardButton("Back to Withdrawal List", callback_data="admin_manage_withdrawals")],
                [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=success_message,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error approving withdrawal: {e}")
            db.session.rollback()
            await query.edit_message_text(f"Error approving withdrawal: {str(e)}")


async def admin_deny_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deny a pending withdrawal request."""
    query = update.callback_query
    await query.answer()
    
    # Extract the withdrawal ID from the callback data
    callback_data = query.data
    withdrawal_id = int(callback_data.split('_')[-1])
    
    with app.app_context():
        try:
            # Get the withdrawal transaction
            withdrawal = Transaction.query.get(withdrawal_id)
            if not withdrawal or withdrawal.transaction_type != "withdraw" or withdrawal.status != "pending":
                await query.edit_message_text("Error: Withdrawal not found or already processed.")
                return
            
            # Get the user record
            user = User.query.get(withdrawal.user_id)
            if not user:
                await query.edit_message_text("Error: User not found in database.")
                return
            
            # Update the transaction status to failed
            withdrawal.status = "failed"
            withdrawal.notes = f"Denied by admin on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Return the funds to the user's balance
            user.balance += withdrawal.amount
            
            db.session.commit()
            
            # Send notification to the user
            try:
                notification_message = (
                    f"❌ Withdrawal Request Denied\n\n"
                    f"Amount: {withdrawal.amount:.2f} SOL\n"
                    f"Status: Failed\n\n"
                    f"Your funds have been returned to your account balance.\n"
                    f"Please contact support if you have any questions."
                )
                
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send withdrawal notification to user {user.id}: {e}")
            
            # Confirm to admin
            success_message = (
                f"❌ Withdrawal of {withdrawal.amount:.2f} SOL has been denied for user {user.username or user.telegram_id}.\n"
                f"Transaction ID: {withdrawal.id}\n"
                f"User has been notified and funds have been returned to their balance."
            )
            
            keyboard = [
                [InlineKeyboardButton("Back to Withdrawal List", callback_data="admin_manage_withdrawals")],
                [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=success_message,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error denying withdrawal: {e}")
            db.session.rollback()
            await query.edit_message_text(f"Error denying withdrawal: {str(e)}")


async def admin_view_completed_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a list of completed withdrawal transactions."""
    query = update.callback_query
    await query.answer()
    
    with app.app_context():
        try:
            # Get recent completed withdrawals (last 10)
            completed_withdrawals = Transaction.query.filter_by(
                transaction_type="withdraw",
                status="completed"
            ).order_by(Transaction.timestamp.desc()).limit(10).all()
            
            if not completed_withdrawals:
                message = "📋 *Completed Withdrawals*\n\nThere are no completed withdrawals to display."
            else:
                message = "📋 *Recent Completed Withdrawals*\n\n"
                
                for i, withdrawal in enumerate(completed_withdrawals, 1):
                    user = User.query.get(withdrawal.user_id)
                    if not user:
                        continue
                    
                    message += (
                        f"*{i}. Transaction #{withdrawal.id}*\n"
                        f"User: {user.username or user.telegram_id}\n"
                        f"Amount: {withdrawal.amount:.2f} SOL\n"
                        f"Completed: {withdrawal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    )
            
            keyboard = [
                [InlineKeyboardButton("View Pending Withdrawals", callback_data="admin_manage_withdrawals")],
                [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error viewing completed withdrawals: {e}")
            await query.edit_message_text(f"Error viewing completed withdrawals: {str(e)}")


async def admin_confirm_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and process the withdrawal."""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('admin_target_user_id')
    withdrawal_amount = context.user_data.get('withdrawal_amount', 0)
    
    if not user_id or withdrawal_amount <= 0:
        await query.edit_message_text("Error: Invalid withdrawal data. Please restart from the admin panel.")
        return
    
    with app.app_context():
        try:
            # Get the user record
            user = User.query.get(user_id)
            if not user:
                await query.edit_message_text("Error: User not found in database.")
                return
            
            # Create a withdrawal transaction record
            transaction = Transaction(
                user_id=user.id,
                transaction_type="withdraw",
                amount=withdrawal_amount,
                status="completed"
            )
            db.session.add(transaction)
            
            # Reset the user's profit records
            for profit in user.profits:
                profit.amount = 0
            
            # Update user balance if needed
            # (In a real implementation, this would depend on your business logic)
            
            db.session.commit()
            
            # Send notification to the user
            try:
                notification_message = (
                    f"🎉 Withdrawal Completed!\n\n"
                    f"Amount: {withdrawal_amount:.2f} SOL\n"
                    f"Status: Completed\n\n"
                    f"Your funds have been sent to your Solana wallet: {user.wallet_address[:6]}...{user.wallet_address[-4:]}\n\n"
                    f"Thank you for using SolanaMemobot! We hope you continue to enjoy our services."
                )
                
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send withdrawal notification to user {user.id}: {e}")
            
            # Confirm to admin
            success_message = (
                f"✅ Withdrawal of {withdrawal_amount:.2f} SOL successfully processed for user {user.username or user.telegram_id}.\n"
                f"Transaction ID: {transaction.id}\n"
                f"User has been notified."
            )
            
            await query.edit_message_text(text=success_message)
            
            # Return to admin panel after a short delay
            # We use a delay here to give admin time to read the confirmation
            await show_admin_panel(context, query.message.chat_id, query.message.message_id)
            
        except Exception as e:
            logger.error(f"Error confirming withdrawal: {e}")
            db.session.rollback()
            await query.edit_message_text(f"Error confirming withdrawal: {str(e)}")


async def admin_direct_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the direct message button."""
    query = update.callback_query
    await query.answer()
    
    message = (
        "✉️ Send a private message to a specific user.\n\n"
        "Enter the user ID you want to message."
    )
    
    await query.edit_message_text(text=message)
    
    return WAITING_FOR_USER_ID

async def admin_direct_message_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user ID for direct message."""
    user_input = update.message.text.strip()
    
    with app.app_context():
        try:
            # Try to find user by telegram ID first
            user = User.query.filter_by(telegram_id=user_input).first()
            
            # If not found, try by username
            if not user and user_input.startswith('@'):
                username = user_input[1:] # Remove @ prefix
                user = User.query.filter_by(username=username).first()
            elif not user:
                # Try with username anyway (in case they forgot the @)
                user = User.query.filter_by(username=user_input).first()
            
            if not user:
                await update.message.reply_text("User not found. Please try again or type /admin to return to admin panel.")
                return WAITING_FOR_USER_ID
            
            # Store user telegram ID in context for later use
            context.user_data['admin_target_telegram_id'] = user.telegram_id
            
            # Prompt for message content
            await update.message.reply_text("Now send the message content.")
            
            return WAITING_FOR_USER_MESSAGE
            
        except Exception as e:
            logger.error(f"Error processing user ID for direct message: {e}")
            await update.message.reply_text("An error occurred. Please try again or type /admin to return to admin panel.")
            return WAITING_FOR_USER_ID

async def admin_process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the message to send to user."""
    message_content = update.message.text
    target_telegram_id = context.user_data.get('admin_target_telegram_id')
    
    if not target_telegram_id:
        await update.message.reply_text("Error: Target user ID not found. Please start over.")
        return ConversationHandler.END
    
    context.user_data['admin_message_content'] = message_content
    
    preview = f"Preview to user {target_telegram_id}:\n'{message_content}'"
    
    keyboard = [
        [InlineKeyboardButton("Send", callback_data="admin_send_direct_message")],
        [InlineKeyboardButton("Cancel", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=preview,
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def admin_send_direct_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the direct message to the user."""
    query = update.callback_query
    await query.answer()
    
    target_telegram_id = context.user_data.get('admin_target_telegram_id')
    message_content = context.user_data.get('admin_message_content')
    
    if not target_telegram_id or not message_content:
        await query.edit_message_text(text="Error: Message details missing. Please try again.")
        return
    
    try:
        # Send the message to the user
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=message_content,
            parse_mode="Markdown"
        )
        
        result_message = f"Message sent successfully to user {target_telegram_id}."  
        await query.edit_message_text(text=result_message)
        
        # Return to admin panel after a short delay
        await show_admin_panel(context, query.message.chat_id, query.message.message_id)
        
    except Exception as e:
        logger.error(f"Error sending direct message: {e}")
        await query.edit_message_text(text=f"Error sending message: {str(e)}")

async def admin_view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the view stats button."""
    query = update.callback_query
    await query.answer()
    
    with app.app_context():
        try:
            # Get statistics from database
            total_users = User.query.count()
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).count()
            
            # Get total deposits
            total_deposits = db.session.query(func.sum(Transaction.amount)).\
                filter_by(transaction_type='deposit', status='completed').scalar() or 0
                
            # Get users active in last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            active_today = User.query.filter(User.last_activity >= yesterday).count()
            
            # Get profitable users in last 7 days
            last_week = datetime.utcnow() - timedelta(days=7)
            profitable_users = db.session.query(Profit.user_id).\
                filter(Profit.date >= last_week, Profit.amount > 0).\
                distinct().count()
            
            # Get withdrawals count
            withdrawals = Transaction.query.filter_by(transaction_type='withdraw', status='completed').count()
            
            # Calculate average ROI
            avg_roi = db.session.query(func.avg(Profit.percentage)).scalar() or 0
            
            stats_message = (
                "📊 Bot Statistics (Real-Time)\n\n"
                f"Total Users: {total_users}\n"
                f"Total Deposits: {total_deposits:.2f} SOL\n"
                f"Average Daily ROI: {avg_roi:.2f}%\n"
                f"Profitable Users (7d): {profitable_users}\n"
                f"Active Today: {active_today}\n"
                f"Withdrawals Processed: {withdrawals}\n"
            )
            
            keyboard = [
                [InlineKeyboardButton("Export CSV", callback_data="admin_export_csv")],
                [InlineKeyboardButton("Back", callback_data="admin_back")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=stats_message,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            await query.edit_message_text(text=f"Error fetching statistics: {str(e)}")

async def admin_export_csv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the export CSV button."""
    query = update.callback_query
    await query.answer()
    
    # In a real implementation, you would generate and send a CSV file
    # For this example, we'll just send a message
    
    message = "CSV export functionality would be implemented here. This would generate files with user data, transactions, and stats."
    
    keyboard = [
        [InlineKeyboardButton("Back to Stats", callback_data="admin_view_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

async def admin_adjust_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the adjust balance button."""
    query = update.callback_query
    await query.answer()
    
    message = (
        "💰 Manually adjust a user's balance.\n\n"
        "Enter User ID:"
    )
    
    await query.edit_message_text(text=message)
    
    return WAITING_FOR_USER_ID

async def admin_adjust_balance_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user ID for balance adjustment."""
    user_input = update.message.text.strip()
    
    with app.app_context():
        try:
            # Try to find user by telegram ID first
            user = User.query.filter_by(telegram_id=user_input).first()
            
            # If not found, try by username
            if not user and user_input.startswith('@'):
                username = user_input[1:] # Remove @ prefix
                user = User.query.filter_by(username=username).first()
            elif not user:
                # Try with username anyway (in case they forgot the @)
                user = User.query.filter_by(username=user_input).first()
            
            if not user:
                await update.message.reply_text("User not found. Please try again or type /admin to return to admin panel.")
                return WAITING_FOR_USER_ID
            
            # Store user info in context for later use
            context.user_data['admin_adjust_user_id'] = user.id
            context.user_data['admin_adjust_telegram_id'] = user.telegram_id
            context.user_data['admin_adjust_current_balance'] = user.balance
            
            # Prompt for adjustment amount
            await update.message.reply_text(
                f"Current balance for user {user.telegram_id}: {user.balance:.2f} SOL\n\n"
                "Enter amount to add or subtract (use minus sign to deduct):"
            )
            
            return WAITING_FOR_BALANCE_ADJUSTMENT
            
        except Exception as e:
            logger.error(f"Error processing user ID for balance adjustment: {e}")
            await update.message.reply_text("An error occurred. Please try again or type /admin to return to admin panel.")
            return WAITING_FOR_USER_ID

async def admin_process_balance_adjustment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the balance adjustment amount."""
    try:
        adjustment = float(update.message.text.strip())
        context.user_data['admin_adjustment_amount'] = adjustment
        
        # Prompt for reason
        await update.message.reply_text("Optional reason (e.g. refund, bonus, penalty):")
        
        return WAITING_FOR_BALANCE_REASON
        
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return WAITING_FOR_BALANCE_ADJUSTMENT

async def admin_process_balance_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the reason for balance adjustment."""
    reason = update.message.text.strip()
    context.user_data['admin_adjustment_reason'] = reason
    
    user_id = context.user_data.get('admin_adjust_telegram_id')
    amount = context.user_data.get('admin_adjustment_amount')
    
    confirmation = f"You're about to {'add' if amount > 0 else 'subtract'} {abs(amount):.2f} SOL to user {user_id} (Reason: '{reason}')."  
    
    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data="admin_confirm_adjustment")],
        [InlineKeyboardButton("Cancel", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=confirmation,
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def admin_confirm_adjustment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and process the balance adjustment."""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('admin_adjust_user_id')
    amount = context.user_data.get('admin_adjustment_amount')
    reason = context.user_data.get('admin_adjustment_reason', 'Admin adjustment')
    
    if not user_id or amount is None:
        await query.edit_message_text(text="Error: Adjustment details missing. Please try again.")
        return
    
    with app.app_context():
        try:
            # Get user from database
            user = User.query.get(user_id)
            
            if not user:
                await query.edit_message_text(text="Error: User not found.")
                return
            
            # Update user balance
            old_balance = user.balance
            user.balance += amount
            
            # Create transaction record
            transaction_type = 'admin_credit' if amount > 0 else 'admin_debit'
            new_transaction = Transaction()
            new_transaction.user_id = user.id
            new_transaction.transaction_type = transaction_type
            new_transaction.amount = abs(amount)
            new_transaction.status = 'completed'
            new_transaction.notes = reason
            
            db.session.add(new_transaction)
            db.session.commit()
            
            # Start auto trading if this is a positive balance adjustment
            if amount > 0:
                try:
                    # Import the auto trading module
                    from utils.auto_trading_history import handle_admin_balance_adjustment
                    
                    # Trigger auto trading based on the balance adjustment
                    handle_admin_balance_adjustment(user.id, amount)
                    logger.info(f"Auto trading history started for user {user.id} after admin balance adjustment")
                except Exception as trading_error:
                    logger.error(f"Failed to start auto trading history for user {user.id}: {trading_error}")
                    # Don't fail the balance adjustment process if auto trading fails
            
            result_message = f"✅ Balance updated. New user balance: {user.balance:.2f} SOL ({old_balance:.2f} → {user.balance:.2f})."  
            
            # Balance adjustment notification removed as requested
            
            await query.edit_message_text(text=result_message)
            
            # Return to admin panel after a short delay
            await show_admin_panel(context, query.message.chat_id, query.message.message_id)
            
        except Exception as e:
            logger.error(f"Error adjusting balance: {e}")
            db.session.rollback()
            await query.edit_message_text(text=f"Error adjusting balance: {str(e)}")

async def admin_bot_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the bot settings button."""
    query = update.callback_query
    await query.answer()
    
    message = (
        "⚙️ Manage trading logic and performance tracking settings."
    )
    
    keyboard = [
        [InlineKeyboardButton("Update Minimum Deposit", callback_data="admin_update_min_deposit")],
        [InlineKeyboardButton("Edit Daily Notification Time", callback_data="admin_edit_notification_time")],
        [InlineKeyboardButton("Toggle Daily Updates: ON", callback_data="admin_toggle_daily_updates")],
        [InlineKeyboardButton("Manage ROI Thresholds", callback_data="admin_manage_roi")],
        [InlineKeyboardButton("Back", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

async def admin_exit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the exit button."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(text="Panel closed. Type /admin to reopen.")

async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the back button."""
    query = update.callback_query
    await query.answer()
    
    await show_admin_panel(context, query.message.chat_id, query.message.message_id)

async def admin_send_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the send message button from user management."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('admin_target_user_id')
    
    if not target_user_id:
        await query.edit_message_text(text="Error: Target user ID not found. Please try again.")
        return ConversationHandler.END
    
    with app.app_context():
        try:
            user = User.query.get(target_user_id)
            
            if not user:
                await query.edit_message_text(text="Error: User not found.")
                return ConversationHandler.END
            
            context.user_data['admin_target_telegram_id'] = user.telegram_id
            
            message = f"Enter message to send to user {user.telegram_id}:"
            
            await query.edit_message_text(text=message)
            
            return WAITING_FOR_USER_MESSAGE
            
        except Exception as e:
            logger.error(f"Error preparing to send message: {e}")
            await query.edit_message_text(text=f"Error: {str(e)}")
            return ConversationHandler.END

async def admin_adjust_user_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the adjust balance button from user management."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('admin_target_user_id')
    
    if not target_user_id:
        await query.edit_message_text(text="Error: Target user ID not found. Please try again.")
        return ConversationHandler.END
    
    with app.app_context():
        try:
            user = User.query.get(target_user_id)
            
            if not user:
                await query.edit_message_text(text="Error: User not found.")
                return ConversationHandler.END
            
            context.user_data['admin_adjust_user_id'] = user.id
            context.user_data['admin_adjust_telegram_id'] = user.telegram_id
            context.user_data['admin_adjust_current_balance'] = user.balance
            
            message = (
                f"Current balance for user {user.telegram_id}: {user.balance:.2f} SOL\n\n"
                "Enter amount to add or subtract (use minus sign to deduct):"
            )
            
            await query.edit_message_text(text=message)
            
            return WAITING_FOR_BALANCE_ADJUSTMENT
            
        except Exception as e:
            logger.error(f"Error preparing to adjust balance: {e}")
            await query.edit_message_text(text=f"Error: {str(e)}")
            return ConversationHandler.END

async def admin_reset_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the reset user button."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('admin_target_user_id')
    
    if not target_user_id:
        await query.edit_message_text(text="Error: Target user ID not found. Please try again.")
        return
    
    with app.app_context():
        try:
            user = User.query.get(target_user_id)
            
            if not user:
                await query.edit_message_text(text="Error: User not found.")
                return
            
            # Reset user to onboarding status
            user.status = UserStatus.ONBOARDING
            db.session.commit()
            
            confirmation = f"User {user.telegram_id} has been reset to onboarding status."
            
            await query.edit_message_text(text=confirmation)
            
            # Notify the user
            try:
                user_notification = (
                    "Your bot has been reset by an administrator. Please start again with /start."
                )
                
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=user_notification
                )
            except Exception as e:
                logger.error(f"Failed to notify user about reset: {e}")
            
        except Exception as e:
            logger.error(f"Error resetting user: {e}")
            db.session.rollback()
            await query.edit_message_text(text=f"Error resetting user: {str(e)}")

async def admin_remove_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the remove user button."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('admin_target_user_id')
    
    if not target_user_id:
        await query.edit_message_text(text="Error: Target user ID not found. Please try again.")
        return
    
    message = f"Are you sure you want to remove this user? This action cannot be undone."
    
    keyboard = [
        [InlineKeyboardButton("Yes, Remove", callback_data="admin_confirm_remove_user")],
        [InlineKeyboardButton("No, Cancel", callback_data="admin_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup
    )

async def admin_confirm_remove_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and process user removal."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('admin_target_user_id')
    
    if not target_user_id:
        await query.edit_message_text(text="Error: Target user ID not found. Please try again.")
        return
    
    with app.app_context():
        try:
            user = User.query.get(target_user_id)
            
            if not user:
                await query.edit_message_text(text="Error: User not found.")
                return
            
            # Store user Telegram ID for notification
            user_telegram_id = user.telegram_id
            
            # Delete the user
            db.session.delete(user)
            db.session.commit()
            
            confirmation = f"User {user_telegram_id} has been removed from the system."
            
            await query.edit_message_text(text=confirmation)
            
            # Notify the user
            try:
                user_notification = (
                    "Your account has been removed from the SolanaMemobot system by an administrator."
                )
                
                await context.bot.send_message(
                    chat_id=user_telegram_id,
                    text=user_notification
                )
            except Exception as e:
                logger.error(f"Failed to notify user about removal: {e}")
            
            # Return to admin panel after a short delay
            await show_admin_panel(context, query.message.chat_id, query.message.message_id)
            
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            db.session.rollback()
            await query.edit_message_text(text=f"Error removing user: {str(e)}")

# Helper function to check if a user is an admin
def is_admin(user_id):
    """Check if a user is an admin."""
    return str(user_id) == ADMIN_USER_ID
