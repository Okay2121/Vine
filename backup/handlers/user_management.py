import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import func, desc
from app import db, app
from models import User, UserStatus, Transaction, Profit, ReferralCode

# Define the Update type for better type hinting
try:
    from telegram import Update
except ImportError:
    # Fallback for older python-telegram-bot versions
    from telegram.update import Update

logger = logging.getLogger(__name__)

async def view_all_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all registered users with detailed information."""
    query = update.callback_query
    await query.answer()
    
    with app.app_context():
        try:
            # Get all users ordered by registration date (most recent first)
            users = User.query.order_by(desc(User.joined_at)).limit(10).all()
            
            if not users:
                message = (
                    "👥 *All Users*\n\n"
                    "There are currently no registered users in the system."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Back to User Management", callback_data="admin_user_management")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            message = "👥 *All Registered Users*\n\n"
            
            # Add user info for each user
            for idx, user in enumerate(users, 1):
                # Calculate total deposits
                total_deposits = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == "deposit",
                    Transaction.status == "completed"
                ).scalar() or 0.0
                
                # Calculate total withdrawals
                total_withdrawn = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == "withdraw",
                    Transaction.status == "completed"
                ).scalar() or 0.0
                
                # Calculate total profits
                total_profits = db.session.query(func.sum(Profit.amount)).filter(
                    Profit.user_id == user.id
                ).scalar() or 0.0
                
                # Count referrals
                referral_code = ReferralCode.query.filter_by(user_id=user.id).first()
                referral_count = 0
                if referral_code:
                    referral_count = User.query.filter_by(referrer_code_id=referral_code.id).count()
                
                # Format wallet address for readability
                wallet_address = user.wallet_address or "Not set"
                display_wallet = wallet_address
                if wallet_address != "Not set" and len(wallet_address) > 10:
                    display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
                
                # Get registration date
                registration_date = user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "N/A"
                
                # Get referral earnings (5% profit)
                referral_earnings = user.referral_bonus if user.referral_bonus is not None else 0.0
                
                # Create user entry
                user_entry = (
                    f"*User #{idx}*\n"
                    f"• Telegram ID: `{user.telegram_id}`\n"
                    f"• Username: @{user.username or 'No Username'}\n"
                    f"• Wallet: `{display_wallet}`\n"
                    f"• Registration: {registration_date}\n"
                    f"• Total Deposited: {total_deposits:.4f} SOL\n"
                    f"• Total Withdrawn: {total_withdrawn:.4f} SOL\n"
                    f"• Current Balance: {user.balance:.4f} SOL\n"
                    f"• Referral Count: {referral_count}\n"
                    f"• Referral Earnings: {referral_earnings:.4f} SOL\n\n"
                )
                
                message += user_entry
            
            # Add pagination note
            message += "\nShowing 10 most recent users. Use search for specific users."
            
            keyboard = [
                [
                    InlineKeyboardButton("Search User", callback_data="admin_search_user"),
                    InlineKeyboardButton("Export Users (CSV)", callback_data="admin_export_csv")
                ],
                [
                    InlineKeyboardButton("View Active Users", callback_data="admin_view_active_users"),
                    InlineKeyboardButton("Back", callback_data="admin_user_management")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error in view_all_users_callback: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            await query.edit_message_text(
                text=f"Error displaying user list: {str(e)}. Please try again.",
                parse_mode="Markdown"
            )

async def view_active_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display active users with detailed information."""
    query = update.callback_query
    await query.answer()
    
    with app.app_context():
        try:
            # Get active users ordered by join date (most recent first)
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).order_by(desc(User.last_activity)).limit(10).all()
            
            if not active_users:
                message = (
                    "👥 *Active Users*\n\n"
                    "There are currently no active users in the system."
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("View All Users", callback_data="admin_view_all_users"),
                        InlineKeyboardButton("Back", callback_data="admin_user_management")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            message = "👥 *Active Users*\n\n"
            
            # Add user info for each active user
            for idx, user in enumerate(active_users, 1):
                # Calculate total deposits
                total_deposits = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == "deposit",
                    Transaction.status == "completed"
                ).scalar() or 0.0
                
                # Calculate total withdrawals
                total_withdrawn = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == "withdraw",
                    Transaction.status == "completed"
                ).scalar() or 0.0
                
                # Calculate total profits
                total_profits = db.session.query(func.sum(Profit.amount)).filter(
                    Profit.user_id == user.id
                ).scalar() or 0.0
                
                # Count referrals
                referral_code = ReferralCode.query.filter_by(user_id=user.id).first()
                referral_count = 0
                if referral_code:
                    referral_count = User.query.filter_by(referrer_code_id=referral_code.id).count()
                
                # Format wallet address for readability
                wallet_address = user.wallet_address or "Not set"
                display_wallet = wallet_address
                if wallet_address != "Not set" and len(wallet_address) > 10:
                    display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
                
                # Get last activity timestamp
                last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "N/A"
                
                # Get referral earnings (5% profit)
                referral_earnings = user.referral_bonus if user.referral_bonus is not None else 0.0
                
                # Create user entry
                user_entry = (
                    f"*User #{idx}*\n"
                    f"• Telegram ID: `{user.telegram_id}`\n"
                    f"• Username: @{user.username or 'No Username'}\n"
                    f"• Wallet: `{display_wallet}`\n"
                    f"• Registration: {user.joined_at.strftime('%Y-%m-%d')}\n"
                    f"• Total Deposited: {total_deposits:.4f} SOL\n"
                    f"• Total Withdrawn: {total_withdrawn:.4f} SOL\n"
                    f"• Current Balance: {user.balance:.4f} SOL\n"
                    f"• Referral Count: {referral_count}\n"
                    f"• Referral Earnings: {referral_earnings:.4f} SOL\n"
                    f"• Last Active: {last_activity}\n\n"
                )
                
                message += user_entry
            
            # Add pagination note
            message += "\nShowing 10 most active users. Use search for specific users."
            
            keyboard = [
                [
                    InlineKeyboardButton("Search User", callback_data="admin_search_user"),
                    InlineKeyboardButton("Export Users (CSV)", callback_data="admin_export_csv")
                ],
                [
                    InlineKeyboardButton("View All Users", callback_data="admin_view_all_users"),
                    InlineKeyboardButton("Back", callback_data="admin_user_management")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error in view_active_users_callback: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            await query.edit_message_text(
                text=f"Error displaying active users: {str(e)}. Please try again.",
                parse_mode="Markdown"
            )

async def search_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the search user button."""
    query = update.callback_query
    await query.answer()
    
    message = (
        "🔍 *Search Users*\n\n"
        "Please enter a Telegram ID or Username to search for."
    )
    
    await query.edit_message_text(
        text=message,
        parse_mode="Markdown"
    )
    
    # Need to return a conversation state for handling the search input
    from handlers.admin import WAITING_FOR_USER_ID
    return WAITING_FOR_USER_ID