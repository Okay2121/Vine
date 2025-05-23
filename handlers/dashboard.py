import logging
import random
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from app import db, app
from models import User, UserStatus, Profit, Transaction, TradingPosition
from utils.trading import calculate_projected_roi
from utils.roi_system import get_user_roi_metrics, get_cycle_history
from config import MIN_DEPOSIT

logger = logging.getLogger(__name__)

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the profit dashboard with trading stats."""
    # Try to import the message cleanup helpers
    try:
        from utils.message_handlers import send_dashboard_message, cleanup_previous_messages
        # Clean up any welcome or start messages as we're moving to the dashboard state
        await cleanup_previous_messages(update, context, ['welcome_message', 'start_message', 'how_it_works'])
    except ImportError:
        logger.debug("Message cleanup module not available")
        
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        
        # Edit the existing message
        await show_dashboard(context, chat_id, message_id, user_id)
    else:
        # Handle direct command
        user_id = update.effective_user.id
        await show_dashboard(context, update.effective_chat.id, None, user_id)


async def show_dashboard(context, chat_id, message_id=None, user_id=None):
    """Show the profit dashboard with trading performance metrics."""
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                # If somehow the user doesn't exist in the database
                error_text = "Please start the bot with /start first."
                if message_id:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=error_text
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=error_text
                    )
                return
            
            # Set initial values for all users
            total_profit_amount = 0
            total_profit_percentage = 0
            today_profit_amount = 0
            today_profit_percentage = 0
            streak = 0
            projected_roi = 30  # Default projected ROI
            current_balance = user.balance
            
            # If the user hasn't deposited yet, set a small minimum initial deposit to avoid division by zero
            if user.initial_deposit == 0:
                user.initial_deposit = max(0.01, user.balance)  # Set a small minimum to avoid division by zero
                db.session.commit()
            
            # Only calculate real stats if user has actual activity
            if user.status == UserStatus.ACTIVE and user.balance >= MIN_DEPOSIT:
                # Calculate profits and stats
                total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
                total_profit_percentage = (total_profit_amount / user.initial_deposit) * 100 if user.initial_deposit > 0 else 0
                
                # Get today's profit
                today = datetime.utcnow().date()
                today_profit = Profit.query.filter_by(user_id=user.id, date=today).first()
                today_profit_amount = today_profit.amount if today_profit else 0
                today_profit_percentage = today_profit.percentage if today_profit else 0
                
                # Calculate profit streak
                streak = 0
                current_date = today
                while True:
                    profit = Profit.query.filter_by(user_id=user.id, date=current_date).first()
                    if profit and profit.amount > 0:
                        streak += 1
                        current_date -= timedelta(days=1)
                    else:
                        break
                
                # Calculate projected monthly ROI based on recent performance
                projected_roi = calculate_projected_roi(user.id)
            
            # Get 7-Day 2x ROI metrics from the ROI system
            roi_metrics = get_user_roi_metrics(user.id)
            
            # Set ROI variables based on metrics
            has_active_cycle = roi_metrics['has_active_cycle']
            days_active = roi_metrics['days_elapsed'] if has_active_cycle else min(7, (datetime.utcnow().date() - user.joined_at.date()).days)
            days_left = roi_metrics['days_remaining'] if has_active_cycle else max(0, 7 - days_active)
            
            # Calculate progress towards 2x goal
            goal_progress = roi_metrics['progress_percentage'] if has_active_cycle else min(100, (total_profit_percentage / 100.0) * 100)
            progress_blocks = int(min(14, goal_progress / (100/14)))
            progress_bar = f"[{'▓' * progress_blocks}{'░' * (14 - progress_blocks)}]"
            
            # Get target and current amounts
            if has_active_cycle:
                target_amount = roi_metrics['target_balance']
                current_amount = roi_metrics['current_balance']
            else:
                # Fall back to standard calculation
                target_amount = user.initial_deposit * 2
                current_amount = user.balance + total_profit_amount
                
            amount_progress = min(100, (current_amount / target_amount) * 100) if target_amount > 0 else 0
            
            # Format the dashboard message with improved 2x2 grid layout and emoji icons
            current_balance = user.balance + total_profit_amount
            
            dashboard_message = (
                "📊 *Profit Dashboard*\n\n"
            )
            
            # First row - Current balance with clear formatting
            dashboard_message += (
                f"• *Balance:* {current_balance:.2f} SOL _(Initial {user.initial_deposit:.2f} SOL + {total_profit_amount:.2f} SOL profit)_\n"
                f"• *Today's Profit:* {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}% of balance)\n"
                f"• *Total Profit:* {total_profit_percentage:.1f}% ({total_profit_amount:.2f} SOL)\n"
            )
            
            # Add streak with fire emoji for gamification
            streak_text = ""
            if streak > 0:
                fire_emojis = "🔥" * min(3, streak)
                streak_text = f"• *Profit Streak:* {streak} days {fire_emojis}\n"
            else:
                streak_text = "• *Profit Streak:* Start your streak today!\n"
                
            dashboard_message += streak_text
            
            # Add 7-Day 2x ROI plan details
            dashboard_message += f"• *ROI Plan:* 2x in 7 Days\n"
            dashboard_message += f"• *Day:* {days_active}\n\n"
            
            # Add 2x goal progress bar with animations
            dashboard_message += "• *Progress Toward 2x Goal:*\n"
            dashboard_message += f"⏳ {progress_bar} {goal_progress:.0f}% Complete\n"
            # Show motivational message based on progress
            progress_ratio = 0 if days_active == 0 else goal_progress / (days_active/7*100)
            if progress_ratio >= 1.1:
                dashboard_message += "You're ahead of schedule to double your SOL! Amazing! 🚀\n\n"
            elif progress_ratio >= 0.9:
                dashboard_message += "You're right on track to double your SOL! 👍\n\n"
            else:
                dashboard_message += "Keep going - you're working toward doubling your SOL! 💪\n\n"
            
            # Add goal completion tracker with real values
            dashboard_message += "• *Goal Completion Tracker:*\n"
            dashboard_message += f"🎯 Target: {target_amount:.2f} SOL (from {user.initial_deposit:.2f} SOL)\n"
            dashboard_message += f"Current: {current_amount:.2f} SOL\n"
            
            # Calculate progress bars using Unicode blocks for visual appeal
            amount_blocks = int(min(10, amount_progress / 10))
            amount_bar = f"[{'█' * amount_blocks}{'░' * (10 - amount_blocks)}] {amount_progress:.1f}% to goal\n\n"  
            dashboard_message += amount_bar
            
            # Add a trust-building reminder message - different messages based on deposit status
            if user.status == UserStatus.ACTIVE and user.balance >= MIN_DEPOSIT:
                tips_message = random.choice([
                    "Your bot is working 24/7 to find the best trading opportunities for you.",
                    "THRIVE automatically buys low and sells high, you just watch your profits grow.",
                    "Trading happens automatically - we do the work, you keep the profits.",
                    "Every day brings new opportunities in the Solana memecoin market.",
                    "Your funds remain secure while THRIVE trades the market for you."
                ])
            else:
                tips_message = random.choice([
                    "Add funds to start trading with the smartest Solana memecoin bot.",
                    "Make a deposit to begin your automated trading journey.",
                    "Solana memecoin trading can start as soon as you deposit SOL.",
                    "Your dashboard is ready - add SOL to see it in action!",
                    "Your full trading dashboard is activated - deposit anytime to start earning."
                ])
            
            dashboard_message += f"_💡 {tips_message}_"
            
            # New button layout based on user requirements
            keyboard = [
                # Row 1 - Primary actions
                [
                    InlineKeyboardButton("💰 Deposit", callback_data="deposit"),
                    InlineKeyboardButton("💸 Withdrawal", callback_data="withdraw_profit")
                ],
                # Row 2 - Performance and Referral
                [
                    InlineKeyboardButton("📊 Performance", callback_data="trading_history"),
                    InlineKeyboardButton("👥 Referral", callback_data="referral")
                ],
                # Row 3 - Support and FAQ
                [
                    InlineKeyboardButton("🛟 Customer Support", callback_data="support"),
                    InlineKeyboardButton("❓ FAQ", callback_data="faqs")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Either edit existing message or send new one
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=dashboard_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=dashboard_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except SQLAlchemyError as e:
            logger.error(f"Database error during dashboard display: {e}")
            db.session.rollback()
            
            error_text = "Sorry, there was an error retrieving your dashboard. Please try again later."
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=error_text
                )


async def withdraw_profit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the withdraw profit button with real-time processing."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot with /start first.")
                return
            
            # Calculate profits and available balance
            total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
            total_profit_percentage = (total_profit_amount / user.initial_deposit) * 100 if user.initial_deposit > 0 else 0
            available_balance = user.balance
            
            # Check if user has a wallet address
            wallet_address = user.wallet_address or "No wallet address found"
            
            # Format wallet address for display (show only part of it)
            if wallet_address and len(wallet_address) > 10:
                display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            else:
                display_wallet = wallet_address
            
            # Show initial withdrawal screen with real-time processing
            withdrawal_message = (
                "💰 *Withdraw Funds*\n\n"
                f"Available Balance: *{available_balance:.2f} SOL*\n"
                f"Total Profit: *{total_profit_amount:.2f} SOL* ({total_profit_percentage:.1f}%)\n\n"
                f"Withdrawal Wallet: `{display_wallet}`\n\n"
                "Select an option below to withdraw your funds:"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("💸 Withdraw All", callback_data="withdraw_all"),
                    InlineKeyboardButton("💲 Withdraw Profit", callback_data="withdraw_profit_only")
                ],
                [InlineKeyboardButton("📈 Custom Amount", callback_data="withdraw_custom")],
                [InlineKeyboardButton("🏠 Back to Dashboard", callback_data="view_dashboard")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=withdrawal_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during withdraw display: {e}")
            db.session.rollback()
            
            error_text = "Sorry, there was an error retrieving your withdrawal information. Please try again later."
            await query.edit_message_text(text=error_text)


async def withdraw_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process withdrawing all funds in real-time."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    
    # Show a simple processing message
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="💸 *Processing...*",
        parse_mode="Markdown"
    )
    
    # Brief pause for visual feedback
    await asyncio.sleep(0.5)
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot with /start first.")
                return
            
            # Get current balance and create withdrawal transaction
            withdrawal_amount = user.balance
            
            if withdrawal_amount <= 0:
                # No funds to withdraw
                no_funds_message = (
                    "⚠️ *Withdrawal Failed*\n\n"
                    "You don't have any funds available to withdraw. Please deposit funds first."
                )
                
                keyboard = [[InlineKeyboardButton("🏠 Back to Dashboard", callback_data="view_dashboard")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=no_funds_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            # Create transaction record with pending status
            new_transaction = Transaction(
                user_id=user.id,
                transaction_type="withdraw",
                amount=withdrawal_amount,
                timestamp=datetime.utcnow(),
                status="pending",
                notes="Full balance withdrawal pending admin approval"
            )
            db.session.add(new_transaction)
            
            # Reserve the balance for withdrawal but don't reset it
            # The admin will either approve (complete the withdrawal) or deny (return the funds)
            previous_balance = user.balance
            user.balance = 0
            db.session.commit()
            
            # Format message for pending withdrawal
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Show pending withdrawal message
            success_message = (
                "⏳ *Withdrawal Request Submitted*\n\n"
                f"Amount: *{withdrawal_amount:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:]}\n"
                f"Request ID: #{new_transaction.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been submitted and is pending approval by an administrator. "
                "You will be notified once your withdrawal has been processed.\n\n"
                "💰 *Current Balance: 0.00 SOL*"
            )
            
            keyboard = [
                [InlineKeyboardButton("💸 View Transaction", callback_data="view_tx")],
                [InlineKeyboardButton("💪 Make Another Deposit", callback_data="deposit")],
                [InlineKeyboardButton("🏠 Back to Dashboard", callback_data="view_dashboard")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=success_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during withdrawal: {e}")
            db.session.rollback()
            
            error_text = "⚠️ Sorry, there was an error processing your withdrawal. Please try again later."
            
            keyboard = [[InlineKeyboardButton("🏠 Back to Dashboard", callback_data="view_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=error_text,
                reply_markup=reply_markup
            )


async def withdraw_profit_only_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process withdrawing only profits in real-time."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    
    # Show a simple processing message
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="💸 *Processing...*",
        parse_mode="Markdown"
    )
    
    # Brief pause for visual feedback
    await asyncio.sleep(0.5)
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot with /start first.")
                return
            
            # Calculate profits
            total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
            
            if total_profit_amount <= 0:
                # No profits to withdraw
                no_profits_message = (
                    "⚠️ *Withdrawal Failed*\n\n"
                    "You don't have any profits available to withdraw at this time.\n\n"
                    "Continue trading to generate profits that you can withdraw."
                )
                
                keyboard = [[InlineKeyboardButton("🏠 Back to Dashboard", callback_data="view_dashboard")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=no_profits_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            # Create transaction record with pending status
            new_transaction = Transaction(
                user_id=user.id,
                transaction_type="withdraw",
                amount=total_profit_amount,
                timestamp=datetime.utcnow(),
                status="pending",
                notes="Profit withdrawal pending admin approval"
            )
            db.session.add(new_transaction)
            
            # Reserve the amount from user's balance but don't subtract yet
            # The admin will either approve (complete the withdrawal) or deny (return the funds)
            user.balance -= total_profit_amount
            user.balance = max(0, user.balance)  # Ensure we don't go negative
            db.session.commit()
            
            # Format message for pending withdrawal
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Show pending withdrawal message
            success_message = (
                "⏳ *Withdrawal Request Submitted*\n\n"
                f"Amount: *{total_profit_amount:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:]}\n"
                f"Request ID: #{new_transaction.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been submitted and is pending approval by an administrator. "
                "You will be notified once your withdrawal has been processed.\n\n"
                f"💰 *Current Balance: {user.balance:.2f} SOL*"
            )
            
            keyboard = [
                [InlineKeyboardButton("💸 View Transaction", callback_data="view_tx")],
                [InlineKeyboardButton("🏠 Back to Dashboard", callback_data="view_dashboard")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=success_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during profit withdrawal: {e}")
            db.session.rollback()
            
            error_text = "⚠️ Sorry, there was an error processing your profit withdrawal. Please try again later."
            
            keyboard = [[InlineKeyboardButton("🏠 Back to Dashboard", callback_data="view_dashboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=error_text,
                reply_markup=reply_markup
            )


async def reinvest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the reinvest button."""
    query = update.callback_query
    await query.answer()
    
    reinvest_explanation = (
        "🔄 *Reinvest Profits*\n\n"
        "Reinvesting your profits allows you to compound your returns over time. "
        "In a real trading scenario, reinvested profits would be used to increase your trading position sizes.\n\n"
        "The power of compound interest means that reinvesting can significantly boost your overall returns.\n\n"
        "For example, reinvesting a 1% daily profit instead of withdrawing it can lead to approximately "
        "37% monthly returns instead of 30%.\n\n"
        "In this simulation, all profits are automatically reinvested to maximize your returns."
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=reinvest_explanation,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def transaction_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's transaction history with deposits, withdrawals, buys, and sells."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot with /start first.")
                return
            
            # Get user's transactions
            transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
            
            if transactions:
                history_message = "📜 *TRANSACTION HISTORY*\n\n📊 Your last 10 transactions with tracking links\n───────────────────\n\n"
                
                for tx in transactions:
                    # Format the date
                    date_str = tx.timestamp.strftime("%Y-%m-%d %H:%M")
                    
                    # Create improved trade record format
                    if tx.transaction_type in ["buy", "sell"] and tx.token_name:
                        # This is a trade transaction - use enhanced format
                        trade_emoji = "🟢" if tx.transaction_type == "buy" else "🔴"
                        trade_type = "Entry" if tx.transaction_type == "buy" else "Exit"
                        
                        # Extract additional trade details from notes if available
                        price = 0.0
                        roi_percentage = None
                        trade_strategy = "Auto"
                        
                        if hasattr(tx, 'notes') and tx.notes:
                            notes = str(tx.notes)
                            # Try to extract price and ROI from notes
                            if "price" in notes.lower():
                                try:
                                    price_match = re.search(r"price[:\s]+([0-9.]+)", notes.lower())
                                    if price_match:
                                        price = float(price_match.group(1))
                                except:
                                    pass
                            
                            if "roi" in notes.lower() or "profit" in notes.lower():
                                try:
                                    roi_match = re.search(r"(roi|profit)[:\s]+([\+\-]?[0-9.]+)%", notes.lower())
                                    if roi_match:
                                        roi_percentage = float(roi_match.group(2))
                                except:
                                    pass
                                    
                            if "strategy" in notes.lower() or "type" in notes.lower():
                                try:
                                    strategy_match = re.search(r"(strategy|type)[:\s]+([a-zA-Z]+)", notes.lower())
                                    if strategy_match:
                                        trade_strategy = strategy_match.group(2).capitalize()
                                except:
                                    pass
                        
                        # Add enhanced trade details
                        history_message += f"{trade_emoji} *Token: ${tx.token_name}*\n"
                        
                        # Add price information
                        if price > 0:
                            history_message += f"• *{trade_type}:* ${price:.6f}\n"
                        else:
                            history_message += f"• *{trade_type}:* {tx.amount:.2f} SOL\n"
                        
                        # Add ROI if available (for sell transactions)
                        if tx.transaction_type == "sell" and roi_percentage is not None:
                            roi_emoji = "📈" if roi_percentage > 0 else "📉"
                            history_message += f"• *ROI:* {roi_emoji} {roi_percentage:.1f}%\n"
                        
                        # Add trade strategy
                        history_message += f"• *Trade Type:* {trade_strategy}\n"
                        
                        # Add date
                        history_message += f"• *Date:* {date_str}\n"
                        
                        # Add transaction hash as clickable link if available
                        if tx.tx_hash:
                            # Create a Solana Explorer link for the transaction
                            explorer_url = f"https://solscan.io/tx/{tx.tx_hash}"
                            history_message += f"• *TX:* [View on Solscan]({explorer_url})\n"
                    
                    else:
                        # For non-trade transactions (deposits, withdrawals, etc.)
                        if tx.transaction_type == "deposit":
                            tx_emoji = "⬇️"
                        elif tx.transaction_type == "withdraw":
                            tx_emoji = "⬆️"
                        else:
                            tx_emoji = "🔄"
                        
                        # Add transaction detail
                        if tx.token_name:
                            history_message += f"{tx_emoji} *{tx.transaction_type.title()}*: {tx.amount:.4f} SOL of {tx.token_name}\n"
                        else:
                            history_message += f"{tx_emoji} *{tx.transaction_type.title()}*: {tx.amount:.4f} SOL\n"
                        
                        history_message += f"• *Date:* {date_str}\n"
                        history_message += f"• *Status:* {tx.status.title()}\n"
                        
                        # Add transaction hash as clickable link with enhanced styling if available
                        if tx.tx_hash:
                            # Create a Solana Explorer link for the transaction
                            explorer_url = f"https://solscan.io/tx/{tx.tx_hash}"
                            history_message += f"• *TX:* [View on Solscan]({explorer_url})\n"
                        
                        # Add notes if available
                        if hasattr(tx, 'notes') and tx.notes:
                            notes = str(tx.notes)
                            if len(notes) > 50:  # Truncate long notes
                                notes = notes[:47] + "..."
                            history_message += f"• *Info:* _{notes}_\n"
                    
                    history_message += "───────────────────\n\n"
            else:
                history_message = "📜 *Transaction History*\n\n*No transactions found.*\n\nStart trading to see your transaction history here!"
            
            keyboard = [
                [
                    InlineKeyboardButton("📈 Export CSV", callback_data="export_transactions"),
                    InlineKeyboardButton("🔙 Back", callback_data="trading_history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=history_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during transaction history display: {e}")
            db.session.rollback()
            
            error_text = "Sorry, there was an error retrieving your transaction history. Please try again later."
            await query.edit_message_text(text=error_text)


async def my_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's wallet information."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot with /start first.")
                return
            
            wallet_address = user.wallet_address or "Not set"
            
            wallet_message = (
                "👛 *My Wallet*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📌 *Your Solana Wallet:*\n"
                f"`{wallet_address}`\n\n"
                "💰 *Total Deposited:*\n"
                f"*{user.initial_deposit:.2f} SOL*\n\n"
                "💸 *Current Balance:*\n"
                f"*{user.balance:.2f} SOL*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "*Note:* You can use this wallet for deposits and withdrawals. "
                "All profits are automatically transferred to this wallet."
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("📋 Copy Address", callback_data="copy_address"),
                    InlineKeyboardButton("🔄 Change Wallet", callback_data="change_wallet")
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data="trading_history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=wallet_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during wallet display: {e}")
            db.session.rollback()
            
            error_text = "Sorry, there was an error retrieving your wallet information. Please try again later."
            await query.edit_message_text(text=error_text)


async def more_options_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the More Options button that shows additional functionality."""
    query = update.callback_query
    await query.answer()
    
    more_options_message = (
        "⚙️ *Additional Options*\n\n"
        "Select from these additional features:\n\n"
    )
    
    keyboard = [
        # Row 1 - My Wallet and Referral Program
        [
            InlineKeyboardButton("👛 My Wallet", callback_data="my_wallet"),
            InlineKeyboardButton("👥 Referral", callback_data="referral")
        ],
        # Row 2 - Notifications and Support
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="notifications"),
            InlineKeyboardButton("🛟 Support", callback_data="support")
        ],
        # Row 3 - FAQ and Back
        [
            InlineKeyboardButton("❓ FAQ", callback_data="faqs"),
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=more_options_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle notifications settings."""
    query = update.callback_query
    await query.answer()
    
    notification_message = (
        "🔔 *Notification Settings*\n\n"
        "Control how and when you receive updates from your THRIVE bot.\n\n"
        "✅ *Currently Enabled:*\n"
        "• Daily profit reports\n"
        "• Trading position updates\n"
        "• Deposit confirmations\n\n"
        "❌ *Currently Disabled:*\n"
        "• Price alerts\n"
        "• Weekly summary reports\n"
        "• Market news updates\n\n"
        "You can customize your notification preferences using the buttons below."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Enable All", callback_data="enable_all_notifications"),
            InlineKeyboardButton("❌ Disable All", callback_data="disable_all_notifications")
        ],
        [
            InlineKeyboardButton("⚙️ Customize", callback_data="customize_notifications"),
            InlineKeyboardButton("🔙 Back", callback_data="trading_history")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=notification_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show support options."""
    query = update.callback_query
    await query.answer()
    
    support_message = (
        "🛟 *THRIVE Support*\n\n"
        "We're here to help! Choose from the options below to get the support you need:\n\n"
        "💬 *Live Chat*: Talk to a support agent directly\n"
        "📚 *FAQs*: Browse our frequently asked questions\n"
        "📝 *Submit Ticket*: Create a support ticket for complex issues\n"
        "📞 *Contact*: Find our phone and email contact information\n\n"
        "Our support team is available 24/7 to assist you with any questions or concerns."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💬 Live Chat", callback_data="live_chat"),
            InlineKeyboardButton("📚 FAQs", callback_data="faqs")
        ],
        [
            InlineKeyboardButton("📝 Submit Ticket", callback_data="submit_ticket"),
            InlineKeyboardButton("🔙 Back", callback_data="more_options")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=support_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def trading_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the performance page with trading history and 7-Day 2x ROI plan tracking."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot with /start first.")
                return
                
            # Get 7-Day 2x ROI metrics for more accurate tracking
            roi_metrics = get_user_roi_metrics(user.id)
            
            # Calculate overall performance metrics
            total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
            total_profit_percentage = (total_profit_amount / user.initial_deposit) * 100 if user.initial_deposit > 0 else 0
            
            # Calculate 7-day performance (focused on 7-Day 2x ROI plan)
            seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
            days_active = min(7, (datetime.utcnow().date() - user.joined_at.date()).days)
            days_left = max(0, 7 - days_active)
            
            # Get daily profit data for the last 7 days (or however many days the user has been active)
            daily_profits = []
            current_date = datetime.utcnow().date()
            
            # Calculate target amount (2x initial deposit)
            target_amount = user.initial_deposit * 2.0
            current_amount = user.balance + total_profit_amount
            amount_needed = max(0, target_amount - current_amount)
            
            # Collect daily performance data
            for i in range(min(7, days_active)):
                day_date = current_date - timedelta(days=i)
                day_profit = Profit.query.filter_by(user_id=user.id, date=day_date).first()
                if day_profit:
                    percentage = day_profit.percentage
                    day_data = f"Day {days_active-i}: +{percentage:.1f}%"
                    daily_profits.insert(0, day_data)  # Insert at beginning to maintain chronological order
            
            # Ensure we have data for all active days (fill with zeros if missing)
            while len(daily_profits) < days_active:
                day_num = len(daily_profits) + 1
                daily_profits.append(f"Day {day_num}: +0.0%")
                
            # Calculate progress toward 2x goal
            goal_progress = min(100, (total_profit_percentage / 100.0) * 100)
            progress_blocks = int(min(14, goal_progress / (100/14)))
            progress_bar = f"[{'██████████' if progress_blocks >= 10 else '█' * progress_blocks}{'░' * (14 - progress_blocks)}] {goal_progress:.0f}% complete"
            
            # Calculate current streak
            streak = 0
            current_date = datetime.utcnow().date()
            while True:
                profit = Profit.query.filter_by(user_id=user.id, date=current_date).first()
                if profit and profit.amount > 0:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break
                    
            # Build the 7-Day Performance Tracker message
            performance_message = (
                "*Performance Tracker*\n\n"
                f"• *Initial Deposit:* {user.initial_deposit:.2f} SOL\n"
                f"• *Current Balance:* {current_amount:.2f} SOL\n"
                f"• *Total Profit:* +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)\n"
                f"• *Cycle:* Day {days_active} of 7\n\n"
            )
            
            # Add motivational message based on remaining amount
            if amount_needed > 0:
                performance_message += f"Only {amount_needed:.1f} SOL left to reach your target!\n\n"
            else:
                performance_message += f"Congratulations! You've reached your 2x target! 🎉\n\n"
            
            # Add daily performance breakdown
            performance_message += "*Daily Performance:*\n"
            for day_data in daily_profits:
                performance_message += f"{day_data}\n"
                
            if days_active < 7:
                performance_message += "(Tomorrow's boost incoming...)\n\n"
            else:
                performance_message += "\n"
                
            # Add streak info
            if streak > 0:
                performance_message += f"*Current Streak:*\n🔥 {streak} Green {'Days' if streak > 1 else 'Day'} in a Row\n"
                
                # Find the best day
                best_day_profit = Profit.query.filter_by(user_id=user.id).order_by(Profit.percentage.desc()).first()
                if best_day_profit:
                    performance_message += f"Best Day So Far: +{best_day_profit.percentage:.1f}%\n\n"
                    
            # Get trade statistics - count wins and losses
            trades = Transaction.query.filter_by(
                user_id=user.id
            ).filter(
                Transaction.transaction_type.in_(['buy', 'sell'])
            ).order_by(
                Transaction.timestamp.desc()
            ).all()
            
            # Count wins and losses
            profitable_trades = 0
            loss_trades = 0
            today = datetime.utcnow().date()
            today_trades = 0
            
            for trade in trades:
                if trade.transaction_type == 'sell' and hasattr(trade, 'notes') and trade.notes:
                    # Notes field often contains profit/loss info
                    if 'profit' in str(trade.notes).lower():
                        profitable_trades += 1
                    elif 'loss' in str(trade.notes).lower():
                        loss_trades += 1
                        
                    # Count today's trades
                    if trade.timestamp.date() == today:
                        today_trades += 1
            
            # Add trading stats section with enhanced visual formatting
            performance_message += "\n📊 *TRADING STATS*\n"
            
            total_trades = profitable_trades + loss_trades
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Enhanced visual display with block styling
            performance_message += "┌─────────────────────────┐\n"
            performance_message += f"│ ✅ Wins:  {profitable_trades:2d}               │\n"
            performance_message += f"│ ❌ Losses: {loss_trades:2d}               │\n"
            
            if total_trades > 0:
                # Create a visual win rate indicator with emojis
                win_indicators = "🟢" * min(5, int(win_rate/20 + 0.5))
                empty_indicators = "⚪" * (5 - len(win_indicators))
                win_rate_display = win_indicators + empty_indicators
                
                performance_message += f"│ Win Rate: {win_rate:.0f}%  {win_rate_display} │\n"
                
                # Show recent trading activity
                if today_trades > 0:
                    performance_message += f"│ Today's Trades: {today_trades:2d}         │\n"
                else:
                    performance_message += "│ No trades completed today  │\n"
                    
                # Add trading streak if applicable
                if profitable_trades > loss_trades:
                    performance_message += "│ 🔥 Profitable trading!      │\n"
                
            else:
                performance_message += "│ No trading history yet     │\n"
                performance_message += "│ Deposit to start trading!  │\n"
                
            performance_message += "└─────────────────────────┘\n"
                
            # Add time left in cycle
            if days_left > 0:
                performance_message += f"\n*Time Left in Cycle:*\n{days_left} {'days' if days_left > 1 else 'day'} left to complete this 7-day goal!\n"
            else:
                performance_message += f"\n*Time Left in Cycle:*\nYour 7-day cycle is complete! Start a new one by depositing more SOL.\n"
            
            # Show recent transactions button if there are trades
            keyboard = []
            
            # Add view transactions button if there are trades
            if total_trades > 0:
                keyboard.append([
                    InlineKeyboardButton("🔍 View Transactions", callback_data="transaction_history"),
                ])
            
            # Add deposit and withdraw options
            keyboard.append([
                InlineKeyboardButton("💲 Deposit More", callback_data="deposit"),
                InlineKeyboardButton("💰 Withdraw", callback_data="withdraw_profit")
            ])
            
            # Add back button
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")
            ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=performance_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during performance display: {e}")
            db.session.rollback()
            
            error_text = "Sorry, there was an error retrieving your performance data. Please try again later."
            await query.edit_message_text(text=error_text)


async def view_positions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's trading positions with real-time token performance."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot with /start first.")
                return
            
            # Get user's trading positions
            positions = TradingPosition.query.filter_by(user_id=user.id, status="open").all()
            
            if positions:
                history_message = "📈 *Current Trading Positions*\n\n"
                
                for position in positions:
                    # Calculate profit/loss
                    pl_amount = (position.current_price - position.entry_price) * position.amount
                    pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                    
                    # Determine emoji based on profit/loss
                    if pl_percentage > 0:
                        pl_emoji = "📈"
                    elif pl_percentage < 0:
                        pl_emoji = "📉"
                    else:
                        pl_emoji = "↔️"
                    
                    # Format date
                    date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                    
                    # Add position detail
                    history_message += f"*{position.token_name}* {pl_emoji} {pl_percentage:.1f}%\n"
                    history_message += f"Amount: {position.amount:.6f} SOL\n"
                    history_message += f"Entry: ${position.entry_price:.6f}\n"
                    history_message += f"Current: ${position.current_price:.6f}\n"
                    history_message += f"P/L: {pl_amount:.6f} SOL\n"
                    history_message += f"Opened: {date_str}\n\n"
            else:
                # If no positions, show simulated ones
                history_message = "📈 *Current Trading Positions*\n\n"
                
                # Create some simulated positions for demonstration
                simulated_positions = [
                    {
                        "token": "BONK",
                        "amount": 150000,
                        "entry": 0.00000231,
                        "current": 0.00000249,
                        "date": "2025-05-05 18:24"
                    },
                    {
                        "token": "WIF",
                        "amount": 0.5,
                        "entry": 0.52315,
                        "current": 0.54721,
                        "date": "2025-05-05 20:35"
                    },
                    {
                        "token": "BOME",
                        "amount": 120000,
                        "entry": 0.00000183,
                        "current": 0.00000203,
                        "date": "2025-05-06 02:12"
                    }
                ]
                
                for pos in simulated_positions:
                    # Calculate profit/loss
                    pl_amount = (pos["current"] - pos["entry"]) * pos["amount"]
                    pl_percentage = ((pos["current"] / pos["entry"]) - 1) * 100
                    
                    # Determine emoji based on profit/loss
                    pl_emoji = "📈" if pl_percentage > 0 else "📉"
                    
                    # Add position detail
                    history_message += f"*{pos['token']}* {pl_emoji} {pl_percentage:.1f}%\n"
                    history_message += f"Amount: {pos['amount']} tokens\n"
                    history_message += f"Entry: ${pos['entry']:.8f}\n"
                    history_message += f"Current: ${pos['current']:.8f}\n"
                    history_message += f"P/L: {pl_amount:.6f} SOL\n"
                    history_message += f"Opened: {pos['date']}\n\n"
                
                history_message += "_These are simulated positions for demonstration purposes._\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 Compare", callback_data="compare_positions_placeholder"),
                    InlineKeyboardButton("🔙 Back", callback_data="trading_history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=history_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during trading positions display: {e}")
            db.session.rollback()
            
            error_text = "Sorry, there was an error retrieving your trading positions. Please try again later."
            await query.edit_message_text(text=error_text)


async def view_profit_chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a visual profit chart for the user."""
    query = update.callback_query
    await query.answer()
    
    # Generate a simple ASCII chart of profit over time
    profit_chart = (
        "📈 *Profit Chart (Last 7 Days)*\n\n"
        "```\n"
        "    SOL |                  *\n"
        "  0.40 |              *     \n"
        "  0.35 |          *         \n"
        "  0.30 |      *             \n"
        "  0.25 |  *                 \n"
        "  0.20 |                    \n"
        "  0.15 |                    \n"
        "  0.10 |                    \n"
        "  0.05 |                    \n"
        "  0.00 +--------------------\n"
        "       |Mo Tu We Th Fr Sa Su\n"
        "```\n\n"
        "Your profit growth has been accelerating over the last week. This chart shows simulated profit data."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Monthly View", callback_data="monthly_chart_placeholder"),
            InlineKeyboardButton("🔙 Back", callback_data="trading_history")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=profit_chart,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def view_allocation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show asset allocation breakdown."""
    query = update.callback_query
    await query.answer()
    
    # Create a simple visualization of asset allocation
    allocation_message = (
        "💱 *Asset Allocation*\n\n"
        "```\n"
        "Current portfolio distribution:\n"
        "\n"
        "BONK    [███████████       ] 55%\n"
        "WIF     [███████           ] 35%\n"
        "BOME    [██                ] 10%\n"
        "```\n\n"
        "Your current allocation is optimized for a balance of risk and reward. The trading bot automatically adjusts these allocations based on market conditions.\n\n"
        "_This is simulated allocation data._"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Rebalance", callback_data="rebalance_allocation"),
            InlineKeyboardButton("🔙 Back", callback_data="trading_history")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=allocation_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
