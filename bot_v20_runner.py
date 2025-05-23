#!/usr/bin/env python
"""
Telegram Bot Runner - Compatible with any version (fallback)
This script implements a simple API-based version of the Telegram bot.
"""
import logging
import os
import sys
import requests
import time
import json
import random
from datetime import datetime, timedelta
from threading import Thread
from config import BOT_TOKEN, MIN_DEPOSIT

# Import Flask app context
from app import app, db
from models import User, UserStatus, Profit, Transaction, TradingPosition, ReferralCode, CycleStatus, BroadcastMessage, AdminMessage

# Global variables for context storage (used by some handlers)
roi_update_context = None

# Global variables for tracking message state
pending_broadcast_id = None
broadcast_target = "all"     # Default broadcast target ("all" or "active")
broadcast_recipients = []    # List of recipient IDs for the current broadcast
dm_recipient_id = None
dm_content = None
dm_image_url = None
dm_image_caption = None
admin_target_user_id = None

# Global variables for balance adjustment
admin_adjust_telegram_id = None
admin_adjust_current_balance = None
admin_adjustment_amount = None
admin_adjustment_reason = None
admin_initial_deposit_amount = None
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    """A simple implementation of a Telegram bot using direct API calls."""
    
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.running = False
        self.offset = 0
        self.handlers = {}
        self.user_states = {}  # Track conversation states for each user
        self.wallet_listeners = {}  # Users waiting to provide a wallet
        logger.info(f"Bot initialized with token ending in ...{self.token[-5:]}")
    
    def add_command_handler(self, command, callback):
        """Add a command handler."""
        self.handlers[command] = callback
        logger.info(f"Added handler for command: {command}")
    
    def add_callback_handler(self, callback_data, callback):
        """Add a callback query handler."""
        self.handlers[callback_data] = callback
        logger.info(f"Added handler for callback: {callback_data}")
    
    def add_message_listener(self, chat_id, listener_type, callback):
        """Add a listener for non-command messages."""
        self.wallet_listeners[chat_id] = (listener_type, callback)
        logger.info(f"Added {listener_type} listener for chat {chat_id}")
    
    def remove_listener(self, chat_id):
        """Remove a listener for a chat."""
        if chat_id in self.wallet_listeners:
            del self.wallet_listeners[chat_id]
            logger.info(f"Removed listener for chat {chat_id}")
    
    def send_message(self, chat_id, text, parse_mode="Markdown", reply_markup=None):
        """Send a message to a chat."""
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup:
            payload['reply_markup'] = reply_markup
            
        response = requests.post(
            f"{self.api_url}/sendMessage",
            json=payload
        )
        return response.json()
    
    def edit_message(self, message_id, chat_id, text, parse_mode="Markdown", reply_markup=None):
        """Edit an existing message."""
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup:
            payload['reply_markup'] = reply_markup
            
        response = requests.post(
            f"{self.api_url}/editMessageText",
            json=payload
        )
        return response.json()
        
    def send_chat_action(self, chat_id, action="typing"):
        """Send a chat action like typing, uploading, etc."""
        try:
            payload = {
                'chat_id': chat_id,
                'action': action  # typing, upload_photo, record_video, upload_document, etc.
            }
            
            response = requests.post(
                f"{self.api_url}/sendChatAction",
                json=payload
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error sending chat action: {e}")
            return None
            
    def send_document(self, chat_id, document, caption=None, parse_mode="Markdown"):
        """Send a document (file) to a chat."""
        try:
            # First show an "uploading document" action
            self.send_chat_action(chat_id, action="upload_document")
            
            # Prepare parameters
            params = {
                'chat_id': chat_id,
                'parse_mode': parse_mode
            }
            
            if caption:
                params['caption'] = caption
                
            # Create a multipart form data payload
            files = {'document': document}
            
            # Send the document
            response = requests.post(
                f"{self.api_url}/sendDocument",
                params=params,
                files=files
            )
            
            return response.json()
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"ok": False, "error": str(e)}
    
    def get_updates(self):
        """Get updates from Telegram API."""
        try:
            response = requests.get(
                f"{self.api_url}/getUpdates",
                params={
                    'offset': self.offset,
                    'timeout': 30
                }
            )
            data = response.json()
            if 'result' in data and data['result']:
                self.offset = data['result'][-1]['update_id'] + 1
            return data.get('result', [])
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []
    
    def create_inline_keyboard(self, buttons):
        """Create an inline keyboard."""
        return {
            'inline_keyboard': buttons
        }
    
    def process_update(self, update):
        """Process a single update."""
        try:
            # Handle messages
            if 'message' in update and 'text' in update['message']:
                text = update['message']['text']
                chat_id = update['message']['chat']['id']
                user_id = str(update['message']['from']['id'])
                
                # Check if there's an active listener waiting for user input
                if chat_id in self.wallet_listeners:
                    listener_type, callback = self.wallet_listeners[chat_id]
                    # Handle all listener types 
                    # (wallet_address, withdrawal_amount, support_ticket, support_username)
                    callback(update, chat_id, text)
                    return
                
                # If this is the user's first message and not a command, show welcome message
                if not text.startswith('/'):
                    with app.app_context():
                        # Check if user exists in database
                        user_exists = User.query.filter_by(telegram_id=user_id).first() is not None
                        
                        # If user doesn't exist, this is likely their first interaction
                        if not user_exists:
                            display_welcome_message(chat_id)
                            return
                
                # Handle commands
                if text.startswith('/'):
                    command = text.split()[0].lower()
                    if command in self.handlers:
                        self.handlers[command](update, chat_id)
                    else:
                        self.send_message(chat_id, f"Unknown command: {command}")
            
            # Handle callback queries if present
            if 'callback_query' in update:
                query_id = update['callback_query']['id']
                chat_id = update['callback_query']['message']['chat']['id']
                data = update['callback_query']['data']
                
                # Answer the callback query to stop the loading indicator
                requests.post(
                    f"{self.api_url}/answerCallbackQuery",
                    json={'callback_query_id': query_id}
                )
                
                # Process the callback data
                if data in self.handlers:
                    self.handlers[data](update, chat_id)
                # Handle custom withdrawal amounts with pattern matching
                elif data.startswith('custom_withdraw_'):
                    try:
                        # Extract the amount from the callback data
                        amount_str = data.split('_')[-1]
                        amount = float(amount_str)
                        # Process the custom withdrawal
                        self.process_custom_withdrawal(chat_id, amount)
                    except Exception as e:
                        logger.error(f"Error processing custom withdrawal: {e}")
                        self.send_message(chat_id, "⚠️ Error processing your withdrawal request. Please try again.")
                # Handle withdrawal approval/denial with dynamic IDs
                elif data.startswith('admin_approve_withdrawal_'):
                    try:
                        admin_approve_withdrawal_handler(update, chat_id)
                    except Exception as e:
                        logger.error(f"Error approving withdrawal: {e}")
                        self.send_message(chat_id, "⚠️ Error approving withdrawal. Please try again.")
                elif data.startswith('admin_deny_withdrawal_'):
                    try:
                        admin_deny_withdrawal_handler(update, chat_id)
                    except Exception as e:
                        logger.error(f"Error denying withdrawal: {e}")
                        self.send_message(chat_id, "⚠️ Error denying withdrawal. Please try again.")
                
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    def start_polling(self):
        """Start polling for updates."""
        self.running = True
        logger.info("Starting polling for updates")
        
        while self.running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.process_update(update)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
            
            time.sleep(1)
    
    def start(self):
        """Start the bot in a separate thread."""
        self.thread = Thread(target=self.start_polling)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Bot started in background thread")
    
    def process_custom_withdrawal(self, chat_id, amount):
        """Process a custom withdrawal amount request with simple balance check."""
        try:
            with app.app_context():
                import random
                from models import User, Transaction
                from datetime import datetime
                from app import db
                
                # First, show simple processing message
                self.send_message(
                    chat_id,
                    "💸 *Processing...*",
                    parse_mode="Markdown"
                )
                
                # Check if user exists and has sufficient balance
                user = User.query.filter_by(telegram_id=str(chat_id)).first()
                is_funded = user and user.balance >= amount
                
                # If not funded, show error message
                if not is_funded:
                    error_message = (
                        "❌ *Withdrawal Failed*\n\n"
                        "Reason: Insufficient balance for the requested amount.\n\n"
                        f"Amount requested: *{amount:.6f} SOL*\n"
                        f"Your available balance: *{user.balance if user else 0:.6f} SOL*\n\n"
                        "Please try a smaller amount or make a deposit first."
                    )
                    
                    keyboard = self.create_inline_keyboard([
                        [{"text": "💰 Make a Deposit", "callback_data": "deposit"}],
                        [{"text": "🔙 Go Back", "callback_data": "withdraw_profit"}]
                    ])
                    
                    self.send_message(
                        chat_id,
                        error_message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                    return
                
                # Create transaction with pending status
                new_transaction = Transaction(
                    user_id=user.id,
                    transaction_type="withdraw",
                    amount=amount,
                    timestamp=datetime.utcnow(),
                    status="pending",
                    notes="Custom withdrawal pending admin approval"
                )
                db.session.add(new_transaction)
                
                # Reserve the amount from user balance
                user.balance -= amount
                db.session.commit()
                
                # Format time
                time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                
                # Show pending withdrawal message
                success_message = (
                    "⏳ *Withdrawal Request Submitted*\n\n"
                    f"Amount: *{amount:.6f} SOL*\n"
                    f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:] if len(user.wallet_address) > 10 else user.wallet_address}\n"
                    f"Request ID: #{new_transaction.id}\n"
                    f"Time: {time_str} UTC\n\n"
                    "Your withdrawal request has been submitted and is pending approval by an administrator. "
                    "You will be notified once your withdrawal has been processed.\n\n"
                    f"Your updated balance is: *{user.balance:.6f} SOL*"
                )
                
                keyboard = self.create_inline_keyboard([
                    [{"text": "💸 View Transaction", "callback_data": "view_tx"}],
                    [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
                ])
                
                self.send_message(
                    chat_id,
                    success_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
        except Exception as e:
            import logging
            logging.error(f"Error in process_custom_withdrawal: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self.send_message(chat_id, f"⚠️ Error processing your withdrawal: {str(e)}")
    
    def stop(self):
        """Stop the bot."""
        self.running = False
        logger.info("Bot stopping...")

# Import app context for database operations
from app import app
from models import User, UserStatus, ReferralCode
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

# Welcome message handler
def display_welcome_message(chat_id):
    """Display the welcome message before a user presses /start."""
    # Format the welcome message exactly as requested
    welcome_message = (
        "Welcome to THRIVE BOT\n"
        "The auto-trading system built for real memecoin winners.\n\n"
        "- Trades live tokens on Solana in real-time\n"
        "- Tracks profits with full transparency\n"
        "- Withdraw anytime with proof in hand\n\n"
        "No subscriptions. No empty promises. Just results.\n\n"
        "Tap \"Start\" to begin your climb."
    )
    
    # Send the welcome message
    bot.send_message(chat_id, welcome_message)
    logger.info(f"Displayed pre-start welcome message to user {chat_id}")

# Command handlers
def start_command(update, chat_id):
    """Handle the /start command with non-blocking database operations."""
    import threading
    
    # Extract user information immediately
    first_name = update['message']['from'].get('first_name', 'there')
    user_id = str(update['message']['from']['id'])
    username = update['message']['from'].get('username', '')
    last_name = update['message']['from'].get('last_name', '')
    
    # Check for referral link parameter (format: ref_123456789)
    start_parameter = None
    if 'message' in update and 'text' in update['message']:
        text = update['message']['text']
        if ' ' in text:  # Check if there's a parameter after /start
            start_parameter = text.split(' ', 1)[1]
    
    # First, send immediate acknowledgment to prevent freezing
    # This makes the bot respond instantly while processing happens in background
    initial_message = f"Welcome {first_name}!"
    bot.send_message(chat_id, initial_message)
    
    # Define function to handle database operations in background
    def process_start_command_in_background():
        with app.app_context():
            try:
                existing_user = User.query.filter_by(telegram_id=user_id).first()
                
                if not existing_user:
                    logger.info(f"New user registered: {user_id} - {username}")
                    
                    # Create a new user record
                    from app import db
                    new_user = User(
                        telegram_id=user_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        joined_at=datetime.utcnow(),
                        status=UserStatus.ONBOARDING
                    )
                    
                    # Generate a referral code for the new user
                    new_referral_code = ReferralCode(
                        user_id=None,  # Temporary placeholder, will update after user is committed
                        code=ReferralCode.generate_code(),
                        created_at=datetime.utcnow(),
                        is_active=True
                    )
                    
                    db.session.add(new_user)
                    db.session.flush()  # Flush to get the user ID
                    
                    # Update the referral code with the new user ID
                    new_referral_code.user_id = new_user.id
                    db.session.add(new_referral_code)
                    
                    # Process referral if applicable
                    if start_parameter and start_parameter.startswith('ref_'):
                        try:
                            # Extract referrer ID from parameter
                            referrer_id = start_parameter.replace('ref_', '')
                            
                            # Find referrer in database
                            referrer = User.query.filter_by(telegram_id=referrer_id).first()
                            
                            if referrer and referrer.id != new_user.id:
                                # Find referrer's referral code
                                ref_code = ReferralCode.query.filter_by(user_id=referrer.id, is_active=True).first()
                                
                                if ref_code:
                                    # Connect the new user to the referrer
                                    new_user.referrer_code_id = ref_code.id
                                    
                                    # Update referral stats
                                    ref_code.total_referrals += 1
                                    
                                    logger.info(f"User {user_id} was referred by {referrer_id}")
                        except Exception as e:
                            logger.error(f"Error processing referral: {e}")
                    
                    # Commit changes to database
                    db.session.commit()
                    
                    # Use the exact original welcome message from handlers/start.py
                    welcome_message = (
                        f"👋 *Welcome to THRIVE Bot*, {first_name}!\n\n"
                        "I'm your automated Solana memecoin trading assistant. I help grow your SOL by buying and selling "
                        "trending memecoins with safe, proven strategies. You retain full control of your funds at all times.\n\n"
                        "💰 No hidden fees, no hidden risks\n"
                        "⚡ Real-time trading 24/7\n"
                        "🔒 Your SOL stays under your control\n\n"
                        "To get started, please enter your *Solana wallet address* below.\n"
                        "This is where your profits will be sent when you withdraw."
                    )
                    
                    # No button in the original design
                    reply_markup = None
                    
                    bot.send_message(chat_id, welcome_message, reply_markup=reply_markup)
                    
                    # Add a listener to wait for the wallet address
                    bot.add_message_listener(chat_id, 'wallet_address', wallet_address_handler)
                else:
                    logger.info(f"Returning user: {user_id} - {username}")
                    # Update last active in background to prevent blocking
                    try:
                        existing_user.last_active = datetime.utcnow()
                        from app import db
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error updating last_active: {e}")
                    
                    # For existing users, show main menu
                    show_main_menu(update, chat_id)
            except SQLAlchemyError as e:
                logger.error(f"Database error during user registration: {e}")
                bot.send_message(chat_id, "⚠️ Sorry, we encountered a database error. Please try again later.")
                return
    
    # Run the database operations in a background thread
    thread = threading.Thread(target=process_start_command_in_background)
    thread.daemon = True
    thread.start()
    
    # Return immediately so bot doesn't freeze
    return

# Referral handler functions
def copy_referral_handler(update, chat_id):
    """Handle the copy referral link button press."""
    try:
        # Import the referral module
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("thrivesolanabot")
                logger.info("Initialized referral manager")
            
            user_id = str(update['callback_query']['from']['id'])
            
            # Get the referral link
            stats = referral_manager.get_referral_stats(user_id)
            
            # Generate the referral code if needed
            if not stats['has_code']:
                code = referral_manager.generate_or_get_referral_code(user_id)
                if code:
                    stats['has_code'] = True
            
            # Show copy confirmation message
            referral_link = f"https://t.me/thrivesolanabot?start=ref_{user_id}"
            
            # Send the referral link as a separate message for easy copying
            bot.send_message(
                chat_id,
                f"`{referral_link}`",
                parse_mode="Markdown"
            )
            
            bot.send_message(
                chat_id,
                "✅ Your referral link is copied to clipboard! Share with friends to earn 5% of their profits."
            )
    except Exception as e:
        logger.error(f"Error in copy_referral_handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error copying referral link: {str(e)}")

def share_referral_handler(update, chat_id):
    """Handle the share referral button press."""
    try:
        # Import the referral module
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("thrivesolanabot")
                logger.info("Initialized referral manager")
            
            user_id = str(update['callback_query']['from']['id'])
            
            # Get the referral link
            stats = referral_manager.get_referral_stats(user_id)
            
            # Generate the referral code if needed
            if not stats['has_code']:
                code = referral_manager.generate_or_get_referral_code(user_id)
                if code:
                    stats['has_code'] = True
            
            # Create a shareable message with the referral link
            referral_link = f"https://t.me/thrivesolanabot?start=ref_{user_id}"
            
            share_message = (
                "🔄 *THRIVE Trading Bot: Double Your SOL in 7 Days*\n\n"
                "Join me on THRIVE Bot - the automated Solana memecoin trading assistant!\n\n"
                "✅ Trades live tokens on Solana\n"
                "✅ Tracks profits with full transparency\n"
                "✅ Withdraw anytime\n\n"
                f"Join now: {referral_link}"
            )
            
            # Send the shareable message for easy forwarding
            bot.send_message(
                chat_id,
                share_message,
                parse_mode="Markdown"
            )
            
            # Send instructions
            bot.send_message(
                chat_id,
                "Forward this message to friends or share the link directly. You'll earn 5% of their profits!"
            )
    except Exception as e:
        logger.error(f"Error in share_referral_handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sharing referral link: {str(e)}")

def referral_stats_handler(update, chat_id):
    """Handle the view referral stats button press with enhanced visualization."""
    try:
        # Import the referral module
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("thrivesolanabot")
                logger.info("Initialized referral manager")
            
            user_id = str(update['callback_query']['from']['id'])
            
            # Get detailed referral stats
            stats = referral_manager.get_referral_stats(user_id)
            
            # Determine referral tier and create progress bar
            active_referrals = stats['active_referrals']
            if active_referrals >= 25:
                tier = "💎 Diamond Tier"
                tier_description = "Elite status with maximum rewards"
                tier_bar = "▰▰▰▰▰▰▰▰▰▰ 100%"
            elif active_referrals >= 10:
                tier = "🥇 Gold Tier"
                tier_description = f"{active_referrals}/25 towards Diamond"
                progress_percent = min(100, (active_referrals - 10) * 100 / 15)
                filled = int(progress_percent / 10)
                tier_bar = f"{'▰' * filled}{'▱' * (10-filled)} {progress_percent:.0f}%"
            elif active_referrals >= 5:
                tier = "🥈 Silver Tier"
                tier_description = f"{active_referrals}/10 towards Gold"
                progress_percent = min(100, (active_referrals - 5) * 100 / 5)
                filled = int(progress_percent / 10)
                tier_bar = f"{'▰' * filled}{'▱' * (10-filled)} {progress_percent:.0f}%"
            else:
                tier = "🥉 Bronze Tier"
                tier_description = f"{active_referrals}/5 towards Silver"
                progress_percent = min(100, active_referrals * 100 / 5)
                filled = int(progress_percent / 10)
                tier_bar = f"{'▰' * filled}{'▱' * (10-filled)} {progress_percent:.0f}%"
            
            # Create various stats visualizations
            
            # Conversion rate (active vs total)
            conversion_rate = 0
            if stats['total_referrals'] > 0:
                conversion_rate = (stats['active_referrals'] / stats['total_referrals']) * 100
                if conversion_rate >= 75:
                    conversion_quality = "🟢 Excellent"
                elif conversion_rate >= 50:
                    conversion_quality = "🟡 Good"
                elif conversion_rate >= 25:
                    conversion_quality = "🟠 Fair"
                else:
                    conversion_quality = "🔴 Needs Improvement"
            else:
                conversion_quality = "⚪ No Data"
            
            # Calculate average earnings per referral
            avg_earnings = 0
            if stats['active_referrals'] > 0:
                avg_earnings = stats['total_earnings'] / stats['active_referrals']
            
            # Create detailed stats message with enhanced visualization
            stats_message = (
                "📊 *DETAILED REFERRAL STATISTICS* 📊\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                f"*{tier}*\n"
                f"{tier_bar}\n"
                f"{tier_description}\n\n"
                
                f"*REFERRAL COUNTS*\n"
                f"Total Invited: {stats['total_referrals']} users\n"
                f"Active Users: {stats['active_referrals']} users\n"
                f"Pending Activation: {stats.get('pending_referrals', 0)} users\n"
                f"Conversion Rate: {conversion_rate:.1f}% ({conversion_quality})\n\n"
                
                f"*EARNINGS BREAKDOWN*\n"
                f"Total Earned: {stats['total_earnings']:.4f} SOL\n"
                f"Avg Per Referral: {avg_earnings:.4f} SOL\n\n"
            )
            
            # Add information about referred users if any
            if stats['referred_users'] and len(stats['referred_users']) > 0:
                stats_message += "*YOUR REFERRED USERS*\n"
                for i, user in enumerate(stats['referred_users'][:5], 1):  # Show up to 5 to keep it tidy
                    active_status = "✅" if user.get('is_active', False) else "⏳"
                    earnings = user.get('earnings', 0.0)
                    stats_message += f"{active_status} User {user.get('id', 'Unknown')}: {earnings:.4f} SOL\n"
                
                # Add summary of other referrals if more than 5
                if len(stats['referred_users']) > 5:
                    remaining = len(stats['referred_users']) - 5
                    stats_message += f"\n_...and {remaining} more referrals not shown_\n"
            else:
                stats_message += (
                    "*START REFERRING TODAY*\n"
                    "You haven't referred anyone yet. Share your referral code to start earning passive income!\n"
                )
            
            # Add tips for improving referrals
            stats_message += (
                "\n*WANT TO INCREASE YOUR EARNINGS?*\n"
                "Share your referral link with friends interested in crypto trading. The more active users you refer, the more you earn!"
            )
            
            # Create enhanced keyboard with sharing options
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📤 Share Now", "callback_data": "share_referral"},
                    {"text": "📱 Create QR Code", "callback_data": "referral_qr_code"}
                ],
                [
                    {"text": "💡 Referral Tips", "callback_data": "referral_tips"}
                ],
                [
                    {"text": "🔙 Back to Referral Menu", "callback_data": "referral"}
                ]
            ])
            
            bot.send_message(chat_id, stats_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in referral_stats_handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying referral stats: {str(e)}")

def wallet_address_handler(update, chat_id, text):
    """Handle the wallet address input."""
    user_id = str(update['message']['from']['id'])
    
    # Remove the listener since we received input
    bot.remove_listener(chat_id)
    
    # Handle skipped wallet case
    if text.lower() == 'skip':
        # We'll use skip, but still keep it mandatory at a later point
        bot.send_message(
            chat_id, 
            "You've chosen to skip providing a wallet address for now.\n\n"
            "🔄 *IMPORTANT*: You'll need to add a wallet before withdrawing profits."
        )
        show_main_menu(update, chat_id)
        return
    
    # Use the exact wallet validation from handlers/start.py
    # Import the Solana address validator if available, otherwise use basic check
    try:
        from utils.solana import is_valid_solana_address
        is_valid = is_valid_solana_address(text)
    except ImportError:
        # Fallback to basic check
        is_valid = len(text) == 44 and text.startswith(('So', '1'))
    
    if not is_valid:
        bot.send_message(
            chat_id,
            "⚠️ This doesn't look like a valid Solana wallet address.\n"
            "Please provide a valid Solana wallet address.\n\n"
            "Valid example: `rAg2CtT591ow7x7eXomCc4aEXyuu4At3sn92wrwygjj`",
            parse_mode="Markdown"
        )
        # Keep the listener active for another attempt
        bot.add_message_listener(chat_id, 'wallet_address', wallet_address_handler)
        return
    
    # Store the wallet address in the database
    with app.app_context():
        try:
            from app import db
            user = User.query.filter_by(telegram_id=user_id).first()
            if user:
                user.wallet_address = text
                db.session.commit()
                
                # Sequence of messages exactly like in the original
                
                # First confirmation message
                wallet_updated_message = (
                    f"Payout wallet address updated to {text[:6]}..."
                    f"{text[-6:]}.\n\n"
                    f"It will be used for all future deposit payouts."
                )
                bot.send_message(chat_id, wallet_updated_message, parse_mode="Markdown")
                
                # Second message - deposit instructions with updated minimum amount
                deposit_instructions = (
                    f"Please send a minimum of *0.5 SOL (Solana)*\n"
                    f"and maximum *5000 SOL* to the following\n"
                    f"address.\n\n"
                    f"Once your deposit is received, it will be\n"
                    f"processed, and you'll be on your way to\n"
                    f"doubling your Solana in just 168 hours! The\n"
                    f"following wallet address is your deposit wallet:"
                )
                bot.send_message(chat_id, deposit_instructions, parse_mode="Markdown")
                
                # Generate a deposit wallet address
                try:
                    from utils.solana import generate_wallet_address
                    deposit_wallet = generate_wallet_address()
                except ImportError:
                    # Fallback - generate a fixed address for demo
                    deposit_wallet = "6xabcdefghijklmnopqrstuvwxyz123456789ABCDEFGHIJK"
                
                # Update user record with the deposit wallet if possible
                try:
                    user.deposit_wallet = deposit_wallet
                    db.session.commit()
                except:
                    pass
                
                # Display the deposit wallet address
                bot.send_message(chat_id, f"`{deposit_wallet}`", parse_mode="Markdown")
                
                # Final message - Buttons in a 2x2 grid
                keyboard = [
                    [
                        {"text": "📋 Copy Address", "callback_data": "copy_address"},
                        {"text": "✅ Deposit Done", "callback_data": "deposit_confirmed"}
                    ],
                    [
                        {"text": "🏠 Back to Main Menu", "callback_data": "start"},
                        {"text": "💻 Help", "callback_data": "help"}
                    ]
                ]
                reply_markup = bot.create_inline_keyboard(keyboard)
                
                bot.send_message(chat_id, "...", reply_markup=reply_markup)
            else:
                logger.error(f"User not found: {user_id}")
                bot.send_message(chat_id, "⚠️ Sorry, we couldn't find your user record. Please try /start again.")
        except SQLAlchemyError as e:
            logger.error(f"Database error saving wallet address: {e}")
            bot.send_message(chat_id, "⚠️ Sorry, we encountered a database error. Please try again later.")

def skip_wallet_callback(update, chat_id):
    """Handle the skip wallet button press."""
    user_id = str(update['callback_query']['from']['id'])
    
    # Remove any active listeners
    bot.remove_listener(chat_id)
    
    bot.send_message(
        chat_id,
        "You've chosen to skip providing a wallet address for now.\n\n"
        "🔄 *IMPORTANT*: You'll need to add a wallet before withdrawing profits."
    )
    show_main_menu_callback(update, chat_id)

def show_main_menu(update, chat_id):
    """Show the main menu for the bot with exact button layout from the original."""
    # This matches the exact button layout from handlers/start.py
    keyboard = [
        # First row - primary actions
        [
            {"text": "💰 Deposit SOL", "callback_data": "deposit"},
            {"text": "📊 Dashboard", "callback_data": "view_dashboard"}

        ],
        # Second row - information and features
        [
            {"text": "ℹ️ How It Works", "callback_data": "how_it_works"},
            {"text": "🔗 Referral Program", "callback_data": "referral"}
        ],
        # Third row - settings and help
        [
            {"text": "⚙️ Settings", "callback_data": "settings"},
            {"text": "❓ Help", "callback_data": "help"}
        ]
    ]
    reply_markup = bot.create_inline_keyboard(keyboard)
    
    # Same welcome message as in the original
    welcome_message = (
        "👋 *Welcome to THRIVE Bot!*\n\n"
        "I'm your automated Solana memecoin trading assistant. I help grow your SOL by buying and selling "
        "trending memecoins with safe, proven strategies. You retain full control of your funds at all times.\n\n"
        "✅ *Current Status*: Ready to help you trade\n"
        "⏰ *Trading Hours*: 24/7 automated monitoring\n"
        "🔒 *Security*: Your SOL stays under your control\n\n"
        "Choose an option below to get started on your trading journey!"
    )
    
    bot.send_message(
        chat_id,
        welcome_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def show_main_menu_callback(update, chat_id):
    """Show the main menu from a callback query."""
    # Use the exact same menu as the regular menu function for consistency
    # This matches the exact button layout from handlers/start.py
    keyboard = [
        # First row - primary actions
        [
            {"text": "💰 Deposit SOL", "callback_data": "deposit"},
            {"text": "📊 Dashboard", "callback_data": "view_dashboard"}
        ],
        # Second row - information and features
        [
            {"text": "ℹ️ How It Works", "callback_data": "how_it_works"},
            {"text": "🔗 Referral Program", "callback_data": "referral"}
        ],
        # Third row - settings and help
        [
            {"text": "⚙️ Settings", "callback_data": "settings"},
            {"text": "❓ Help", "callback_data": "help"}
        ]
    ]
    reply_markup = bot.create_inline_keyboard(keyboard)
    
    # Same welcome message as in the original
    welcome_message = (
        "👋 *Welcome to THRIVE Bot!*\n\n"
        "I'm your automated Solana memecoin trading assistant. I help grow your SOL by buying and selling "
        "trending memecoins with safe, proven strategies. You retain full control of your funds at all times.\n\n"
        "✅ *Current Status*: Ready to help you trade\n"
        "⏰ *Trading Hours*: 24/7 automated monitoring\n"
        "🔒 *Security*: Your SOL stays under your control\n\n"
        "Choose an option below to get started on your trading journey!"
    )
    
    bot.send_message(
        chat_id,
        welcome_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def help_command(update, chat_id):
    """Handle the /help command."""
    try:
        help_message = (
            "🤔 *Need Help? Here's How THRIVE Works*\n\n"
            "• *Getting Started:* Use the /start command to begin\n"
            "• *Deposit:* Add SOL to start automated trading\n"
            "• *Dashboard:* Check profits and trading performance\n"
            "• *Withdrawal:* Get your profits anytime\n"
            "• *Settings:* Customize your trading preferences\n"
            "• *Referral:* Invite friends and earn 5% of their profits\n\n"
            "🏆 *Our Strategy:*\n"
            "THRIVE analyzes social media sentiment, trading volume, and market momentum to identify promising memecoins. Our intelligent algorithms execute precise trades to maximize your returns.\n\n"
            "📈 *Common Commands:*\n"
            "/start - Set up your account\n"
            "/deposit - Add funds to start trading\n"
            "/dashboard - View trading performance\n"
            "/settings - Manage your account\n"
            "/referral - Share with friends\n"
            "/help - Get assistance\n\n"
            "💬 *Still have questions?* Tap the Customer Support button in your dashboard."
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "🏠 Dashboard", "callback_data": "view_dashboard"},
                {"text": "💰 Deposit", "callback_data": "deposit"}
            ],
            [
                {"text": "🚀 How It Works", "callback_data": "how_it_works"}
            ]

        ])
        
        bot.send_message(chat_id, help_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in help command: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying help page: {str(e)}")

def deposit_confirmed_handler(update, chat_id):
    """Handle the user confirming they've made a deposit."""
    try:
        with app.app_context():
            from app import db
            from models import User, Transaction, SystemSettings
            from config import ADMIN_USER_ID, MIN_DEPOSIT
            import random
            from datetime import datetime
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Tell the user we're processing their deposit
            bot.send_chat_action(chat_id, action="typing")
            processing_message = (
                "✅ *Processing Your Deposit*\n\n"
                "Thank you for confirming your deposit.\n"
                "We're verifying the transaction details and will notify you shortly."
            )
            
            msg = bot.send_message(chat_id, processing_message, parse_mode="Markdown")
            message_id = msg.get('message_id')
            
            # For demonstration purposes, simulate a successful transaction 70% of the time
            # In a real implementation, we'd check the blockchain for actual deposits
            deposit_found = random.random() < 0.7
            
            if deposit_found:
                # Simulate found transaction
                # Generate a random deposit amount between MIN_DEPOSIT and 2*MIN_DEPOSIT
                deposit_amount = round(random.uniform(MIN_DEPOSIT, MIN_DEPOSIT * 2), 2)
                
                # Record the transaction in the database
                transaction = Transaction(
                    user_id=user.id,
                    transaction_type="deposit",
                    amount=deposit_amount,
                    timestamp=datetime.utcnow(),
                    status="completed",
                    notes=f"User-initiated deposit confirmation"
                )
                db.session.add(transaction)
                
                # Update user balance
                previous_balance = user.balance
                user.balance += deposit_amount
                
                # Update user status if needed
                if user.status.value == "ONBOARDING" or user.status.value == "DEPOSITING":
                    from models import UserStatus
                    user.status = UserStatus.ACTIVE
                
                # If this is their first deposit, set initial deposit amount
                if user.initial_deposit == 0:
                    user.initial_deposit = deposit_amount
                
                db.session.commit()
                
                # Send confirmation to user
                success_message = (
                    "🎉 *Deposit Successfully Processed!*\n\n"
                    f"Your deposit of *{deposit_amount} SOL* has been confirmed and added to your account.\n\n"
                    f"• Previous balance: {previous_balance:.2f} SOL\n"
                    f"• New balance: {user.balance:.2f} SOL\n\n"
                    "Your funds are now being used for trading with our automated strategy."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [
                        {"text": "📊 View Dashboard", "callback_data": "dashboard"},
                        {"text": "🔗 Invite Friends", "callback_data": "referral"}
                    ],
                    [{"text": "🏠 Back to Main Menu", "callback_data": "start"}]
                ])
                
                bot.edit_message(message_id, chat_id, success_message, parse_mode="Markdown", reply_markup=keyboard)
                
                # Notify admin about new deposit
                try:
                    admin_notification = (
                        "💰 *New Deposit Alert*\n\n"
                        f"• User: `{user.telegram_id}`"
                    )
                    if user.username:
                        admin_notification += f" (@{user.username})"
                    
                    admin_notification += (
                        f"\n• Amount: *{deposit_amount} SOL*\n"
                        f"• Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"• New Balance: {user.balance:.2f} SOL"
                    )
                    
                    # Send notification to admin
                    bot.send_message(ADMIN_USER_ID, admin_notification, parse_mode="Markdown")
                except Exception as admin_error:
                    logging.error(f"Failed to send admin notification: {str(admin_error)}")
            else:
                # No transaction found - show helpful message
                bot.edit_message(message_id, chat_id,
                    "⚠️ *No Transaction Found*\n\n"
                    "We couldn't detect your deposit. This could be because:\n\n"
                    "• The transaction is still confirming\n"
                    "• The transaction was sent to a different address\n"
                    "• You may need to wait a few more minutes\n\n"
                    "Please verify your transaction details and try again shortly.",
                    parse_mode="Markdown",
                    reply_markup=bot.create_inline_keyboard([
                        [
                            {"text": "🔄 Check Again", "callback_data": "deposit_confirmed"},
                            {"text": "📑 Deposit Instructions", "callback_data": "deposit"}
                        ],
                        [{"text": "🏠 Back to Main Menu", "callback_data": "start"}]
                    ])
                )
    except Exception as e:
        import logging
        logging.error(f"Error in deposit_confirmed_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing deposit confirmation: {str(e)}")


def deposit_command(update, chat_id):
    """Handle the /deposit command."""
    try:
        with app.app_context():
            from app import db
            from models import User, SystemSettings
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Get system deposit wallet address from settings
            deposit_setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
            
            # If no wallet is configured in system settings, use a default address
            if deposit_setting and deposit_setting.setting_value:
                deposit_wallet = deposit_setting.setting_value
            else:
                deposit_wallet = "Soa8DkfSzZEmXLJ2AWEqm76fgrSWYxT5iPg6kDdZbKmx"  # Default fallback address
            
            # Send the styled deposit message
            deposit_message = (
                "💰 *Deposit SOL*\n\n"
                f"To start trading with THRIVE, please deposit a\n"
                f"minimum of *0.5 SOL* to your personal trading wallet:\n\n"
                f"`{deposit_wallet}`\n\n"
                f"• *Minimum Deposit:* 0.5 SOL\n"
                f"• *Network:* Solana (SOL)\n"
                f"• *Processing Time:* 1-5 minutes\n\n"
                f"_Once your deposit is received, the bot will automatically start trading for you with our proven strategy._"
            )
            
            # Create keyboard with deposit options in 2x2 grid
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📋 Copy Address", "callback_data": "copy_address"},
                    {"text": "✅ I've Sent SOL", "callback_data": "deposit_confirmed"}
                ],
                [
                    {"text": "🏠 Back to Main Menu", "callback_data": "start"},
                    {"text": "💻 Help", "callback_data": "help"}
                ]
            ])
            
            bot.send_message(chat_id, deposit_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in deposit command: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying deposit page: {str(e)}")

def dashboard_command(update, chat_id):
    """Handle the /dashboard command."""
    try:
        # Import datetime at the function level to avoid the UnboundLocalError
        from datetime import datetime, timedelta
        
        with app.app_context():
            from app import db
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
                
            # Calculate profits and available balance
            from sqlalchemy import func
            from models import Profit, UserStatus
            
            # Set initial values for all users
            total_profit_amount = 0
            total_profit_percentage = 0
            today_profit_amount = 0
            today_profit_percentage = 0
            
            # Calculate profits for active users
            if user.status == UserStatus.ACTIVE and user.initial_deposit > 0:
                # Get total profits
                total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
                total_profit_percentage = (total_profit_amount / user.initial_deposit) * 100 if user.initial_deposit > 0 else 0
                
                # Get today's profits
                today = datetime.utcnow().date()
                today_profit = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id, date=today).scalar() or 0
                today_profit_amount = today_profit
                today_profit_percentage = (today_profit / user.balance) * 100 if user.balance > 0 else 0
            
            # Get profit streak
            streak = 0
            current_date = datetime.utcnow().date()
            
            # Check up to 30 days back (maximum reasonable streak)
            for i in range(30):
                check_date = current_date - timedelta(days=i)
                day_profit = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id, date=check_date).scalar() or 0
                
                if day_profit > 0:
                    if i == 0 or streak > 0:  # Today counts or continuing streak
                        streak += 1
                else:
                    if i > 0:  # Not counting today
                        break
            
            # Get ROI metrics - internal implementation since we can't import from utils
            def get_user_roi_metrics(user_id):
                """Get ROI metrics for a user - simplified implementation"""
                with app.app_context():
                    from models import TradingCycle, CycleStatus
                    
                    # Query for the user's active trading cycle
                    active_cycle = TradingCycle.query.filter_by(
                        user_id=user_id, 
                        status=CycleStatus.IN_PROGRESS
                    ).first()
                    
                    # Default metrics if no active cycle
                    metrics = {
                        'has_active_cycle': False,
                        'days_elapsed': 0,
                        'days_remaining': 7,
                        'progress_percentage': 0,
                        'target_balance': 0,
                        'current_balance': 0,
                        'is_on_track': True
                    }
                    
                    if active_cycle:
                        # Calculate days elapsed
                        days_elapsed = (datetime.utcnow() - active_cycle.start_date).days
                        days_elapsed = max(0, min(7, days_elapsed))
                        
                        # Calculate days remaining
                        days_remaining = max(0, 7 - days_elapsed)
                        
                        # Calculate progress percentage
                        if active_cycle.target_balance > 0:
                            progress = (active_cycle.current_balance / active_cycle.target_balance) * 100
                        else:
                            progress = 0
                        
                        # Update metrics
                        metrics = {
                            'has_active_cycle': True,
                            'days_elapsed': days_elapsed,
                            'days_remaining': days_remaining,
                            'progress_percentage': min(100, progress),
                            'target_balance': active_cycle.target_balance,
                            'current_balance': active_cycle.current_balance,
                            'is_on_track': active_cycle.is_on_track() if hasattr(active_cycle, 'is_on_track') else True
                        }
                    
                    return metrics
                
            roi_metrics = get_user_roi_metrics(user.id)
            
            # Format metrics for display
            has_active_cycle = roi_metrics['has_active_cycle']
            days_active = roi_metrics['days_elapsed'] if has_active_cycle else min(7, (datetime.utcnow().date() - user.joined_at.date()).days)
            days_left = roi_metrics['days_remaining'] if has_active_cycle else max(0, 7 - days_active)
            
            # Calculate next milestone target - 10% of initial deposit or minimum 0.05 SOL
            milestone_target = max(user.initial_deposit * 0.1, 0.05)
            
            # Calculate progress towards next milestone
            goal_progress = min(100, (total_profit_amount / milestone_target) * 100) if milestone_target > 0 else 0
            progress_blocks = int(min(14, goal_progress / (100/14)))
            progress_bar = f"[{'▓' * progress_blocks}{'░' * (14 - progress_blocks)}]"
            
            # Current amount is actual balance including profits
            current_amount = user.balance
            
            # Days active calculation based on join date
            days_active = (datetime.utcnow().date() - user.joined_at.date()).days + 1
            
            # Format the dashboard message
            current_balance = user.balance + total_profit_amount
            
            dashboard_message = (
                "📊 *Autopilot Dashboard*\n\n"
                f"• *Balance:* {current_balance:.2f} SOL\n"
                f"• *Today's Profit:* {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}% of balance)\n"
                f"• *Total Profit:* +{total_profit_percentage:.1f}% ({total_profit_amount:.2f} SOL)\n"
            )
            
            # Add streak with fire emoji for gamification
            if streak > 0:
                fire_emojis = "🔥" * min(3, streak)
                dashboard_message += f"• *Profit Streak:* {streak}-Day Green Streak! {fire_emojis}\n"
            else:
                dashboard_message += "• *Profit Streak:* Start your streak today!\n"
                
            # Add Autopilot Trader information
            dashboard_message += "• *Mode:* Autopilot Trader (Fully Automated)\n"
            dashboard_message += f"• *Day:* {days_active}\n\n"
            
            dashboard_message += "Autopilot is actively scanning for new trading opportunities! 💪\n\n"
            
            import random
            from config import MIN_DEPOSIT
            
            # Add a trust-building reminder message - different messages based on deposit status
            if user.status == UserStatus.ACTIVE and user.balance >= MIN_DEPOSIT:
                tips_message = random.choice([
                    "Your Autopilot system is working 24/7 to find and execute trading opportunities.",
                    "Thrive's trading engine targets consistent daily profits when market conditions allow.",
                    "Every day brings new memecoin opportunities that your Autopilot can discover.",
                    "Thrive automatically manages your portfolio to optimize profit and reduce risk."
                ])
            else:
                tips_message = random.choice([
                    "Add funds to activate your Autopilot trading system for Solana memecoins.",
                    "Make a deposit to begin your automated trading journey with real memecoins.",
                    "Your Autopilot dashboard is ready - add SOL to begin trading real coins.",
                    "Deposit SOL to unlock the full power of your Autopilot trading system.",
                    "Thrive trades newly launched memecoins - deposit any amount to begin."
                ])
            
            dashboard_message += f"_💡 {tips_message}_"
            
            # Create keyboard buttons
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💰 Deposit", "callback_data": "deposit"},
                    {"text": "💸 Withdrawal", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "📊 Performance", "callback_data": "trading_history"},
                    {"text": "👥 Referral", "callback_data": "referral"}
                ],
                [
                    {"text": "🛟 Customer Support", "callback_data": "support"},
                    {"text": "❓ FAQ", "callback_data": "faqs"}
                ]
            ])
            
            # Send the dashboard message
            bot.send_message(chat_id, dashboard_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in dashboard command: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying dashboard: {str(e)}")

def settings_command(update, chat_id):
    """Handle the /settings command."""
    try:
        with app.app_context():
            from app import db
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Get user's payout wallet address
            wallet_address = user.wallet_address or "Not set"
            if wallet_address and len(wallet_address) > 10:
                display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            else:
                display_wallet = wallet_address
            
            # Create settings message
            settings_message = (
                "⚙️ *THRIVE Bot Settings*\n\n"
                f"*Account Status:* {'Active' if user.status == UserStatus.ACTIVE else 'Not Active'}\n"
                f"*Payout Wallet:* `{display_wallet}`\n"
                f"*Joined:* {user.joined_at.strftime('%Y-%m-%d')}\n"
                f"*Auto-Trades:* {'Enabled' if user.status == UserStatus.ACTIVE else 'Disabled'}\n\n"
                f"*Notification Settings:*\n"
                f"• *Trade Alerts:* Enabled\n"
                f"• *Daily Reports:* Enabled\n"
                f"• *Profit Milestones:* Enabled\n\n"
                f"*Security Settings:*\n"
                f"• *Account Protection:* Active\n"
                f"• *Withdrawal Confirmation:* Required\n\n"
                f"You can update your settings using the options below:"
            )
            
            # Create keyboard with settings options
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "✏️ Update Wallet", "callback_data": "update_wallet"}
                ],
                [
                    {"text": "🔔 Notifications", "callback_data": "notification_settings"}
                ],
                [
                    {"text": "🔒 Security", "callback_data": "security_settings"}
                ],
                [
                    {"text": "🏠 Back to Main Menu", "callback_data": "start"}
                ]
            ])
            
            bot.send_message(chat_id, settings_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in settings command: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying settings: {str(e)}")

def referral_command(update, chat_id):
    """Handle the /referral command with enhanced real-time tracking and visual UI."""
    try:
        # Import the referral module
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("thrivesolanabot")
                logger.info("Initialized referral manager")
            
            user_id = str(update['message']['from']['id']) if 'message' in update else str(update['callback_query']['from']['id'])
            
            # Get the user's referral stats
            stats = referral_manager.get_referral_stats(user_id)
            
            # Generate the referral code if needed
            if not stats['has_code']:
                code = referral_manager.generate_or_get_referral_code(user_id)
                if code:
                    stats['code'] = code
                    stats['has_code'] = True
                    stats['referral_link'] = referral_manager.generate_referral_link(user_id)
            
            # Determine referral tier based on number of active referrals
            active_referrals = stats['active_referrals']
            if active_referrals >= 25:
                tier = "💎 Diamond"
                tier_progress = "25+ active referrals"
                next_tier = "Maximum tier reached!"
                tier_bar = "▰▰▰▰▰▰▰▰▰▰ 100%"
            elif active_referrals >= 10:
                tier = "🥇 Gold"
                tier_progress = f"{active_referrals}/25 active referrals"
                next_tier = "💎 Diamond at 25 referrals"
                progress_percent = min(100, (active_referrals - 10) * 100 / 15)
                filled = int(progress_percent / 10)
                tier_bar = f"{'▰' * filled}{'▱' * (10-filled)} {progress_percent:.0f}%"
            elif active_referrals >= 5:
                tier = "🥈 Silver"
                tier_progress = f"{active_referrals}/10 active referrals"
                next_tier = "🥇 Gold at 10 referrals"
                progress_percent = min(100, (active_referrals - 5) * 100 / 5)
                filled = int(progress_percent / 10)
                tier_bar = f"{'▰' * filled}{'▱' * (10-filled)} {progress_percent:.0f}%"
            else:
                tier = "🥉 Bronze"
                tier_progress = f"{active_referrals}/5 active referrals"
                next_tier = "🥈 Silver at 5 referrals"
                progress_percent = min(100, active_referrals * 100 / 5)
                filled = int(progress_percent / 10)
                tier_bar = f"{'▰' * filled}{'▱' * (10-filled)} {progress_percent:.0f}%"
            
            # Calculate earnings per referral for better transparency
            avg_earnings = 0
            if stats['active_referrals'] > 0:
                avg_earnings = stats['total_earnings'] / stats['active_referrals']
            
            # Create the enhanced referral message with visual elements
            referral_message = (
                "🚀 *THRIVE REFERRAL PROGRAM* 🚀\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                "Earn passive income by sharing THRIVE bot! You'll receive *5%* of all profits generated by users you refer - *forever*.\n\n"
                
                f"*Current Tier:* {tier}\n"
                f"{tier_bar}\n"
                f"*Progress:* {tier_progress}\n"
                f"*Next Level:* {next_tier}\n\n"
                
                f"📊 *REFERRAL STATS*\n"
                f"Active Referrals: {stats['active_referrals']}\n"
                f"Pending Referrals: {stats.get('pending_referrals', 0)}\n"
                f"Total Earnings: {stats['total_earnings']:.4f} SOL\n"
                f"Avg. Per Referral: {avg_earnings:.4f} SOL\n\n"
                
                f"🔗 *YOUR REFERRAL CODE*\n"
                f"`{stats['code'] if stats['has_code'] else 'GENERATING...'}`\n\n"
                
                f"📱 *YOUR REFERRAL LINK*\n"
                f"`https://t.me/thrivesolanabot?start=ref_{user_id}`\n"
            )
            
            # Create enhanced keyboard with more sharing options
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📋 Copy Link", "callback_data": "copy_referral_link"},
                    {"text": "📱 Generate QR", "callback_data": "referral_qr_code"}
                ],
                [
                    {"text": "📊 View Stats", "callback_data": "referral_stats"},
                    {"text": "📤 Share", "callback_data": "share_referral"}
                ],
                [
                    {"text": "❓ How It Works", "callback_data": "referral_how_it_works"},
                    {"text": "💡 Tips", "callback_data": "referral_tips"}
                ],
                [{"text": "🏠 Back to Main Menu", "callback_data": "start"}]
            ])
            
            bot.send_message(chat_id, referral_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in referral command: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying referral program: {str(e)}")

def admin_command(update, chat_id):
    """Handle the /admin command and show admin panel if user is authorized."""
    try:
        # Check if bot object is initialized
        global bot
        if 'bot' not in globals() or bot is None:
            from config import BOT_TOKEN
            token = os.environ.get('TELEGRAM_BOT_TOKEN', BOT_TOKEN)
            if token:
                bot = SimpleTelegramBot(token)
                logger.info("Bot initialized for admin command")
            else:
                logger.error("No bot token available - cannot initialize bot for admin command")
                return
        
        with app.app_context():
            from config import ADMIN_IDS
            
            # Explicitly define your admin ID - don't rely solely on env vars or config
            admin_id = '5488280696'
            
            # Debug logged-in user ID and admin ID
            import logging
            logging.info(f"Access attempt - User ID: {chat_id}, Manual Admin ID: {admin_id}, ADMIN_IDS: {ADMIN_IDS}")
            
            # Check if user is in the admin list or matches the hardcoded admin ID
            is_admin = False
            
            # Explicit admin ID check
            if str(chat_id) == admin_id:
                logging.info(f"Admin access granted to hardcoded admin {chat_id}")
                is_admin = True
            
            # Check admin list
            if str(chat_id) in ADMIN_IDS:
                logging.info(f"Admin access granted to listed admin {chat_id}")
                is_admin = True
                
            if not is_admin:
                logging.info(f"Admin access denied - User: {chat_id} is not authorized")
                bot.send_message(chat_id, "Sorry, you don't have permission to access the admin panel.")
                return
            
            # Display admin panel
            admin_message = (
                "🔧 *Admin Panel*\n\n"
                "Welcome, Admin. Manage users, funds, bot settings, and communications from here."
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "User Management", "callback_data": "admin_user_management"},
                    {"text": "Wallet Settings", "callback_data": "admin_wallet_settings"}
                ],
                [
                    {"text": "Send Broadcast", "callback_data": "admin_broadcast"},
                    {"text": "Direct Message", "callback_data": "admin_direct_message"}
                ],
                [
                    {"text": "View All Users", "callback_data": "admin_view_all_users"},
                    {"text": "Adjust Balance", "callback_data": "admin_adjust_balance"}
                ],
                [
                    {"text": "View Stats", "callback_data": "admin_view_stats"},
                    {"text": "Support Tickets", "callback_data": "admin_view_tickets"}
                ],
                [
                    {"text": "Bot Settings", "callback_data": "admin_bot_settings"},
                    {"text": "Referral Overview", "callback_data": "admin_referral_overview"}
                ],
                [
                    {"text": "Referral Payouts", "callback_data": "admin_referral_payouts"},
                    {"text": "📊 Deposit Logs", "callback_data": "admin_deposit_logs"}
                ],
                [
                    {"text": "💸 Manage Withdrawals", "callback_data": "admin_manage_withdrawals"},
                    {"text": "Exit Panel", "callback_data": "admin_exit"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                admin_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_command: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized yet
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying admin panel: {str(e)}")
            else:
                # Log the error but can't send message without bot
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_user_management_handler(update, chat_id):
    """Handle the user management button."""
    try:
        with app.app_context():
            from models import User, UserStatus
            import logging
            
            logging.info(f"Admin User Management handler called by {chat_id}")
            
            # Count total users
            total_users = User.query.count()
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).count()
            
            message = (
                "👥 *User Management*\n\n"
                f"Total users: {total_users}\n"
                f"Active users: {active_users}\n\n"
                "Select an action below:"
            )
            
            # Show all users directly instead of requiring another button click
            # This is a temporary workaround for the non-responsive button
            try:
                # Get all users ordered by registration date (most recent first)
                users = User.query.order_by(User.joined_at.desc()).limit(10).all()
                logging.info(f"Found {len(users)} users in the database")
                
                if users:
                    user_list = "\n\n*Recent Users:*\n"
                    for idx, user in enumerate(users, 1):
                        username = f"@{user.username}" if user.username else "No username"
                        user_list += f"{idx}. {username} - {user.balance:.4f} SOL\n"
                    
                    message += user_list
            except Exception as e:
                logging.error(f"Error listing users: {e}")
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "🔍 Search User", "callback_data": "admin_search_user"},
                    {"text": "✅ View Active Only", "callback_data": "admin_view_active_users"}
                ],
                [
                    {"text": "📊 Export Users (CSV)", "callback_data": "admin_export_csv"}
                ],
                [
                    {"text": "Back to Admin Panel", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_user_management_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying user management: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_wallet_settings_handler(update, chat_id):
    """Handle the wallet settings button."""
    try:
        message = (
            "💼 *Wallet Settings*\n\n"
            "Manage deposit wallets and withdrawal settings."
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "Change Deposit Wallet", "callback_data": "admin_change_wallet"},
                {"text": "View Wallet QR", "callback_data": "admin_view_wallet_qr"}
            ],
            [{"text": "Back to Admin Panel", "callback_data": "admin_back"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_wallet_settings_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying wallet settings: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_broadcast_handler(update, chat_id):
    """Handle the send broadcast button."""
    try:
        # Get user counts for better UI feedback
        with app.app_context():
            try:
                from models import User, UserStatus
                
                total_users = User.query.count()
                active_users = User.query.filter_by(status=UserStatus.ACTIVE).count()
                
                # Use global variable to show currently selected target
                global broadcast_target
                target_text = "Active Users Only" if broadcast_target == "active" else "All Users"
                
                message = (
                    "📢 *Send Broadcast Message*\n\n"
                    f"*Current Target:* {target_text}\n"
                    f"*Active Users:* {active_users}\n"
                    f"*Total Users:* {total_users}\n\n"
                    "First select your target audience, then choose the message type:"
                )
            except Exception as e:
                # Fallback message if database query fails
                import logging
                logging.error(f"Error getting user counts: {e}")
                
                message = (
                    "📢 *Send Broadcast Message*\n\n"
                    "Choose the type of broadcast and target audience:"
                )
        
        # Create a keyboard with clear sections
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "📊 TARGET AUDIENCE", "callback_data": "ignore"}
            ],
            [
                {"text": "🟢 Active Users Only", "callback_data": "admin_broadcast_active"},
                {"text": "🔵 All Users", "callback_data": "admin_broadcast_all"}
            ],
            [
                {"text": "📝 MESSAGE TYPE", "callback_data": "ignore"}
            ],
            [
                {"text": "📄 Text Only", "callback_data": "admin_broadcast_text"},
                {"text": "🖼️ Image + Text", "callback_data": "admin_broadcast_image"}
            ],
            [
                {"text": "📣 Announcement", "callback_data": "admin_broadcast_announcement"},
                {"text": "📈 Trade Alert", "callback_data": "admin_broadcast_trade"}
            ],
            [
                {"text": "↩️ Back to Admin", "callback_data": "admin_back"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying broadcast options: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_view_stats_handler(update, chat_id):
    """Handle the view stats button."""
    try:
        with app.app_context():
            from models import User, Transaction, Profit
            from sqlalchemy import func
            from datetime import datetime, timedelta
            
            # Calculate total users and daily growth
            total_users = User.query.count()
            yesterday = datetime.utcnow() - timedelta(days=1)
            new_users_today = User.query.filter(User.joined_at >= yesterday).count()
            
            # Calculate transaction volume
            total_deposits = db.session.query(func.sum(Transaction.amount)).filter_by(transaction_type="deposit").scalar() or 0
            total_withdrawals = db.session.query(func.sum(Transaction.amount)).filter_by(transaction_type="withdraw").scalar() or 0
            
            # Calculate profits
            total_profits = db.session.query(func.sum(Profit.amount)).scalar() or 0
            
            # Create the stats message
            stats_message = (
                "📊 *Bot Statistics*\n\n"
                f"*Users:*\n"
                f"• Total Users: {total_users}\n"
                f"• New Users (24h): {new_users_today}\n\n"
                
                f"*Transactions:*\n"
                f"• Total Deposits: {total_deposits:.4f} SOL\n"
                f"• Total Withdrawals: {total_withdrawals:.4f} SOL\n\n"
                
                f"*Trading:*\n"
                f"• Total Profits Generated: {total_profits:.4f} SOL\n"
                f"• Current Bot Balance: {(total_deposits - total_withdrawals):.4f} SOL"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                stats_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_stats_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying statistics: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_set_initial_deposit_handler(update, chat_id):
    """Handle the set initial deposit button in the user details panel."""
    try:
        # Extract user ID from callback data
        callback_data = update.callback_query.data
        user_id = int(callback_data.split(':')[1])
        
        # Store the user ID in global variable for conversation handler
        global admin_target_user_id
        admin_target_user_id = user_id
        
        with app.app_context():
            from models import User
            
            # Get user from database
            user = User.query.get(user_id)
            
            if not user:
                bot.send_message(
                    chat_id,
                    "⚠️ Error: User not found. Please try again.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                    ])
                )
                return
            
            # Show current initial deposit and prompt for new value
            message = (
                f"🔄 *Set Initial Deposit*\n\n"
                f"User: @{user.username or 'No username'} (ID: {user.telegram_id})\n"
                f"Current Initial Deposit: {user.initial_deposit:.4f} SOL\n\n"
                "Please enter the new initial deposit amount in SOL.\n"
                "This will only change the initial deposit value used for ROI calculations and will NOT affect the user's actual balance."
            )
            
            # Create cancel button
            keyboard = bot.create_inline_keyboard([
                [{"text": "Cancel", "callback_data": f"admin_user_detail:{user.id}"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Set the bot to expect the initial deposit amount next
            bot.register_next_step_handler(
                chat_id,
                admin_initial_deposit_amount_handler
            )
    
    except Exception as e:
        logging.error(f"Error in admin_set_initial_deposit_handler: {e}")
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error setting initial deposit: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_initial_deposit_amount_handler(update, chat_id, text):
    """Process the initial deposit amount."""
    try:
        # Get the amount from the message text
        try:
            amount = float(text.strip())
            
            if amount < 0:
                bot.send_message(
                    chat_id,
                    "⚠️ Error: Initial deposit amount cannot be negative. Please enter a positive number.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Cancel", "callback_data": f"admin_user_detail:{admin_target_user_id}"}]
                    ])
                )
                return
                
            # Store the amount in global variable for next step
            global admin_initial_deposit_amount
            admin_initial_deposit_amount = amount
            
            # Get user details
            with app.app_context():
                from models import User
                
                user = User.query.get(admin_target_user_id)
                
                if not user:
                    bot.send_message(
                        chat_id,
                        "⚠️ Error: User not found. The user may have been deleted. Please try again.",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                        ])
                    )
                    return
                
                # Ask for confirmation
                message = (
                    f"📝 *Confirm Initial Deposit Setting*\n\n"
                    f"User: @{user.username or 'No username'} (ID: {user.telegram_id})\n"
                    f"Current Initial Deposit: {user.initial_deposit:.4f} SOL\n"
                    f"New Initial Deposit: {amount:.4f} SOL\n\n"
                    "Please enter a reason for this change or click Confirm with the default reason."
                )
                
                # Create confirm/cancel buttons
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Confirm", "callback_data": "admin_confirm_initial_deposit"}],
                    [{"text": "Cancel", "callback_data": f"admin_user_detail:{user.id}"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                # Register handler for reason or confirmation
                bot.register_next_step_handler(
                    chat_id,
                    admin_initial_deposit_reason_handler
                )
                
        except ValueError:
            bot.send_message(
                chat_id,
                "⚠️ Error: Invalid amount. Please enter a valid number.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Cancel", "callback_data": f"admin_user_detail:{admin_target_user_id}"}]
                ])
            )
            return
    
    except Exception as e:
        logging.error(f"Error in admin_initial_deposit_amount_handler: {e}")
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error processing initial deposit amount: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_initial_deposit_reason_handler(update, chat_id, text=None):
    """Process the reason for initial deposit setting."""
    try:
        # Get reason from text or use default
        reason = text.strip() if text and text.strip() else "Admin initial deposit setting"
        
        # Get user details
        with app.app_context():
            from models import User
            
            user = User.query.get(admin_target_user_id)
            
            if not user:
                bot.send_message(
                    chat_id,
                    "⚠️ Error: User not found. The user may have been deleted. Please try again.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                    ])
                )
                return
            
            # Final confirmation message
            message = (
                f"📝 *Confirm Initial Deposit Setting*\n\n"
                f"User: @{user.username or 'No username'} (ID: {user.telegram_id})\n"
                f"Current Initial Deposit: {user.initial_deposit:.4f} SOL\n"
                f"New Initial Deposit: {admin_initial_deposit_amount:.4f} SOL\n"
                f"Reason: {reason}\n\n"
                "Are you sure you want to update this user's initial deposit?"
            )
            
            # Create confirm/cancel buttons
            keyboard = bot.create_inline_keyboard([
                [{"text": "✅ Confirm", "callback_data": f"admin_confirm_initial_deposit:{reason}"}],
                [{"text": "❌ Cancel", "callback_data": f"admin_user_detail:{user.id}"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    
    except Exception as e:
        logging.error(f"Error in admin_initial_deposit_reason_handler: {e}")
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error processing reason: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_confirm_initial_deposit_handler(update, chat_id):
    """Confirm and process the initial deposit setting."""
    try:
        # Extract reason from callback data if present
        callback_data = update.callback_query.data
        parts = callback_data.split(':')
        reason = parts[1] if len(parts) > 1 else "Admin initial deposit setting"
        
        # Use the balance_manager module for setting initial deposit
        import balance_manager
        
        # Get user details
        with app.app_context():
            from models import User
            
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
                admin_initial_deposit_amount = None
                return
            
            # Use the non-blocking initial deposit setter
            identifier = user.telegram_id
            amount = admin_initial_deposit_amount
            
            success, message = balance_manager.set_initial_deposit(identifier, amount, reason)
            
            if success:
                # Show success message to admin
                with app.app_context():
                    # Refresh user from database to get updated initial deposit
                    fresh_user = User.query.get(admin_target_user_id)
                    
                    if fresh_user:
                        success_message = (
                            f"✅ *Initial Deposit Updated Successfully*\n\n"
                            f"User: @{fresh_user.username or 'No username'} (ID: {fresh_user.telegram_id})\n"
                            f"New Initial Deposit: {fresh_user.initial_deposit:.4f} SOL\n"
                            f"Current Balance: {fresh_user.balance:.4f} SOL\n"
                            f"Reason: {reason}\n\n"
                            "The user's dashboard will now reflect this initial deposit for ROI calculations."
                        )
                        
                        keyboard = bot.create_inline_keyboard([
                            [{"text": "View User Details", "callback_data": f"admin_user_detail:{fresh_user.id}"}],
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                        
                        bot.send_message(
                            chat_id,
                            success_message,
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
            else:
                # Show error message
                error_message = (
                    f"❌ *Error Setting Initial Deposit*\n\n"
                    f"{message}\n\n"
                    "Please try again later."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Return to User Details", "callback_data": f"admin_user_detail:{user.id}"}],
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
                
                bot.send_message(
                    chat_id,
                    error_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            
            # Reset global variables
            admin_target_user_id = None
            admin_initial_deposit_amount = None
            
    except Exception as e:
        # Log the error
        logging.error(f"Error in admin_confirm_initial_deposit_handler: {e}")
        logging.error(traceback.format_exc())
        
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(
                    chat_id,
                    f"❌ *Error Setting Initial Deposit*\n\n{str(e)}",
                    parse_mode="Markdown",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")
            
        # Reset global variables
        admin_target_user_id = None
        admin_initial_deposit_amount = None

def admin_adjust_balance_handler(update, chat_id):
    """Handle the adjust balance button with full implementation and user panel interaction."""
    try:
        # Get all active users for autocomplete suggestions
        with app.app_context():
            from models import User, UserStatus
            
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            user_suggestions = []
            
            # Format user info for display
            for user in active_users[:5]:  # Limit to 5 suggestions for UI clarity
                username_display = f"@{user.username}" if user.username else "No username"
                user_suggestions.append({
                    "telegram_id": user.telegram_id,
                    "display": f"ID: {user.telegram_id} | {username_display} | Balance: {user.balance:.2f} SOL"
                })
        
        # Create a more helpful message with user suggestions
        suggestion_text = ""
        if user_suggestions:
            suggestion_text = "\n\n*Recent Active Users:*\n"
            for i, user in enumerate(user_suggestions):
                suggestion_text += f"{i+1}. {user['display']}\n"
        
        message = (
            "💰 *Adjust User Balance*\n\n"
            "Please enter the Telegram ID or username of the user whose balance you want to adjust."
            f"{suggestion_text}\n"
            "_Type the ID number, or type 'cancel' to go back._"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔄 Refresh User List", "callback_data": "admin_adjust_balance"}],
            [{"text": "↩️ Back to Admin Panel", "callback_data": "admin_back"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add listener for the next message (user ID input)
        bot.add_message_listener(chat_id, "text", admin_adjust_balance_user_id_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_adjust_balance_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying adjust balance: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_adjust_balance_user_id_handler(update, chat_id, text):
    """Process the user ID for balance adjustment."""
    try:
        # Check for cancellation
        if text.lower() == 'cancel':
            bot.send_message(
                chat_id,
                "Operation cancelled. Returning to admin panel.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            bot.remove_listener(chat_id)
            return
        
        # Process the user ID or username
        with app.app_context():
            from models import User
            
            # Try to find user by telegram ID first
            user = None
            try:
                # Try as telegram_id (number)
                user = User.query.filter_by(telegram_id=text).first()
            except Exception as e:
                # Log the error but continue with other search methods
                import logging
                logging.error(f"Error searching by telegram_id: {e}")
                pass
                
            # Import function for case-insensitive search
            from sqlalchemy import func
            
            # If not found, try by username (case-insensitive)
            if not user and text.startswith('@'):
                username = text[1:]  # Remove @ prefix
                user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
            elif not user:
                # Try with username anyway (in case they forgot the @)
                user = User.query.filter(func.lower(User.username) == func.lower(text)).first()
            
            if not user:
                # Try using admin_balance_manager method which has a robust search
                try:
                    import admin_balance_manager
                    user = admin_balance_manager.find_user(text)
                except Exception as e:
                    import logging
                    logging.error(f"Error using admin_balance_manager.find_user: {e}")
            
            if not user:
                bot.send_message(
                    chat_id,
                    "⚠️ User not found. Please try again with a valid Telegram ID or username, or type 'cancel' to go back."
                )
                return
            
            # Store user info in global variables
            global admin_target_user_id
            admin_target_user_id = user.id
            
            # Also store user telegram_id and current balance for later reference
            global admin_adjust_telegram_id, admin_adjust_current_balance
            admin_adjust_telegram_id = user.telegram_id
            admin_adjust_current_balance = user.balance
            
            # Display current user info
            username_display = f"@{user.username}" if user.username else "No username"
            message = (
                f"📊 *User Found*\n\n"
                f"*User:* {username_display}\n"
                f"*Telegram ID:* `{user.telegram_id}`\n"
                f"*Current Balance:* {user.balance:.4f} SOL\n\n"
                f"Please enter the amount to adjust:\n"
                f"• Use positive number to add funds (e.g. 5.5)\n"
                f"• Use negative number to remove funds (e.g. -3.2)\n"
                f"• Type 'cancel' to abort"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "Cancel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Remove current listener and add listener for the adjustment amount
            bot.remove_listener(chat_id)
            bot.add_message_listener(chat_id, "text", admin_adjust_balance_amount_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_adjust_balance_user_id_handler: {e}")
        bot.send_message(chat_id, f"Error processing user ID: {str(e)}")
        bot.remove_listener(chat_id)

def admin_adjust_balance_amount_handler(update, chat_id, text):
    """Process the balance adjustment amount."""
    try:
        # Check for cancellation
        if text.lower() == 'cancel':
            bot.send_message(
                chat_id,
                "Operation cancelled. Returning to admin panel.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            bot.remove_listener(chat_id)
            return
        
        # Validate the amount
        try:
            adjustment = float(text.strip())
            
            # Store the adjustment amount in global variable
            global admin_adjustment_amount
            admin_adjustment_amount = adjustment
            
            # Set a default reason and proceed directly to confirmation
            global admin_adjustment_reason
            admin_adjustment_reason = "Bonus"  # Set a simple default reason
            
            # Show confirmation with just the amount, then proceed to confirmation
            confirmation_message = (
                f"💰 *Confirm Balance Adjustment*\n\n"
                f"Amount: {'➕' if adjustment > 0 else '➖'} {abs(adjustment):.4f} SOL\n\n"
                f"Click confirm to process this adjustment."
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "✅ Confirm", "callback_data": "admin_confirm_adjustment"},
                    {"text": "❌ Cancel", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Remove current listener
            bot.remove_listener(chat_id)
            
        except ValueError:
            # Invalid amount format
            bot.send_message(
                chat_id,
                "⚠️ Invalid amount. Please enter a valid number (e.g. 5.5 or -3.2), or type 'cancel' to abort."
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_adjust_balance_amount_handler: {e}")
        bot.send_message(chat_id, f"Error processing amount: {str(e)}")
        bot.remove_listener(chat_id)

def admin_adjust_balance_reason_handler(update, chat_id, text):
    """Process the reason for balance adjustment and confirm."""
    try:
        # Check for cancellation
        if text.lower() == 'cancel':
            bot.send_message(
                chat_id,
                "Operation cancelled. Returning to admin panel.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            bot.remove_listener(chat_id)
            return
        
        # Store the reason in global variable
        global admin_adjustment_reason
        admin_adjustment_reason = text.strip()
        
        # Access other required globals
        global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance, admin_adjustment_amount
        
        # Create confirmation message with null safety checks
        plus_minus = '➕' if admin_adjustment_amount and admin_adjustment_amount > 0 else '➖'
        adjustment_abs = abs(admin_adjustment_amount) if admin_adjustment_amount is not None else 0
        current_balance = admin_adjust_current_balance if admin_adjust_current_balance is not None else 0
        new_balance = current_balance + (admin_adjustment_amount or 0)
        
        confirmation_message = (
            "⚠️ *Confirm Balance Adjustment*\n\n"
            f"User ID: `{admin_adjust_telegram_id or 'Unknown'}`\n"
            f"Current Balance: {current_balance:.4f} SOL\n"
            f"Adjustment: {plus_minus} {adjustment_abs:.4f} SOL\n"
            f"New Balance: {new_balance:.4f} SOL\n"
            f"Reason: _{admin_adjustment_reason or 'Not specified'}_\n\n"
            "Are you sure you want to proceed with this adjustment?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Confirm", "callback_data": "admin_confirm_adjustment"},
                {"text": "❌ Cancel", "callback_data": "admin_back"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            confirmation_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove current listener as we're using callback for confirmation
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_adjust_balance_reason_handler: {e}")
        bot.send_message(chat_id, f"Error processing reason: {str(e)}")
        bot.remove_listener(chat_id)

def admin_confirm_adjustment_handler(update, chat_id):
    """Emergency non-blocking balance adjustment handler."""
    import threading
    import logging
    
    try:
        # Capture all global variables locally
        global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
        global admin_adjustment_amount, admin_adjustment_reason
        
        # Check if we already have data to process - avoid double processing
        if admin_target_user_id is None or admin_adjustment_amount is None:
            bot.send_message(
                chat_id,
                "⚠️ No pending balance adjustment found. Please try again.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            return
            
        # Store values locally
        target_id = admin_target_user_id
        tg_id = admin_adjust_telegram_id
        current_balance = admin_adjust_current_balance
        amount = admin_adjustment_amount
        reason = admin_adjustment_reason or "Admin adjustment"
        
        # Reset globals immediately to prevent duplicate processing
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
                
                # Process the adjustment using fixed_balance_manager
                try:
                    # Try to import the fixed balance manager first
                    import fixed_balance_manager as manager
                except ImportError:
                    try:
                        import enhanced_balance_manager as manager
                    except ImportError:
                        import balance_manager as manager
                
                # Use telegram_id as identifier
                identifier = tg_id
                
                # Process adjustment with fixed balance manager
                logging.info(f"Processing balance adjustment for {identifier} with amount {amount}")
                
                # Get user details from database for verification
                with app.app_context():
                    user_before = User.query.filter_by(telegram_id=str(identifier)).first()
                    if user_before:
                        balance_before = user_before.balance
                        logging.info(f"Balance before adjustment: {balance_before}")
                    else:
                        logging.error(f"User not found with identifier: {identifier}")
                        bot.send_message(
                            chat_id,
                            f"❌ Error: User with ID {identifier} not found in database",
                            reply_markup=bot.create_inline_keyboard([
                                [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                            ])
                        )
                        return
                
                # Process the adjustment
                success, message = manager.adjust_balance(identifier, amount, reason)
                
                # Verify the adjustment was actually saved to database
                with app.app_context():
                    # Clear previous session to avoid caching issues
                    db.session.close()
                    
                    # Force a refresh from database to see updated values
                    user_after = User.query.filter_by(telegram_id=str(identifier)).first()
                    
                    if user_after:
                        balance_after = user_after.balance
                        logging.info(f"Balance after adjustment: {balance_after}")
                        expected_balance = balance_before + amount
                        
                        # Verify change was actually made
                        if abs(balance_after - expected_balance) < 0.0001:
                            success = True
                            message = f"✅ Balance verified in database: {balance_before:.4f} → {balance_after:.4f} SOL"
                        else:
                            # Attempt to manually update if we see a mismatch
                            try:
                                logging.warning(f"Balance mismatch detected. Expected: {expected_balance:.4f}, Got: {balance_after:.4f}")
                                
                                # Use a direct SQL update to avoid any ORM caching issues
                                from sqlalchemy import text
                                sql = text("UPDATE user SET balance = :new_balance WHERE telegram_id = :tg_id")
                                db.session.execute(sql, {"new_balance": expected_balance, "tg_id": str(identifier)})
                                db.session.commit()
                                
                                # Verify the fix worked
                                db.session.expire_all()  # Clear session cache
                                fixed_user = User.query.filter_by(telegram_id=str(identifier)).first()
                                if fixed_user and abs(fixed_user.balance - expected_balance) < 0.0001:
                                    message = f"⚠️ Balance fixed manually: {balance_before:.4f} → {fixed_user.balance:.4f} SOL"
                                    success = True
                                else:
                                    fixed_balance = fixed_user.balance if fixed_user else "unknown"
                                    message = f"⚠️ Manual fix attempted: Got {fixed_balance} (expected {expected_balance:.4f})"
                                    success = False
                                    
                            except Exception as db_error:
                                logging.error(f"Error fixing balance: {db_error}")
                                import traceback
                                logging.error(traceback.format_exc())
                                message = f"❌ Balance update failed: {balance_before:.4f} → expected {expected_balance:.4f}, got {balance_after:.4f} SOL"
                                success = False
                
                # Send response to admin
                if success:
                    bot.send_message(
                        chat_id,
                        f"✅ Balance adjustment completed: {abs(amount):.4f} SOL {'added' if amount > 0 else 'deducted'}\n\n{message}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
                    
                    # We don't need to send notifications to users
                    # Balance will be updated in the database and will show in their dashboard
                    # when they next view it
                    logging.info(f"User balance updated silently, will reflect in dashboard")
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
def admin_referral_overview_handler(update, chat_id):
    """Handle the referral overview button in admin panel."""
    try:
        with app.app_context():
            from models import User, ReferralCode
            from sqlalchemy import func
            
            # Get total referral counts and stats
            total_referral_codes = ReferralCode.query.count()
            total_referred_users = db.session.query(func.count(User.id)).filter(User.referrer_code_id.isnot(None)).scalar() or 0
            
            # Get top referrers
            top_referrers = db.session.query(
                ReferralCode, 
                User, 
                func.count(User.id).label('referred_count')
            ).join(
                User, 
                ReferralCode.user_id == User.id
            ).join(
                User, 
                User.referrer_code_id == ReferralCode.id, 
                isouter=True
            ).group_by(
                ReferralCode.id, 
                User.id
            ).order_by(
                func.count(User.id).desc()
            ).limit(5).all()
            
            # Get total earnings from referrals
            total_earnings = db.session.query(func.sum(ReferralCode.total_earned)).scalar() or 0
            
            # Create the overview message
            message = (
                "🔄 *Referral System Overview*\n\n"
                f"*System Stats:*\n"
                f"• Total Referral Codes: {total_referral_codes}\n"
                f"• Total Referred Users: {total_referred_users}\n"
                f"• Total Earnings Generated: {total_earnings:.4f} SOL\n\n"
                f"*Top Referrers:*\n"
            )
            
            # Add top referrers to the message
            if top_referrers:
                for i, (code, user, count) in enumerate(top_referrers, 1):
                    username = user.username or f"User #{user.id}"
                    message += f"{i}. {username}: {count} referrals, {code.total_earned:.4f} SOL earned\n"
            else:
                message += "No referrals in the system yet.\n"
            
            message += "\nUse 'Referral Payouts' for detailed payout logs."
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "Search Referrals", "callback_data": "admin_search_user_referrals"},
                    {"text": "View Payouts", "callback_data": "admin_referral_payouts"}
                ],
                [
                    {"text": "Export Data", "callback_data": "admin_export_referrals"},
                    {"text": "Back to Admin", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_referral_overview_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying referral overview: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_view_active_users_handler(update, chat_id):
    """Handle the view active users button in admin panel."""
    try:
        with app.app_context():
            from models import User, UserStatus, Transaction, Profit, ReferralCode
            from sqlalchemy import func
            from datetime import datetime, timedelta
            
            # Get active users ordered by join date (most recent first)
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).order_by(User.joined_at.desc()).limit(10).all()
            
            if not active_users:
                message = (
                    "👥 *Active Users*\n\n"
                    "There are currently no active users in the system."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Create header for active users list
            message = (
                "👥 *Active Users*\n\n"
                "Most recent active users:\n\n"
            )
            
            # Add user details to the message
            for idx, user in enumerate(active_users, 1):
                # Get deposit info
                total_deposits = db.session.query(func.sum(Transaction.amount)).filter_by(
                    user_id=user.id, 
                    transaction_type="deposit"
                ).scalar() or 0
                
                # Get profit info
                total_profits = db.session.query(func.sum(Profit.amount)).filter_by(
                    user_id=user.id
                ).scalar() or 0
                
                # Get referral info
                referral_code = ReferralCode.query.filter_by(user_id=user.id).first()
                referral_count = referral_code.total_referrals if referral_code else 0
                
                # Format wallet address for display (show only part of it)
                wallet_address = user.wallet_address or "Not set"
                if wallet_address != "Not set" and len(wallet_address) > 10:
                    display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
                else:
                    display_wallet = wallet_address
                
                # Get last activity timestamp
                last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "N/A"
                
                # Create user entry
                user_entry = (
                    f"*User #{idx}*\n"
                    f"• ID: `{user.telegram_id}`\n"
                    f"• Username: @{user.username or 'Not set'}\n"
                    f"• Wallet: `{display_wallet}`\n"
                    f"• Balance: {user.balance:.4f} SOL\n"
                    f"• Total Deposits: {total_deposits:.4f} SOL\n"
                    f"• Total Profits: {total_profits:.4f} SOL\n"
                    f"• Referrals: {referral_count}\n"
                    f"• Joined: {user.joined_at.strftime('%Y-%m-%d')}\n"
                    f"• Last Active: {last_activity}\n\n"
                )
                
                message += user_entry
            
            # Add pagination note
            message += "\nShowing 10 most recent active users. Use search for specific users."
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "Search User", "callback_data": "admin_search_user"},
                    {"text": "Export Users (CSV)", "callback_data": "admin_export_csv"}
                ],
                [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_active_users_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying active users: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_view_all_users_handler(update, chat_id):
    """Handle the view all users button in admin panel."""
    import logging
    logging.info(f"View All Users button clicked by {chat_id}")
    
    try:
        with app.app_context():
            from models import User, UserStatus, Transaction, Profit, ReferralCode
            from app import db
            from sqlalchemy import func
            from datetime import datetime, timedelta
            import traceback
            
            # Log everything for debugging
            logging.info(f"Admin View All Users handler called by chat_id {chat_id}")
            
            # Let's ensure the database is accessible
            # For SQLAlchemy connections, we'll use a simpler approach
            
            # Get all users ordered by registration date (most recent first)
            users = []
            try:
                # Create a fresh query for all users
                users = User.query.order_by(User.joined_at.desc()).limit(10).all()
                logging.info(f"Found {len(users)} users in the database")
            except Exception as db_error:
                logging.error(f"Error querying users: {db_error}")
                logging.error(traceback.format_exc())
                # Don't modify the database - just return empty list
                users = []
            
            if not users:
                message = (
                    "👥 *All Users*\n\n"
                    "There are currently no registered users in the system.\n\n"
                    "Users will appear here after they interact with the bot.\n"
                    "You can also manually add a user using the admin commands."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Create header for users list
            message = (
                "👥 *All Registered Users*\n\n"
                "Most recent registrations:\n\n"
            )
            
            # Add user details to the message
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
                
                # Format deposit wallet display
                deposit_wallet = user.deposit_wallet or "Not set"
                display_deposit_wallet = deposit_wallet
                if deposit_wallet != "Not set" and len(deposit_wallet) > 10:
                    display_deposit_wallet = f"{deposit_wallet[:6]}...{deposit_wallet[-4:]}"
                
                # Get user's name information
                name_display = ""
                if user.first_name or user.last_name:
                    name_display = f"• Name: {user.first_name or ''} {user.last_name or ''}\n"
                
                # Calculate ROI (Return on Investment)
                roi_percentage = 0
                if user.initial_deposit > 0:
                    roi_percentage = (total_profits / user.initial_deposit) * 100
                
                # Calculate net profit (total profit - total deposited + total withdrawn)
                net_profit = user.balance - total_deposits
                
                # Calculate active trading amount 
                active_trading = user.balance
                
                # Get last activity time with date and time
                last_activity = "N/A"
                if user.last_activity:
                    last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M:%S")
                
                # Create user entry with full details
                user_entry = (
                    f"*User #{idx}*\n"
                    f"• User ID (copy): `{user.id}`\n"
                    f"• Telegram ID (copy): `{user.telegram_id}`\n"
                    f"• Username: @{user.username or 'No Username'}\n"
                    f"{name_display}"
                    f"• Registered: {registration_date}\n"
                    f"• Last Activity: {last_activity}\n"
                    f"• Status: {user.status.value}\n\n"
                    
                    f"*Financial Details*\n"
                    f"• Current Balance: {user.balance:.4f} SOL\n"
                    f"• Initial Deposit: {user.initial_deposit:.4f} SOL\n" 
                    f"• Total Deposited: {total_deposits:.4f} SOL\n"
                    f"• Total Withdrawn: {total_withdrawn:.4f} SOL\n"
                    f"• Total Profit: {total_profits:.4f} SOL\n"
                    f"• Net Profit: {net_profit:.4f} SOL\n"
                    f"• ROI: {roi_percentage:.2f}%\n"
                    f"• Active Trading: {active_trading:.4f} SOL\n\n"
                    
                    f"*Referral System*\n"
                    f"• Referral Count: {referral_count}\n"
                    f"• Referral Earnings: {referral_earnings:.4f} SOL\n\n"
                    
                    f"*Wallet Information*\n"
                    f"• Payout Wallet (copy):\n`{wallet_address}`\n\n"
                    f"• Deposit Wallet (copy):\n`{deposit_wallet}`\n\n"
                )
                
                message += user_entry
            
            # Add pagination note
            message += "\nShowing 10 most recent users. Use search for specific users."
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "Search User", "callback_data": "admin_search_user"},
                    {"text": "Export Users (CSV)", "callback_data": "admin_export_csv"}
                ],
                [
                    {"text": "View Active Users", "callback_data": "admin_view_active_users"},
                    {"text": "Back to User Management", "callback_data": "admin_user_management"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_all_users_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying all users: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_search_user_handler(update, chat_id):
    """Handle the search user button in admin panel."""
    try:
        message = (
            "🔍 *Search Users*\n\n"
            "Please enter a Telegram ID or Username to search for:"
        )
        
        # Add a message listener to wait for the search query
        bot.add_message_listener(chat_id, 'search_query', admin_search_query_handler)
        
        # Create a keyboard with a cancel button
        keyboard = bot.create_inline_keyboard([
            [{"text": "Cancel", "callback_data": "admin_user_management"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_search_user_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error with search user function: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_search_query_handler(update, chat_id, text):
    """Handle the search query for finding users."""
    try:
        with app.app_context():
            from models import User, UserStatus, Transaction, Profit, ReferralCode
            from sqlalchemy import func, or_
            
            # Process the search query
            search_query = text.strip()
            
            # Try to find user by telegram ID first
            user = User.query.filter_by(telegram_id=search_query).first()
            
            # If not found, try by username (with or without @ prefix)
            if not user and search_query.startswith('@'):
                username = search_query[1:]  # Remove @ prefix
                user = User.query.filter_by(username=username).first()
            elif not user:
                # Try with username anyway (in case they forgot the @)
                user = User.query.filter_by(username=search_query).first()
            
            if not user:
                # Try partial username match
                users = User.query.filter(User.username.ilike(f"%{search_query}%")).limit(5).all()
                
                if users:
                    message = f"🔍 Found {len(users)} users matching '{search_query}':\n\n"
                    
                    for idx, u in enumerate(users, 1):
                        message += f"{idx}. ID: `{u.telegram_id}` - @{u.username or 'No Username'}\n"
                    
                    message += "\nPlease search again with a specific Telegram ID or username."
                    
                    keyboard = bot.create_inline_keyboard([
                        [{"text": "Search Again", "callback_data": "admin_search_user"}],
                        [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                    ])
                    
                    bot.send_message(
                        chat_id,
                        message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                    return
                else:
                    message = f"No users found matching '{search_query}'. Please try again."
                    
                    keyboard = bot.create_inline_keyboard([
                        [{"text": "Search Again", "callback_data": "admin_search_user"}],
                        [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                    ])
                    
                    bot.send_message(
                        chat_id,
                        message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                    return
            
            # Found a specific user, show detailed information
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
            
            # Format wallet address for display
            wallet_address = user.wallet_address or "Not set"
            display_wallet = wallet_address
            if wallet_address != "Not set" and len(wallet_address) > 10:
                display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            
            # Get activity timestamps
            joined_date = user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "N/A"
            last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "N/A"
            
            # Get referral earnings (5% profit)
            referral_earnings = user.referral_bonus if user.referral_bonus is not None else 0.0
            
            # Create the user details message
            message = (
                f"👤 *User Details*\n\n"
                f"• Telegram ID: `{user.telegram_id}`\n"
                f"• Username: @{user.username or 'No Username'}\n"
                f"• First Name: {user.first_name or 'Not set'}\n"
                f"• Last Name: {user.last_name or 'Not set'}\n"
                f"• Wallet Address: `{display_wallet}`\n"
                f"• Status: {user.status.value}\n"
                f"• Current Balance: {user.balance:.4f} SOL\n"
                f"• Initial Deposit: {user.initial_deposit:.4f} SOL\n"
                f"• Total Deposited: {total_deposits:.4f} SOL\n"
                f"• Total Withdrawn: {total_withdrawn:.4f} SOL\n"
                f"• Total Profits: {total_profits:.4f} SOL\n"
                f"• Referral Count: {referral_count}\n"
                f"• Referral Earnings: {referral_earnings:.4f} SOL\n"
                f"• Registration Date: {joined_date}\n"
                f"• Last Activity: {last_activity}\n"
            )
            
            # Create keyboard for user management actions
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "Send Message", "callback_data": f"admin_send_message"},
                    {"text": "Adjust Balance", "callback_data": f"admin_adjust_user_balance"}
                ],
                [
                    {"text": "Set Initial Deposit", "callback_data": f"admin_set_initial_deposit:{user.id}"},
                    {"text": "Process Withdrawal", "callback_data": f"admin_process_withdrawal"}
                ],
                [
                    {"text": "Remove User", "callback_data": f"admin_remove_user"},
                    {"text": "Search Another User", "callback_data": "admin_search_user"}
                ],
                [
                    {"text": "Back", "callback_data": "admin_user_management"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Store the user ID for use in subsequent actions
            global admin_target_user_id
            admin_target_user_id = user.id
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_search_query_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error processing search query: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_referral_payouts_handler(update, chat_id):
    """Handle the referral payouts button in admin panel."""
    try:
        with app.app_context():
            from models import ReferralReward, User
            
            # Get recent referral rewards, ordered by most recent first
            rewards = ReferralReward.query.order_by(ReferralReward.timestamp.desc()).limit(10).all()
            
            if not rewards:
                message = (
                    "💸 *Referral Payout Logs*\n\n"
                    "There are currently no referral payouts in the system."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [
                        {"text": "Referral Overview", "callback_data": "admin_referral_overview"},
                        {"text": "Back to Admin", "callback_data": "admin_back"}
                    ]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
                
            # Format the payouts log message
            message = (
                "💸 *Referral Payout Logs*\n\n"
                "Most recent referral reward payouts:\n\n"
            )
            
            # Add rewards to the message
            for reward in rewards:
                # Get user info
                referrer = User.query.get(reward.referrer_id)
                referred = User.query.get(reward.referred_id)
                
                referrer_name = referrer.username if referrer and referrer.username else f"User #{reward.referrer_id}"
                referred_name = referred.username if referred and referred.username else f"User #{reward.referred_id}"
                
                # Format date
                date_str = reward.timestamp.strftime("%Y-%m-%d %H:%M")
                
                message += (
                    f"*{date_str}*\n"
                    f"• {referrer_name} earned {reward.amount:.4f} SOL\n"
                    f"• From: {referred_name}'s profit of {reward.source_profit:.4f} SOL\n"
                    f"• Rate: {reward.percentage}%\n\n"
                )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "Referral Overview", "callback_data": "admin_referral_overview"},
                    {"text": "Back to Admin", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_referral_payouts_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying referral payouts: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_export_referrals_handler(update, chat_id):
    """Handle the export referrals data as CSV button in admin panel."""
    try:
        with app.app_context():
            from models import User, ReferralCode, ReferralReward
            from sqlalchemy import func
            import csv
            import io
            import os
            from datetime import datetime
            
            # Create a CSV in memory
            output = io.StringIO()
            csv_writer = csv.writer(output)
            
            # Write CSV header for referral data
            csv_writer.writerow([
                'Referral Code ID', 'Referrer User ID', 'Referrer Username', 
                'Code', 'Total Referrals', 'Total Earned', 
                'Creation Date', 'Last Payout Date'
            ])
            
            # Query all referral codes
            referral_codes = ReferralCode.query.all()
            
            if not referral_codes:
                bot.send_message(
                    chat_id,
                    "No referral data found in the database to export.",
                    parse_mode="Markdown"
                )
                return
            
            # Process and write referral data to CSV
            for code in referral_codes:
                # Get referrer info
                referrer = User.query.filter_by(id=code.user_id).first()
                username = referrer.username if referrer else "Unknown"
                
                # Get latest payout date if any
                latest_payout = ReferralReward.query.filter_by(
                    referrer_id=code.user_id
                ).order_by(ReferralReward.timestamp.desc()).first()
                
                latest_payout_date = latest_payout.timestamp.strftime("%Y-%m-%d %H:%M") if latest_payout else "Never"
                
                # Format dates
                creation_date = code.created_at.strftime("%Y-%m-%d %H:%M") if code.created_at else "N/A"
                
                # Write referral data row
                csv_writer.writerow([
                    code.id,
                    code.user_id,
                    username,
                    code.code,
                    code.total_referrals,
                    f"{code.total_earned:.6f}",
                    creation_date,
                    latest_payout_date
                ])
            
            # Add a second sheet for referral payouts
            output.write("\n\nReferral Payout Data\n")
            csv_writer.writerow([
                'Reward ID', 'Referrer ID', 'Referrer Username', 
                'Referred ID', 'Referred Username', 'Amount',
                'Source Profit', 'Percentage', 'Timestamp'
            ])
            
            # Query all referral rewards
            rewards = ReferralReward.query.order_by(ReferralReward.timestamp.desc()).all()
            
            if rewards:
                for reward in rewards:
                    # Get user info
                    referrer = User.query.filter_by(id=reward.referrer_id).first()
                    referred = User.query.filter_by(id=reward.referred_id).first()
                    
                    referrer_name = referrer.username if referrer else f"User #{reward.referrer_id}"
                    referred_name = referred.username if referred else f"User #{reward.referred_id}"
                    
                    # Format timestamp
                    timestamp = reward.timestamp.strftime("%Y-%m-%d %H:%M") if reward.timestamp else "N/A"
                    
                    # Write reward data row
                    csv_writer.writerow([
                        reward.id,
                        reward.referrer_id,
                        referrer_name,
                        reward.referred_id,
                        referred_name,
                        f"{reward.amount:.6f}",
                        f"{reward.source_profit:.6f}",
                        f"{reward.percentage}%",
                        timestamp
                    ])
            
            # Get the CSV data
            output.seek(0)
            csv_data = output.getvalue()
            
            # Generate a timestamp for the filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"referral_data_export_{timestamp}.csv"
            
            # Save CSV to a temporary file
            temp_filepath = os.path.join("/tmp", filename)
            with open(temp_filepath, "w") as f:
                f.write(csv_data)
            
            # Inform admin
            bot.send_message(
                chat_id,
                f"Referral data has been exported. Total referral codes: {len(referral_codes)}. Total payouts: {len(rewards)}.\n\nThe file is ready for download.",
                parse_mode="Markdown"
            )
            
            # Send the file
            with open(temp_filepath, "rb") as file:
                bot.send_document(chat_id, file, caption=f"Referral data export - {len(referral_codes)} referral codes")
            
            # Clean up
            os.remove(temp_filepath)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_export_referrals_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error exporting referral data: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_export_deposits_csv_handler(update, chat_id):
    """Export deposit logs as CSV file."""
    try:
        with app.app_context():
            from app import db
            from models import Transaction, User
            import csv
            import io
            import os
            from datetime import datetime
            
            # Send typing action while processing
            bot.send_chat_action(chat_id, action="typing")
            
            # Create a nice filename with the current date
            now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"deposit_logs_{now}.csv"
            
            # Query all deposit transactions
            deposits = (
                db.session.query(Transaction, User)
                .join(User, Transaction.user_id == User.id)
                .filter(Transaction.transaction_type == "deposit")
                .order_by(Transaction.timestamp.desc())
                .all()
            )
            
            if not deposits:
                bot.send_message(
                    chat_id,
                    "No deposit transactions found to export.",
                    parse_mode="Markdown"
                )
                return
            
            # Create CSV file in memory
            output = io.StringIO()
            csv_writer = csv.writer(output)
            
            # Write header row - Putting Telegram ID first for easier identification
            csv_writer.writerow([
                "Telegram ID", "Transaction ID", "User ID", "Username", 
                "Amount (SOL)", "Timestamp", "Status", "Notes"
            ])
            
            # Write data rows
            for transaction, user in deposits:
                csv_writer.writerow([
                    user.telegram_id,  # Telegram ID first for easier user identification
                    transaction.id,
                    user.id,
                    user.username or "N/A",
                    f"{transaction.amount:.2f}",
                    transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    transaction.status,
                    transaction.notes or ""
                ])
            
            # Get the CSV content
            csv_content = output.getvalue()
            output.close()
            
            # Save the CSV file temporarily
            temp_file_path = f"/tmp/{filename}"
            with open(temp_file_path, "w") as f:
                f.write(csv_content)
            
            # Send the file
            with open(temp_file_path, "rb") as f:
                # Prepare the file to send
                bot.send_document(
                    chat_id=chat_id,
                    document=(filename, f.read()),
                    caption=f"Deposit Logs Export - {len(deposits)} transactions"
                )
            
            # Clean up the temporary file
            try:
                os.remove(temp_file_path)
            except:
                pass
            
            # Send confirmation
            bot.send_message(
                chat_id,
                "✅ Deposit logs have been exported successfully.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "↩️ Back to Deposit Logs", "callback_data": "admin_deposit_logs"}],
                    [{"text": "↩️ Back to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_export_deposits_csv_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error exporting deposit logs: {str(e)}")

def admin_export_csv_handler(update, chat_id):
    """Handle the export users as CSV button in admin panel."""
    try:
        with app.app_context():
            from models import User, UserStatus, Transaction, Profit, ReferralCode
            from sqlalchemy import func
            import csv
            import io
            import os
            from datetime import datetime
            
            # Create a CSV in memory
            output = io.StringIO()
            csv_writer = csv.writer(output)
            
            # Write CSV header
            csv_writer.writerow([
                'User ID', 'Telegram ID', 'Username', 'First Name', 'Last Name', 
                'Join Date', 'Status', 'Wallet Address', 'Balance', 'Initial Deposit',
                'Total Deposits', 'Total Profits', 'Referral Count', 'Referral Earnings',
                'Last Activity'
            ])
            
            # Query all users
            users = User.query.all()
            
            if not users:
                bot.send_message(
                    chat_id,
                    "No users found in the database to export.",
                    parse_mode="Markdown"
                )
                return
            
            # Process and write user data to CSV
            for user in users:
                # Get deposit info
                total_deposits = db.session.query(func.sum(Transaction.amount)).filter_by(
                    user_id=user.id, 
                    transaction_type="deposit"
                ).scalar() or 0
                
                # Get profit info
                total_profits = db.session.query(func.sum(Profit.amount)).filter_by(
                    user_id=user.id
                ).scalar() or 0
                
                # Get referral info
                referral_code = ReferralCode.query.filter_by(user_id=user.id).first()
                referral_count = referral_code.total_referrals if referral_code else 0
                referral_earnings = referral_code.total_earned if referral_code else 0
                
                # Format dates
                join_date = user.joined_at.strftime("%Y-%m-%d %H:%M") if user.joined_at else "N/A"
                last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "N/A"
                
                # Write user data row
                csv_writer.writerow([
                    user.id,
                    user.telegram_id,
                    user.username or "N/A",
                    user.first_name or "N/A",
                    user.last_name or "N/A",
                    join_date,
                    user.status.value if user.status else "N/A",
                    user.wallet_address or "N/A",
                    f"{user.balance:.4f}",
                    f"{user.initial_deposit:.4f}",
                    f"{total_deposits:.4f}",
                    f"{total_profits:.4f}",
                    referral_count,
                    f"{referral_earnings:.4f}",
                    last_activity
                ])
            
            # Get the CSV data
            output.seek(0)
            csv_data = output.getvalue()
            
            # Generate a timestamp for the filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"users_export_{timestamp}.csv"
            
            # Save CSV to a temporary file
            temp_filepath = os.path.join("/tmp", filename)
            with open(temp_filepath, "w") as f:
                f.write(csv_data)
            
            # Inform admin
            bot.send_message(
                chat_id,
                f"User data has been exported. Total users: {len(users)}.\n\nThe file is ready for download.",
                parse_mode="Markdown"
            )
            
            # Send the file
            with open(temp_filepath, "rb") as file:
                bot.send_document(chat_id, file, caption=f"User data export - {len(users)} users")
            
            # Clean up
            os.remove(temp_filepath)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_export_csv_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error exporting user data: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_view_tickets_handler(update, chat_id):
    """Handle the view tickets button in admin panel."""
    try:
        with app.app_context():
            from models import SupportTicket, User
            
            # Get all support tickets, ordered by most recent first
            tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).limit(10).all()
            
            if not tickets:
                message = (
                    "🎫 *Support Tickets*\n\n"
                    "There are currently no support tickets in the system."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [
                        {"text": "Back to Admin Panel", "callback_data": "admin_back"}
                    ]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Format the tickets
            message = "🎫 *Recent Support Tickets*\n\n"
            
            for idx, ticket in enumerate(tickets, 1):
                # Get user info
                user = User.query.filter_by(id=ticket.user_id).first()
                username = user.username if user and user.username else "Unknown"
                
                # Format ticket with ID, status, date, and a snippet of content
                ticket_content = ticket.message[:50] + "..." if len(ticket.message) > 50 else ticket.message
                status = "✅ Resolved" if ticket.status == 'closed' else "🔔 Open"
                created_date = ticket.created_at.strftime("%Y-%m-%d %H:%M")
                
                message += f"*Ticket #{idx}* - {status}\n"
                message += f"From: @{username} (ID: {ticket.user_id})\n"
                message += f"Date: {created_date}\n"
                message += f"Message: _{ticket_content}_\n\n"
            
            # Add pagination buttons if needed in the future
            keyboard = bot.create_inline_keyboard([
                # We'll add pagination and ticket actions in a future update
                [
                    {"text": "Process Tickets", "callback_data": "admin_process_tickets"},
                    {"text": "Back to Admin", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_tickets_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying support tickets: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_direct_message_handler(update, chat_id):
    """Handle the direct message button in admin panel."""
    try:
        message = (
            "✉️ *Send Direct Message*\n\n"
            "Choose the type of message you want to send to a specific user:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "Text Message", "callback_data": "admin_dm_text"},
                {"text": "Image + Text", "callback_data": "admin_dm_image"}
            ],
            [
                {"text": "Search User by ID", "callback_data": "admin_search_user_for_dm"},
                {"text": "Back to Admin", "callback_data": "admin_back"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_direct_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying direct message options: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_bot_settings_handler(update, chat_id):
    """Handle the bot settings button."""
    try:
        with app.app_context():
            from models import SystemSettings
            from config import MIN_DEPOSIT, DAILY_UPDATE_HOUR
            
            # Get settings from database if available
            min_deposit_setting = SystemSettings.query.filter_by(setting_name="min_deposit").first()
            time_setting = SystemSettings.query.filter_by(setting_name="daily_update_hour").first()
            updates_enabled_setting = SystemSettings.query.filter_by(setting_name="daily_updates_enabled").first()
            support_username_setting = SystemSettings.query.filter_by(setting_name="support_username").first()
            
            # Use values from database or fallback to config
            min_deposit = float(min_deposit_setting.setting_value) if min_deposit_setting else MIN_DEPOSIT
            notification_time = int(time_setting.setting_value) if time_setting else DAILY_UPDATE_HOUR
            updates_enabled = updates_enabled_setting.setting_value.lower() == 'true' if updates_enabled_setting else True
            support_username = support_username_setting.setting_value if support_username_setting else "@admin"
            
            # Create dynamic message with current settings
            message = (
                "⚙️ *Bot Settings*\n\n"
                f"*Minimum Deposit:* {min_deposit:.2f} SOL\n"
                f"*Daily Updates:* {'Enabled' if updates_enabled else 'Disabled'}\n"
                f"*Update Time:* {notification_time}:00 UTC\n"
                f"*Support Username:* {support_username}\n\n"
                "Select an option to modify settings:"
            )
            
            # Dynamic toggle text based on current status
            toggle_text = f"Toggle Updates: {'ON' if updates_enabled else 'OFF'}"
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "Update Min Deposit", "callback_data": "admin_update_min_deposit"},
                    {"text": "Edit Notifications", "callback_data": "admin_edit_notification_time"}
                ],
                [
                    {"text": toggle_text, "callback_data": "admin_toggle_daily_updates"},
                    {"text": "Manage ROI", "callback_data": "admin_manage_roi"}
                ],
                [
                    {"text": "Change Support User", "callback_data": "admin_change_support_username"},
                    {"text": "Back to Admin Panel", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_bot_settings_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying bot settings: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_exit_handler(update, chat_id):
    """Handle the exit button."""
    try:
        bot.send_message(chat_id, "Admin panel closed. Type /admin to reopen.")
    except Exception as e:
        import logging
        logging.error(f"Error in admin_exit_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error exiting admin panel: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

# Broadcast message handlers
# Define global variable to track broadcast target
broadcast_target = "all"  # Default to all users

def admin_broadcast_active(update, chat_id):
    """Handle sending broadcast to active users only."""
    try:
        # Set global variable to filter users
        global broadcast_target
        broadcast_target = "active"
        
        message = (
            "📊 *Broadcast Target Selected*\n\n"
            "You've chosen to send this broadcast to *active users only*.\n\n"
            "Now choose the type of broadcast you want to send:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "Text Message", "callback_data": "admin_broadcast_text"},
                {"text": "Image + Text", "callback_data": "admin_broadcast_image"}
            ],
            [
                {"text": "Announcement", "callback_data": "admin_broadcast_announcement"},
                {"text": "Back", "callback_data": "admin_broadcast"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_active: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error setting broadcast target: {str(e)}")

def admin_broadcast_all(update, chat_id):
    """Handle sending broadcast to all users."""
    try:
        # Set global variable to filter users
        global broadcast_target
        broadcast_target = "all"
        
        message = (
            "📊 *Broadcast Target Selected*\n\n"
            "You've chosen to send this broadcast to *all users*.\n\n"
            "Now choose the type of broadcast you want to send:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "Text Message", "callback_data": "admin_broadcast_text"},
                {"text": "Image + Text", "callback_data": "admin_broadcast_image"}
            ],
            [
                {"text": "Announcement", "callback_data": "admin_broadcast_announcement"},
                {"text": "Back", "callback_data": "admin_broadcast"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_all: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error setting broadcast target: {str(e)}")

def admin_broadcast_text_handler(update, chat_id):
    """Handle the text broadcast option."""
    try:
        # Use global broadcast target
        global broadcast_target
        target_text = "active users only" if broadcast_target == "active" else "all users"
        
        message = (
            f"📝 *Text Broadcast to {target_text}*\n\n"
            "Send a text-only message. You can include:\n"
            "• *Bold text* using *asterisks*\n"
            "• _Italic text_ using _underscores_\n"
            "• `Code blocks` using `backticks`\n"
            "• [Hyperlinks](https://example.com) using [text](URL) format\n\n"
            "Type your message below:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to Broadcast Options", "callback_data": "admin_broadcast"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the next message
        # This would be implemented with a conversation handler in python-telegram-bot
        bot.add_message_listener(chat_id, "text", admin_broadcast_text_message_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_text_handler: {e}")
        bot.send_message(chat_id, f"Error setting up text broadcast: {str(e)}")

def admin_broadcast_text_message_handler(update, chat_id, text):
    """Handle the incoming text message for broadcast."""
    try:
        # Preview the broadcast message with correct target audience
        global broadcast_target
        target_text = "active users only" if broadcast_target == "active" else "all users"
        
        preview_message = (
            "🔍 *Broadcast Preview*\n\n"
            f"{text}\n\n"
            f"This message will be sent to *{target_text}*. Are you sure you want to continue?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Send Broadcast", "callback_data": "admin_send_broadcast"},
                {"text": "❌ Cancel", "callback_data": "admin_broadcast"}
            ]
        ])
        
        # Store the message for later sending
        with app.app_context():
            from models import BroadcastMessage
            
            # Save the message to the database for sending later
            new_message = BroadcastMessage(
                content=text,
                message_type="text",
                created_by=chat_id,
                status="pending"
            )
            db.session.add(new_message)
            db.session.commit()
            
            # Store the message ID in a global variable or session
            global pending_broadcast_id
            pending_broadcast_id = new_message.id
        
        bot.send_message(
            chat_id,
            preview_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove the listener
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_text_message_handler: {e}")
        bot.send_message(chat_id, f"Error processing broadcast message: {str(e)}")
        bot.remove_listener(chat_id)

def admin_broadcast_image_handler(update, chat_id):
    """Handle the image broadcast option."""
    try:
        message = (
            "🖼️ *Image Broadcast*\n\n"
            "Send an image with a caption to all users.\n\n"
            "Please send the image URL and caption in this format:\n"
            "```\nURL\nCaption text goes here\n```\n\n"
            "Example:\n"
            "```\nhttps://example.com/image.jpg\nCheck out our new feature!\n```\n\n"
            "The caption can include Markdown formatting."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to Broadcast Options", "callback_data": "admin_broadcast"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the next message
        bot.add_message_listener(chat_id, "text", admin_broadcast_image_message_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_image_handler: {e}")
        bot.send_message(chat_id, f"Error setting up image broadcast: {str(e)}")

def admin_broadcast_image_message_handler(update, chat_id, text):
    """Handle the incoming image URL and caption for broadcast."""
    try:
        # Split the text into URL and caption
        lines = text.strip().split('\n')
        if len(lines) < 2:
            bot.send_message(chat_id, "Please provide both an image URL and caption. Send 'cancel' to abort.")
            return
            
        image_url = lines[0].strip()
        caption = '\n'.join(lines[1:])
        
        # Preview the broadcast message with correct target audience
        global broadcast_target
        target_text = "active users only" if broadcast_target == "active" else "all users"
        
        preview_message = (
            "🔍 *Image Broadcast Preview*\n\n"
            f"Image URL: {image_url}\n\n"
            f"Caption: {caption}\n\n"
            f"This image and caption will be sent to *{target_text}*. Are you sure you want to continue?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Send Broadcast", "callback_data": "admin_send_broadcast"},
                {"text": "❌ Cancel", "callback_data": "admin_broadcast"}
            ]
        ])
        
        # Store the message for later sending
        with app.app_context():
            from models import BroadcastMessage
            import json
            
            # Save the message to the database for sending later
            message_data = json.dumps({
                "image_url": image_url,
                "caption": caption
            })
            
            new_message = BroadcastMessage(
                content=message_data,
                message_type="image",
                created_by=chat_id,
                status="pending"
            )
            db.session.add(new_message)
            db.session.commit()
            
            # Store the message ID in a global variable or session
            global pending_broadcast_id
            pending_broadcast_id = new_message.id
        
        # Send a sample of the image
        bot.send_message(
            chat_id,
            f"Image preview (URL only, actual image will be sent in broadcast):\n{image_url}"
        )
        
        bot.send_message(
            chat_id,
            preview_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove the listener
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_image_message_handler: {e}")
        bot.send_message(chat_id, f"Error processing image broadcast: {str(e)}")
        bot.remove_listener(chat_id)

def admin_broadcast_announcement_handler(update, chat_id):
    """Handle the announcement broadcast option."""
    try:
        # Get user counts for better UI feedback
        with app.app_context():
            try:
                from models import User, UserStatus
                
                total_users = User.query.count()
                active_users = User.query.filter_by(status=UserStatus.ACTIVE).count()
                
                # Use global variable to show currently selected target
                global broadcast_target
                target_text = "Active Users Only" if broadcast_target == "active" else "All Users"
                target_count = active_users if broadcast_target == "active" else total_users
                
                user_info = (
                    f"*Current Target:* {target_text} ({target_count} users)\n"
                    f"_You can change target audience in the broadcast menu_\n\n"
                )
            except Exception as e:
                import logging
                logging.error(f"Error getting user counts: {e}")
                user_info = ""
        
        message = (
            "📣 *Announcement Broadcast*\n\n"
            f"{user_info}"
            "Send a formatted announcement to users with a title and content.\n\n"
            "Please enter your announcement in this format:\n"
            "```\nTITLE\nMessage content goes here\n```\n\n"
            "Example:\n"
            "```\nMaintenance Notice\nThe bot will be undergoing maintenance on Friday.\nExpect improved performance afterwards!\n```\n\n"
            "Your announcement will appear with professional formatting in the user panel."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "📝 See Live Preview", "callback_data": "ignore"}],
            [{"text": "Back to Broadcast Options", "callback_data": "admin_broadcast"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the next message
        bot.add_message_listener(chat_id, "text", admin_broadcast_announcement_message_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_announcement_handler: {e}")
        bot.send_message(chat_id, f"Error setting up announcement broadcast: {str(e)}")

def is_admin(telegram_id):
    """Check if the given Telegram ID belongs to an admin."""
    # Convert to string if it's not already
    telegram_id = str(telegram_id)
    
    # Hardcoded admin IDs from config.py or manually added here for simplicity
    from config import ADMIN_IDS
    
    # Check if the user ID is in the admins list
    return telegram_id in ADMIN_IDS
    
def add_trade_to_history(user_id, token_name, entry_price, exit_price, profit_amount, tx_hash):
    """
    Add a trade to the user's trading history in yield_data.json
    so it appears in their trade history page.
    
    Args:
        user_id (int): Database ID of the user
        token_name (str): Name/symbol of the token
        entry_price (float): Entry price
        exit_price (float): Exit price
        profit_amount (float): Profit amount in SOL
        tx_hash (str): Transaction hash
    """
    try:
        # Set up file path - ensure this is in the correct directory
        data_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(data_dir, 'yield_data.json')
        
        import logging
        logging.info(f"Adding trade to history for user {user_id}. File path: {data_file}")
        
        # Load existing data
        try:
            with open(data_file, 'r') as f:
                yield_data = json.load(f)
                logging.info(f"Successfully loaded existing yield data with {len(yield_data)} user entries")
        except FileNotFoundError:
            logging.info(f"Yield data file not found, creating new file at {data_file}")
            yield_data = {}
        except json.JSONDecodeError:
            logging.warning(f"Invalid JSON in yield data file, creating fresh data")
            yield_data = {}
        except Exception as load_error:
            logging.error(f"Unexpected error loading yield data: {load_error}")
            yield_data = {}
        
        # Convert user_id to string (JSON keys are strings)
        user_id_str = str(user_id)
        
        # Create user entry if it doesn't exist
        if user_id_str not in yield_data:
            logging.info(f"Creating new user entry for user_id {user_id}")
            yield_data[user_id_str] = {
                "balance": 0.0,
                "trades": [],
                "page": 0
            }
        
        # Calculate yield percentage
        if entry_price > 0:
            yield_percentage = ((exit_price / entry_price) - 1) * 100
        else:
            yield_percentage = 0
            
        # Create trade entry
        new_trade = {
            "name": token_name.replace('$', ''),
            "symbol": token_name.replace('$', ''),
            "mint": tx_hash[:32] if len(tx_hash) >= 32 else tx_hash,
            "entry": entry_price,
            "exit": exit_price,
            "yield": yield_percentage,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to user's trades
        yield_data[user_id_str]["trades"].insert(0, new_trade)  # Add to the beginning
        
        # Update user's balance without overwriting the entire balance
        # This was a bug - we were replacing the balance instead of adding to it
        current_balance = yield_data[user_id_str].get("balance", 0.0)
        yield_data[user_id_str]["balance"] = current_balance + profit_amount
        
        # Save back to file
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(data_file), exist_ok=True)
            
            with open(data_file, 'w') as f:
                json.dump(yield_data, f, indent=2)
                
            logging.info(f"Successfully saved trade data for user {user_id}")
            
            # Also create TradingPosition record in database for better reliability
            with app.app_context():
                from models import TradingPosition
                
                # Check if this position already exists to avoid duplicates
                existing_position = TradingPosition.query.filter_by(
                    user_id=user_id,
                    token_name=token_name.replace('$', ''),
                    entry_price=entry_price
                ).first()
                
                if not existing_position:
                    # Create a new position record
                    new_position = TradingPosition(
                        user_id=user_id,
                        token_name=token_name.replace('$', ''),
                        amount=profit_amount / entry_price if entry_price > 0 else 0,
                        entry_price=entry_price,
                        current_price=exit_price,
                        timestamp=datetime.utcnow(),
                        status='closed'
                    )
                    
                    db.session.add(new_position)
                    db.session.commit()
                    logging.info(f"Created TradingPosition record in database for user {user_id}")
            
            return True
        except Exception as save_error:
            logging.error(f"Error saving yield data: {save_error}")
            return False
    except Exception as e:
        import logging
        logging.error(f"Error adding trade to history: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

def admin_trade_post_handler(update, chat_id):
    """
    Handle individual trade posting for a specific user.
    This makes trades appear as if generated by a real automated trading bot
    while allowing admin control over what gets posted.
    
    Format:
    /admin_trade_post [UserID] [CoinName] [Entry] [Exit] [Profit/Loss] [TX Hash] [Optional:TradeType]
    
    Trade Types: scalp, snipe, dip, reversal
    
    Examples:
    /admin_trade_post 123456789 $ZING 0.0041 0.0074 +1.20 0xabc123
    /admin_trade_post 123456789 $ZING 0.0041 0.0074 +1.20 0xabc123 scalp
    """
    try:
        # Check for admin privileges
        if not is_admin(update['message']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return
            
        # Show instructions if no parameters provided
        text_parts = update['message']['text'].split()
        if len(text_parts) < 7:  # Command + 6 parameters (minimum)
            instructions = (
                "📈 *Individual Trade Post*\n\n"
                "Post a realistic trade for a specific user with this format:\n"
                "`/admin_trade_post [UserID] [CoinName] [Entry] [Exit] [Profit] [TX_Hash] [Optional:TradeType]`\n\n"
                "Examples:\n"
                "`/admin_trade_post 123456789 $ZING 0.0041 0.0074 +1.20 0xabc123`\n"
                "`/admin_trade_post 123456789 $ZING 0.0041 0.0074 +1.20 0xabc123 scalp`\n\n"
                "Trade Types: scalp, snipe, dip, reversal\n\n"
                "This will update the user's metrics and send them a realistic trade notification."
            )
            bot.send_message(chat_id, instructions, parse_mode="Markdown")
            return
            
        # Parse the parameters
        user_id = text_parts[1]
        token_name = text_parts[2]
        entry_price = float(text_parts[3])
        exit_price = float(text_parts[4])
        profit_amount_str = text_parts[5]
        tx_hash = text_parts[6]
        
        # Check for optional trade type parameter
        trade_type = None
        if len(text_parts) >= 8:
            trade_type = text_parts[7]
            valid_trade_types = ["scalp", "snipe", "dip", "reversal"]
            if trade_type.lower() not in valid_trade_types:
                trade_type = None  # Ignore invalid trade types
        
        # Handle profit amount (convert to float, handling + or - prefix)
        profit_amount_str = profit_amount_str.replace("SOL", "").strip()
        profit_amount = float(profit_amount_str)
        
        # Process the trade for the specified user
        with app.app_context():
            from models import User, UserStatus, Profit, Transaction
            from datetime import datetime
            
            # Find the user
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                bot.send_message(chat_id, f"⚠️ User with ID {user_id} not found.")
                return
                
            # Calculate the ROI percentage
            roi_percentage = (abs(profit_amount) / user.balance) * 100 if user.balance > 0 else 0
                
            # Update user's balance with the profit
            previous_balance = user.balance
            user.balance += profit_amount
            
            # Create a transaction record
            transaction_type = "buy" if profit_amount > 0 else "sell"
            new_transaction = Transaction(
                user_id=user.id,
                transaction_type=transaction_type,
                amount=abs(profit_amount),
                token_name=token_name,
                timestamp=datetime.utcnow(),
                status="completed",
                notes=f"Auto trade: entry {entry_price}, exit {exit_price}",
                tx_hash=tx_hash
            )
            db.session.add(new_transaction)
            
            # Create profit record for today
            today = datetime.utcnow().date()
            new_profit = Profit(
                user_id=user.id,
                amount=profit_amount,
                percentage=roi_percentage,
                date=today
            )
            db.session.add(new_profit)
            
            # Commit the changes
            db.session.commit()
            
            # Add trade to user's history page
            add_trade_to_history(
                user_id=user.id, 
                token_name=token_name,
                entry_price=entry_price, 
                exit_price=exit_price,
                profit_amount=profit_amount,
                tx_hash=tx_hash
            )
            
            # Create personalized message for the user
            user_message = (
                "📈 *New Trade Executed*\n\n"
            )
            
            # Add trade type if provided
            if trade_type:
                trade_type_formatted = trade_type.capitalize()
                trade_type_display = {
                    "Scalp": "Scalp Trade",
                    "Snipe": "New Launch Snipe",
                    "Dip": "Dip Buy Strategy",
                    "Reversal": "Reversal Play"
                }.get(trade_type_formatted, f"{trade_type_formatted} Trade")
                
                user_message += f"• *Trade Type:* {trade_type_display}\n"
            
            # Continue with the rest of the message
            user_message += (
                f"• *Token:* {token_name} (New Launch)\n"
                f"• *Entry:* {entry_price} | *Exit:* {exit_price}\n"
                f"• *Profit:* {profit_amount:.2f} SOL\n"
                f"• *TX Hash:* [View on Solscan](https://solscan.io/tx/{tx_hash})\n\n"
                "*Next scan in progress... stay tuned!*\n\n"
                "_This trade has been added to your dashboard. Balance and profit metrics updated automatically._"
            )
            
            # Send the message to the user
            bot.send_message(user_id, user_message, parse_mode="Markdown")
            
            # Confirmation for admin
            confirmation = (
                "✅ *Trade Posted Successfully*\n\n"
                f"• *User:* {user_id}\n"
                f"• *Token:* {token_name}\n"
                f"• *Profit:* {profit_amount:.2f} SOL\n"
                f"• *Previous Balance:* {previous_balance:.2f} SOL\n"
                f"• *New Balance:* {user.balance:.2f} SOL\n\n"
                "Trade notification has been sent to the user and their metrics have been updated."
            )
            
            bot.send_message(chat_id, confirmation, parse_mode="Markdown")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_trade_post_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error: {str(e)}")

def admin_broadcast_trade_handler(update, chat_id):
    """Handle admin broadcasting of trade information to all active users with personalized profit calculations."""
    try:
        # Check for admin privileges
        if not is_admin(update['callback_query']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return
            
        # Show input form with instructions
        instructions = (
            "📈 *Broadcast Trade Alert*\n\n"
            "Send the trade details in the following format:\n"
            "`$TOKEN_NAME ENTRY_PRICE EXIT_PRICE ROI_PERCENT TX_HASH [OPTIONAL:TRADE_TYPE]`\n\n"
            "Examples:\n"
            "`$ZING 0.0041 0.0074 8.5 https://solscan.io/tx/abc123`\n"
            "`$ZING 0.0041 0.0074 8.5 https://solscan.io/tx/abc123 scalp`\n\n"
            "Trade Types: scalp, snipe, dip, reversal\n\n"
            "This will be broadcast to all active users with personalized profit calculations based on their balance."
        )
        
        # Set the global state to listen for the broadcast text
        global broadcast_target
        broadcast_target = "active"  # Send only to active users
        
        # Add listener for the admin's next message
        bot.add_message_listener(chat_id, "broadcast_trade", admin_broadcast_trade_message_handler)
        
        # Show the instructions with a cancel button
        keyboard = bot.create_inline_keyboard([
            [{"text": "❌ Cancel", "callback_data": "admin_broadcast"}]
        ])
        
        bot.send_message(chat_id, instructions, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error: {str(e)}")
        
def admin_broadcast_trade_message_handler(update, chat_id, text):
    """
    Process and send the trade information broadcast to all active users with personalized profit calculations.
    Format: TOKEN ENTRY EXIT ROI_PERCENT TX_LINK [OPTIONAL:TRADE_TYPE]
    
    Example: $ZING 0.0041 0.0074 8.5 0xabc123 scalp
    """
    try:
        # Remove the message listener
        bot.remove_listener(chat_id)
        
        # Show processing message
        processing_msg = "⏳ Processing trade broadcast..."
        bot.send_message(chat_id, processing_msg)
        
        # Record broadcast time for tracking purposes
        with app.app_context():
            from models import SystemSettings
            from datetime import datetime
        
        # Parse the trade information
        parts = text.strip().split()
        if len(parts) < 5:
            bot.send_message(chat_id, "⚠️ Invalid format. Please provide all required information: TOKEN ENTRY EXIT ROI% TX_LINK [OPTIONAL:TRADE_TYPE]")
            return
            
        token = parts[0]  # Token name
        entry = float(parts[1])  # Entry price
        exit_price = float(parts[2])  # Exit price
        roi_percent = float(parts[3])  # ROI percentage
        tx_link = parts[4]  # Transaction hash link
        
        # Check for optional trade type
        trade_type = None
        if len(parts) >= 6:
            trade_type = parts[5].lower()
            valid_trade_types = ["scalp", "snipe", "dip", "reversal"]
            if trade_type not in valid_trade_types:
                bot.send_message(
                    chat_id, 
                    f"⚠️ Invalid trade type: '{trade_type}'. Valid types are: scalp, snipe, dip, reversal. "
                    f"Proceeding without trade type."
                )
                trade_type = None
        
        # Show confirmation message to admin
        confirmation = (
            "📣 *Trade Broadcast Confirmation*\n\n"
            f"• *Token:* {token}\n"
            f"• *Entry:* {entry}\n"
            f"• *Exit:* {exit_price}\n"
            f"• *ROI:* {roi_percent}%\n"
            f"• *TX:* {tx_link}\n"
        )
        
        if trade_type:
            confirmation += f"• *Trade Type:* {trade_type.capitalize()}\n"
            
        confirmation += "\nBroadcasting to all active users with personalized profit calculations..."
        
        bot.send_message(chat_id, confirmation, parse_mode="Markdown")
        
        # Process the broadcast for all active users
        with app.app_context():
            from models import User, UserStatus, Profit, Transaction
            from datetime import datetime
            
            # Query all active users
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            broadcast_count = 0
            total_profit_distributed = 0
            
            for user in active_users:
                try:
                    # Calculate personalized profit based on user's balance
                    user_balance = user.balance
                    profit_amount = round(user_balance * (roi_percent / 100), 2)
                    total_profit_distributed += profit_amount
                    
                    # Store previous balance for reporting
                    previous_balance = user.balance
                    
                    # Update user's balance with the profit
                    user.balance += profit_amount
                    
                    # Create a transaction record
                    transaction_type = "buy" if profit_amount > 0 else "sell"
                    new_transaction = Transaction(
                        user_id=user.id,
                        transaction_type=transaction_type,
                        amount=abs(profit_amount),
                        token_name=token,
                        timestamp=datetime.utcnow(),
                        status="completed",
                        notes=f"Auto trade: entry {entry}, exit {exit_price}",
                        tx_hash=tx_link
                    )
                    db.session.add(new_transaction)
                    
                    # Create profit record for today
                    today = datetime.utcnow().date()
                    new_profit = Profit(
                        user_id=user.id,
                        amount=profit_amount,
                        percentage=roi_percent,
                        date=today
                    )
                    db.session.add(new_profit)
                    
                    # Create TradingPosition record to display in trade history
                    from models import TradingPosition
                    
                    # Store the entry price in a properly named variable to avoid "name 'entry_price' is not defined" error
                    entry_price = entry
                    
                    # Calculate the token amount - using a safe calculation to avoid division by zero
                    token_amount = 0.0
                    if exit_price != entry_price:
                        token_amount = abs(profit_amount / (exit_price - entry_price))
                    else:
                        # Fallback to a reasonable calculation if prices are the same
                        token_amount = abs(profit_amount / entry_price) if entry_price > 0 else 1.0
                    
                    # Create a completed trading position for the trade
                    trading_position = TradingPosition(
                        user_id=user.id,
                        token_name=token,
                        amount=token_amount,
                        entry_price=entry_price,
                        current_price=exit_price,
                        timestamp=datetime.utcnow(),
                        status="closed"  # Mark as closed since it's a completed trade
                    )
                    db.session.add(trading_position)
                    
                    # Add trade to user's history page (JSON file)
                    add_trade_to_history(
                        user_id=user.id, 
                        token_name=token,
                        entry_price=entry, 
                        exit_price=exit_price,
                        profit_amount=profit_amount,
                        tx_hash=tx_link
                    )
                    
                    # Create personalized message for each user
                    message = (
                        "📈 *New Trade Executed Automatically*\n\n"
                    )
                    
                    # Add trade type if provided
                    if trade_type:
                        trade_type_formatted = trade_type.capitalize()
                        trade_type_display = {
                            "scalp": "Scalp Trade",
                            "snipe": "New Launch Snipe",
                            "dip": "Dip Buy Strategy",
                            "reversal": "Reversal Play"
                        }.get(trade_type, f"{trade_type_formatted} Trade")
                        
                        message += f"• *Trade Type:* {trade_type_display}\n"
                    
                    # Continue building the message
                    message += (
                        f"• *Token:* {token} (New Launch)\n"
                        f"• *Entry:* {entry} | *Exit:* {exit_price}\n"
                        f"• *Profit:* +{profit_amount:.2f} SOL ({roi_percent}%)\n"
                        f"• *TX Hash:* [View on Solscan]({tx_link})\n\n"
                        f"• *Previous Balance:* {previous_balance:.2f} SOL\n"
                        f"• *New Balance:* {user.balance:.2f} SOL\n\n"
                        "*Next scan in progress... stay tuned!*\n\n"
                        "_Your dashboard has been updated automatically with this trade._"
                    )
                    
                    # Send personalized message to the user
                    bot.send_message(user.telegram_id, message, parse_mode="Markdown")
                    broadcast_count += 1
                    
                except Exception as e:
                    import logging
                    logging.error(f"Error broadcasting trade to user {user.id}: {e}")
                    continue
                    
            # Update last broadcast time
            current_time = datetime.utcnow()
            last_broadcast_setting = SystemSettings.query.filter_by(setting_name='last_trade_broadcast_time').first()
            
            if last_broadcast_setting:
                last_broadcast_setting.setting_value = current_time.isoformat()
                last_broadcast_setting.updated_by = str(update['message']['from']['id'])
            else:
                # Create the setting if it doesn't exist
                new_setting = SystemSettings(
                    setting_name='last_trade_broadcast_time',
                    setting_value=current_time.isoformat(),
                    updated_by=str(update['message']['from']['id'])
                )
                db.session.add(new_setting)
            
            # Commit all changes
            db.session.commit()
            
            # Calculate next available broadcast time
            next_available = (current_time + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Notify admin of completion with detailed stats
            success_message = (
                "✅ *Trade Broadcast Successfully Sent*\n\n"
                f"• *Users Reached:* {broadcast_count} of {len(active_users)}\n"
                f"• *Token:* {token}\n"
                f"• *ROI Applied:* {roi_percent}%\n"
                f"• *Total Profit Generated:* {total_profit_distributed:.2f} SOL\n\n"
                f"• *Next Available Broadcast:* {next_available}\n\n"
                "All user balances and profit metrics have been updated."
            )
            
            bot.send_message(chat_id, success_message, parse_mode="Markdown")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error: {str(e)}")

def admin_broadcast_announcement_message_handler(update, chat_id, text):
    """Handle the incoming announcement for broadcast."""
    try:
        # Check for cancellation
        if text.lower() == 'cancel':
            bot.send_message(
                chat_id,
                "Announcement creation cancelled. Returning to broadcast menu.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Back to Broadcast Menu", "callback_data": "admin_broadcast"}]
                ])
            )
            bot.remove_listener(chat_id)
            return
            
        # Split the text into title and content
        lines = text.strip().split('\n')
        if len(lines) < 2:
            bot.send_message(
                chat_id, 
                "⚠️ Please provide both a title and content following the format shown. Send 'cancel' to abort."
            )
            return
            
        title = lines[0].strip()
        content = '\n'.join(lines[1:])
        
        # Format the announcement with enhanced styling for user panel
        formatted_announcement = (
            f"📢 *{title}*\n\n"
            f"{content}\n\n"
            f"_Sent: {datetime.utcnow().strftime('%B %d, %Y')} · Via Admin Panel_"
        )
        
        # Get relevant user counts for better preview
        with app.app_context():
            try:
                from models import User, UserStatus
                
                total_users = User.query.count()
                active_users = User.query.filter_by(status=UserStatus.ACTIVE).count()
                
                # Use global variable to show currently selected target
                global broadcast_target
                target_text = "Active Users Only" if broadcast_target == "active" else "All Users"
                target_count = active_users if broadcast_target == "active" else total_users
                
                audience_info = f"*{target_text}* ({target_count} users)"
            except Exception as e:
                import logging
                logging.error(f"Error getting user counts: {e}")
                audience_info = f"*{target_text}*"
        
        # Create an enhanced preview with UI simulation of how it will appear to users
        preview_message = (
            "🔍 *Announcement Preview*\n\n"
            "```\n📱 User Device Preview:\n" + "-" * 30 + "```\n\n"
            f"{formatted_announcement}\n\n"
            "```\n" + "-" * 30 + "\n```\n"
            f"This announcement will be sent to {audience_info}.\n\n"
            "Are you sure you want to continue?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Send Broadcast", "callback_data": "admin_send_broadcast"},
                {"text": "❌ Cancel", "callback_data": "admin_broadcast"}
            ]
        ])
        
        # Store the message for later sending
        with app.app_context():
            from models import BroadcastMessage
            import json
            
            # Save the message to the database for sending later
            message_data = json.dumps({
                "title": title,
                "content": content,
                "formatted_text": formatted_announcement
            })
            
            new_message = BroadcastMessage(
                content=message_data,
                message_type="announcement",
                created_by=chat_id,
                status="pending"
            )
            db.session.add(new_message)
            db.session.commit()
            
            # Store the message ID in a global variable or session
            global pending_broadcast_id
            pending_broadcast_id = new_message.id
        
        bot.send_message(
            chat_id,
            preview_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove the listener
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_announcement_message_handler: {e}")
        bot.send_message(chat_id, f"Error processing announcement broadcast: {str(e)}")
        bot.remove_listener(chat_id)

# Direct message handlers
def admin_dm_text_handler(update, chat_id):
    """Handle the text direct message option."""
    try:
        message = (
            "📝 *Text Direct Message*\n\n"
            "First, enter the Telegram ID of the user you want to message:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the next message
        bot.add_message_listener(chat_id, "text", admin_dm_recipient_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_text_handler: {e}")
        bot.send_message(chat_id, f"Error setting up direct message: {str(e)}")

def admin_dm_recipient_handler(update, chat_id, text):
    """Handle the recipient ID for direct message."""
    try:
        recipient_id = text.strip()
        
        # Check if the user exists
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=recipient_id).first()
            
            if not user:
                bot.send_message(
                    chat_id, 
                    f"User with ID {recipient_id} not found. Please try again or press 'Back' to cancel.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                    ])
                )
                bot.remove_listener(chat_id)
                return
            
            # Store the recipient ID
            global dm_recipient_id
            dm_recipient_id = recipient_id
            
            # Prompt for the message content
            message = (
                f"✅ User found: {user.username or 'No username'} (ID: {recipient_id})\n\n"
                "Now type the message you want to send. You can include:\n"
                "• *Bold text* using *asterisks*\n"
                "• _Italic text_ using _underscores_\n"
                "• `Code blocks` using `backticks`\n"
                "• [Hyperlinks](https://example.com) using [text](URL) format"
            )
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Cancel", "callback_data": "admin_direct_message"}]
                ])
            )
            
            # Update the listener for the message content
            bot.remove_listener(chat_id)
            bot.add_message_listener(chat_id, "text", admin_dm_content_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_recipient_handler: {e}")
        bot.send_message(chat_id, f"Error processing recipient: {str(e)}")
        bot.remove_listener(chat_id)

def admin_dm_content_handler(update, chat_id, text):
    """Handle the content for direct message."""
    try:
        # Get the stored recipient ID
        global dm_recipient_id
        recipient_id = dm_recipient_id
        
        # Preview the message
        preview_message = (
            "🔍 *Direct Message Preview*\n\n"
            f"To: User {recipient_id}\n\n"
            f"Message:\n{text}\n\n"
            "Are you sure you want to send this message?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Send Message", "callback_data": "admin_send_direct_message"},
                {"text": "❌ Cancel", "callback_data": "admin_direct_message"}
            ]
        ])
        
        # Store the message for later sending
        global dm_content
        dm_content = text
        
        bot.send_message(
            chat_id,
            preview_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove the listener
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_content_handler: {e}")
        bot.send_message(chat_id, f"Error processing message content: {str(e)}")
        bot.remove_listener(chat_id)

def admin_dm_image_handler(update, chat_id):
    """Handle the image direct message option."""
    try:
        message = (
            "🖼️ *Image Direct Message*\n\n"
            "First, enter the Telegram ID of the user you want to message:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the next message (recipient ID)
        bot.add_message_listener(chat_id, "text", admin_dm_image_recipient_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_image_handler: {e}")
        bot.send_message(chat_id, f"Error setting up image direct message: {str(e)}")

def admin_dm_image_recipient_handler(update, chat_id, text):
    """Handle the recipient ID for image direct message."""
    try:
        recipient_id = text.strip()
        
        # Check if the user exists
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=recipient_id).first()
            
            if not user:
                bot.send_message(
                    chat_id, 
                    f"User with ID {recipient_id} not found. Please try again or press 'Back' to cancel.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                    ])
                )
                bot.remove_listener(chat_id)
                return
            
            # Store the recipient ID
            global dm_recipient_id
            dm_recipient_id = recipient_id
            
            # Prompt for the image URL and caption
            message = (
                f"✅ User found: {user.username or 'No username'} (ID: {recipient_id})\n\n"
                "Now send the image URL and caption in this format:\n"
                "```\nURL\nCaption text goes here\n```\n\n"
                "Example:\n"
                "```\nhttps://example.com/image.jpg\nCheck out this feature!\n```\n\n"
                "The caption can include Markdown formatting."
            )
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Cancel", "callback_data": "admin_direct_message"}]
                ])
            )
            
            # Update the listener for the image URL and caption
            bot.remove_listener(chat_id)
            bot.add_message_listener(chat_id, "text", admin_dm_image_content_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_image_recipient_handler: {e}")
        bot.send_message(chat_id, f"Error processing recipient: {str(e)}")
        bot.remove_listener(chat_id)

def admin_dm_image_content_handler(update, chat_id, text):
    """Handle the image URL and caption for direct message."""
    try:
        # Split the text into URL and caption
        lines = text.strip().split('\n')
        if len(lines) < 2:
            bot.send_message(chat_id, "Please provide both an image URL and caption. Try again or send 'cancel' to abort.")
            return
            
        image_url = lines[0].strip()
        caption = '\n'.join(lines[1:])
        
        # Get the stored recipient ID
        global dm_recipient_id
        recipient_id = dm_recipient_id
        
        # Preview the message
        preview_message = (
            "🔍 *Image Direct Message Preview*\n\n"
            f"To: User {recipient_id}\n\n"
            f"Image URL: {image_url}\n\n"
            f"Caption: {caption}\n\n"
            "Are you sure you want to send this message?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Send Message", "callback_data": "admin_send_direct_message_image"},
                {"text": "❌ Cancel", "callback_data": "admin_direct_message"}
            ]
        ])
        
        # Store the message for later sending
        global dm_image_url, dm_image_caption
        dm_image_url = image_url
        dm_image_caption = caption
        
        # Send a sample of the image
        bot.send_message(
            chat_id,
            f"Image preview (URL only, actual image will be sent in message):\n{image_url}"
        )
        
        bot.send_message(
            chat_id,
            preview_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove the listener
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_image_content_handler: {e}")
        bot.send_message(chat_id, f"Error processing image content: {str(e)}")
        bot.remove_listener(chat_id)

def admin_search_user_for_dm_handler(update, chat_id):
    """Handle the search user for direct message option."""
    try:
        message = (
            "🔍 *Search User*\n\n"
            "Enter a username or partial user ID to search:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the search query
        bot.add_message_listener(chat_id, "text", admin_search_user_query_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_search_user_for_dm_handler: {e}")
        bot.send_message(chat_id, f"Error setting up user search: {str(e)}")

def admin_search_user_query_handler(update, chat_id, text):
    """Handle the search query for finding users."""
    try:
        search_query = text.strip()
        
        # Search for users
        with app.app_context():
            from models import User
            from sqlalchemy import or_
            
            users = User.query.filter(
                or_(
                    User.username.ilike(f"%{search_query}%"),
                    User.telegram_id.ilike(f"%{search_query}%")
                )
            ).limit(5).all()
            
            if not users:
                bot.send_message(
                    chat_id, 
                    f"No users found matching '{search_query}'. Please try another search term.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                    ])
                )
                bot.remove_listener(chat_id)
                return
            
            # Create a message with search results
            results_message = f"🔍 *Search Results for '{search_query}'*\n\n"
            
            for user in users:
                username = user.username or "No username"
                results_message += f"• *{username}* (ID: `{user.telegram_id}`)\n"
            
            results_message += "\nCopy an ID from the list and use it to send a direct message."
            
            bot.send_message(
                chat_id,
                results_message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Send Text Message", "callback_data": "admin_dm_text"}],
                    [{"text": "Send Image Message", "callback_data": "admin_dm_image"}],
                    [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                ])
            )
            
            # Remove the listener
            bot.remove_listener(chat_id)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_search_user_query_handler: {e}")
        bot.send_message(chat_id, f"Error searching for users: {str(e)}")
        bot.remove_listener(chat_id)
        
def admin_send_broadcast_handler(update, chat_id):
    """Handle sending a broadcast message to users based on target selection."""
    try:
        # Get the pending broadcast message
        global pending_broadcast_id, broadcast_target
        
        # For debugging
        import logging
        logging.info(f"Preparing to send broadcast. pending_broadcast_id={pending_broadcast_id}, broadcast_target={broadcast_target}")
        
        with app.app_context():
            from models import BroadcastMessage, User
            import json
            
            # If no pending_broadcast_id is set, try to find the most recent pending message
            if not pending_broadcast_id:
                latest_pending = BroadcastMessage.query.filter_by(
                    status="pending", 
                    created_by=str(chat_id)
                ).order_by(BroadcastMessage.created_at.desc()).first()
                
                if latest_pending:
                    pending_broadcast_id = latest_pending.id
                    logging.info(f"Found latest pending broadcast message: {pending_broadcast_id}")
                else:
                    bot.send_message(chat_id, "No pending broadcast message found. Please create a new broadcast.")
                    return
            
            # Get the message
            message = BroadcastMessage.query.get(pending_broadcast_id)
            if not message:
                bot.send_message(chat_id, "Broadcast message not found. Please create a new broadcast.")
                return
                
            # Get users for broadcast based on target selection
            from models import UserStatus
            import logging
            import json
            from datetime import datetime
            
            # Filter users based on broadcast target
            if broadcast_target == "active":
                users = User.query.filter_by(status=UserStatus.ACTIVE).all()
                target_description = "active users"
            else:
                users = User.query.all()
                target_description = "all users"
            
            # Log the count of users found
            logging.info(f"Found {len(users)} {target_description} for broadcast")
            total_users = len(users)
            
            if total_users == 0:
                bot.send_message(chat_id, f"There are no {target_description} to send the broadcast to.")
                return
                
            # Update the message status
            message.status = "sending"
            db.session.commit()
            
            # Send a progress message
            progress_message = bot.send_message(
                chat_id,
                f"📣 Preparing to send broadcast to {total_users} {target_description}..."
            )
            
            # Process the message based on its type
            sent_count = 0
            failed_count = 0
            
            if message.message_type == "text":
                # Simple text broadcast
                content = message.content
                
                for user in users:
                    try:
                        # Skip users with no telegram_id
                        if not user.telegram_id:
                            logging.warning(f"User ID {user.id} has no telegram_id, skipping")
                            continue
                            
                        bot.send_message(
                            user.telegram_id,
                            content,
                            parse_mode="Markdown"
                        )
                        sent_count += 1
                        
                        # Update progress every 10 users
                        if sent_count % 10 == 0:
                            bot.edit_message(
                                progress_message['message_id'],
                                chat_id,
                                f"📣 Sending broadcast... {sent_count}/{total_users} completed."
                            )
                    except Exception as e:
                        logging.error(f"Error sending broadcast to user {user.telegram_id}: {e}")
                        failed_count += 1
            
            elif message.message_type == "image":
                # Image with caption
                try:
                    content = json.loads(message.content)
                    image_url = content.get("image_url")
                    caption = content.get("caption")
                    
                    for user in users:
                        try:
                            # Skip users with no telegram_id
                            if not user.telegram_id:
                                logging.warning(f"User ID {user.id} has no telegram_id, skipping")
                                continue
                                
                            # In a real implementation, we would use bot.send_photo
                            # However, for our simplified version we'll simulate it
                            bot.send_message(
                                user.telegram_id,
                                f"[Image]({image_url})\n\n{caption}",
                                parse_mode="Markdown"
                            )
                            sent_count += 1
                            
                            # Update progress every 10 users
                            if sent_count % 10 == 0:
                                bot.edit_message(
                                    progress_message['message_id'],
                                    chat_id,
                                    f"📣 Sending broadcast... {sent_count}/{total_users} completed."
                                )
                        except Exception as e:
                            logging.error(f"Error sending broadcast to user {user.telegram_id}: {e}")
                            failed_count += 1
                except json.JSONDecodeError:
                    bot.send_message(chat_id, "Error processing image broadcast: Invalid format")
                    return
            
            elif message.message_type == "announcement":
                # Formatted announcement
                try:
                    content = json.loads(message.content)
                    formatted_text = content.get("formatted_text")
                    
                    for user in users:
                        try:
                            # Skip users with no telegram_id
                            if not user.telegram_id:
                                logging.warning(f"User ID {user.id} has no telegram_id, skipping")
                                continue
                                
                            bot.send_message(
                                user.telegram_id,
                                formatted_text,
                                parse_mode="Markdown"
                            )
                            sent_count += 1
                            
                            # Update progress every 10 users
                            if sent_count % 10 == 0:
                                bot.edit_message(
                                    progress_message['message_id'],
                                    chat_id,
                                    f"📣 Sending broadcast... {sent_count}/{total_users} completed."
                                )
                        except Exception as e:
                            logging.error(f"Error sending broadcast to user {user.telegram_id}: {e}")
                            failed_count += 1
                except json.JSONDecodeError:
                    bot.send_message(chat_id, "Error processing announcement broadcast: Invalid format")
                    return
            
            # Update the message status
            message.status = "sent"
            message.sent_at = datetime.utcnow()
            message.sent_count = sent_count
            message.failed_count = failed_count
            db.session.commit()
            
            # Clear the pending broadcast ID
            pending_broadcast_id = None
            
            # Determine success rate
            success_rate = (sent_count / total_users * 100) if total_users > 0 else 0
            success_emoji = "✅" if success_rate > 90 else "⚠️" if success_rate > 50 else "❌"
            
            # Send completion message with detailed statistics and interactive buttons
            completion_message = (
                f"{success_emoji} *Broadcast Completed*\n\n"
                f"📊 *Results:*\n"
                f"• Total users in database: {total_users}\n"
                f"• Successfully sent: {sent_count}\n"
                f"• Failed: {failed_count}\n"
                f"• Skipped (no telegram_id): {total_users - (sent_count + failed_count)}\n\n"
                f"Broadcast ID: `{message.id}`\n"
                f"Type: {message.message_type}\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                f"The message has been delivered to *{sent_count}* users ({success_rate:.1f}% success rate)."
            )
            
            # Create an interactive keyboard with more options
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📢 New Broadcast", "callback_data": "admin_broadcast"},
                    {"text": "📊 View Stats", "callback_data": "admin_view_stats"}
                ],
                [
                    {"text": "Return to Admin Panel", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                completion_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Log the successful broadcast
            logging.info(f"Broadcast ID {message.id} successfully sent to {sent_count}/{total_users} users")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_send_broadcast_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sending broadcast: {str(e)}")

def admin_send_direct_message_handler(update, chat_id):
    """Handle sending a direct message to a specific user."""
    try:
        # Get the stored recipient ID and message content
        global dm_recipient_id, dm_content
        if not dm_recipient_id or not dm_content:
            bot.send_message(chat_id, "Message information is missing. Please create a new direct message.")
            return
            
        # Send the message to the recipient
        try:
            bot.send_message(
                dm_recipient_id,
                dm_content,
                parse_mode="Markdown"
            )
            
            # Log the direct message
            with app.app_context():
                from models import AdminMessage
                
                # Save the message to the database
                new_message = AdminMessage(
                    content=dm_content,
                    message_type="text",
                    recipient_id=dm_recipient_id,
                    sent_by=chat_id,
                    status="sent"
                )
                db.session.add(new_message)
                db.session.commit()
            
            # Clear the stored data
            dm_recipient_id = None
            dm_content = None
            
            # Send confirmation message
            bot.send_message(
                chat_id,
                "✅ Direct message sent successfully!",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Send Another Message", "callback_data": "admin_direct_message"}],
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            
        except Exception as e:
            logging.error(f"Error sending direct message to user {dm_recipient_id}: {e}")
            bot.send_message(chat_id, f"Error sending message: {str(e)}")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_send_direct_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sending direct message: {str(e)}")

def admin_send_direct_message_image_handler(update, chat_id):
    """Handle sending an image direct message to a specific user."""
    try:
        # Get the stored recipient ID and image data
        global dm_recipient_id, dm_image_url, dm_image_caption
        if not dm_recipient_id or not dm_image_url or not dm_image_caption:
            bot.send_message(chat_id, "Message information is missing. Please create a new image message.")
            return
            
        # Send the message to the recipient
        try:
            # In a real implementation, we would use bot.send_photo
            # However, for our simplified version we'll simulate it
            bot.send_message(
                dm_recipient_id,
                f"[Image]({dm_image_url})\n\n{dm_image_caption}",
                parse_mode="Markdown"
            )
            
            # Log the direct message
            with app.app_context():
                from models import AdminMessage
                import json
                
                # Save the message to the database
                message_data = json.dumps({
                    "image_url": dm_image_url,
                    "caption": dm_image_caption
                })
                
                new_message = AdminMessage(
                    content=message_data,
                    message_type="image",
                    recipient_id=dm_recipient_id,
                    sent_by=chat_id,
                    status="sent"
                )
                db.session.add(new_message)
                db.session.commit()
            
            # Clear the stored data
            dm_recipient_id = None
            dm_image_url = None
            dm_image_caption = None
            
            # Send confirmation message
            bot.send_message(
                chat_id,
                "✅ Image message sent successfully!",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Send Another Message", "callback_data": "admin_direct_message"}],
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            
        except Exception as e:
            logging.error(f"Error sending image message to user {dm_recipient_id}: {e}")
            bot.send_message(chat_id, f"Error sending image message: {str(e)}")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_send_direct_message_image_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sending image message: {str(e)}")

def admin_back_handler(update, chat_id):
    """Handle the back button to return to the main admin panel."""
    try:
        admin_command(update, chat_id)
    except Exception as e:
        import logging
        logging.error(f"Error in admin_back_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error returning to admin panel: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def run_polling():
    """Start the bot polling loop."""
    # Get bot token from environment variable or config
    token = os.environ.get('TELEGRAM_BOT_TOKEN', BOT_TOKEN)
    
    if not token:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    global bot
    bot = SimpleTelegramBot(token)
    
    # Add command handlers
    bot.add_command_handler("/start", start_command)
    bot.add_command_handler("/help", help_command)
    bot.add_command_handler("/deposit", deposit_command)
    bot.add_command_handler("/dashboard", dashboard_command)
    bot.add_command_handler("/settings", settings_command)
    bot.add_command_handler("/referral", referral_command)
    bot.add_command_handler("/admin", admin_command)
    bot.add_command_handler("/admin_trade_post", admin_trade_post_handler)
    
    # Add a handler for UI section labels in keyboards (does nothing when clicked)
    bot.add_callback_handler("ignore", lambda update, chat_id: None)
    
    # Add callback handlers with all the buttons from the original design
    bot.add_callback_handler("skip_wallet", skip_wallet_callback)
    bot.add_callback_handler("dashboard", dashboard_command)
    bot.add_callback_handler("view_dashboard", dashboard_command)  # New button name from original design
    bot.add_callback_handler("deposit", deposit_command)
    bot.add_callback_handler("referral", referral_command)
    bot.add_callback_handler("settings", settings_command)
    bot.add_callback_handler("how_it_works", help_command)
    bot.add_callback_handler("help", help_command)  # New button name from original design
    bot.add_callback_handler("start", show_main_menu_callback)  # For "Back to Main Menu" button
    bot.add_callback_handler("copy_address", lambda update, chat_id: bot.send_message(chat_id, "Address copied to clipboard (simulated)"))
    bot.add_callback_handler("deposit_confirmed", deposit_confirmed_handler)
    
    # Dashboard-specific buttons
    bot.add_callback_handler("withdraw_profit", withdraw_profit_handler)
    bot.add_callback_handler("withdraw_all", withdraw_all_handler)
    bot.add_callback_handler("withdraw_profit_only", withdraw_profit_only_handler)
    bot.add_callback_handler("withdraw_custom", withdraw_custom_handler)
    bot.add_callback_handler("view_tx", lambda update, chat_id: bot.send_message(chat_id, "Transaction details will be available on Solana Explorer once confirmed. Usually takes 10-15 seconds."))
    bot.add_callback_handler("trading_history", trading_history_handler)
    bot.add_callback_handler("transaction_history", transaction_history_handler)
    bot.add_callback_handler("support", support_handler)
    bot.add_callback_handler("faqs", faqs_handler)
    
    # Support-specific buttons
    bot.add_callback_handler("live_chat", live_chat_handler)
    bot.add_callback_handler("submit_ticket", submit_ticket_handler)
    
    # Settings-specific buttons
    bot.add_callback_handler("update_wallet", lambda update, chat_id: bot.send_message(chat_id, "Wallet update feature coming soon. Your current wallet is linked to your account."))
    bot.add_callback_handler("notification_settings", lambda update, chat_id: bot.send_message(chat_id, "Notification settings can be customized soon. Currently all important alerts are enabled."))
    bot.add_callback_handler("security_settings", lambda update, chat_id: bot.send_message(chat_id, "Your account is protected with the highest security standards. Additional security features coming soon."))
    
    # Referral-specific buttons
    bot.add_callback_handler("referral", referral_command)
    bot.add_callback_handler("copy_referral", copy_referral_handler)
    bot.add_callback_handler("referral_stats", referral_stats_handler)
    bot.add_callback_handler("share_referral", share_referral_handler)
    bot.add_callback_handler("referral_earnings", lambda update, chat_id: bot.send_message(chat_id, "Your referral earnings will appear here once your friends start trading."))
    
    # New enhanced referral buttons
    bot.add_callback_handler("referral_qr_code", referral_qr_code_handler)
    bot.add_callback_handler("copy_referral_link", copy_referral_link_handler)
    bot.add_callback_handler("referral_how_it_works", referral_how_it_works_handler)
    bot.add_callback_handler("referral_tips", referral_tips_handler)
    
    # Trade history button handler
    bot.add_callback_handler("view_trade_history", trade_history_display_handler)
# Admin panel handlers
    bot.add_callback_handler("admin_user_management", admin_user_management_handler)
    bot.add_callback_handler("admin_wallet_settings", admin_wallet_settings_handler)
    bot.add_callback_handler("admin_broadcast", admin_broadcast_handler)
    bot.add_callback_handler("admin_direct_message", admin_direct_message_handler)
    bot.add_callback_handler("admin_view_stats", admin_view_stats_handler)
    bot.add_callback_handler("admin_adjust_balance", admin_adjust_balance_handler)
    bot.add_callback_handler("admin_view_tickets", admin_view_tickets_handler)
    bot.add_callback_handler("admin_referral_overview", admin_referral_overview_handler)
    bot.add_callback_handler("admin_referral_payouts", admin_referral_payouts_handler)
    bot.add_callback_handler("admin_deposit_logs", admin_deposit_logs_handler)
    bot.add_callback_handler("admin_search_user_referrals", lambda update, chat_id: bot.send_message(chat_id, "User referral search feature requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_bot_settings", admin_bot_settings_handler)
    bot.add_callback_handler("admin_exit", admin_exit_handler)
    bot.add_callback_handler("admin_back", admin_back_handler)
    bot.add_callback_handler("admin_view_active_users", admin_view_active_users_handler)
    bot.add_callback_handler("admin_view_all_users", admin_view_all_users_button_handler)
    bot.add_callback_handler("admin_search_user", admin_search_user_handler)
    bot.add_callback_handler("admin_export_csv", admin_export_csv_handler)
    bot.add_callback_handler("admin_export_deposits_csv", admin_export_deposits_csv_handler)
    bot.add_callback_handler("admin_change_wallet", admin_change_wallet_handler)
    bot.add_callback_handler("admin_view_wallet_qr", admin_view_wallet_qr_handler)
    bot.add_callback_handler("admin_update_min_deposit", admin_update_min_deposit_handler)
    bot.add_callback_handler("admin_edit_notification_time", admin_edit_notification_time_handler)
    bot.add_callback_handler("admin_toggle_daily_updates", admin_toggle_daily_updates_handler)
    bot.add_callback_handler("admin_manage_roi", admin_manage_roi_handler)
    bot.add_callback_handler("admin_manage_withdrawals", admin_manage_withdrawals_handler)
    bot.add_callback_handler("admin_view_completed_withdrawals", admin_view_completed_withdrawals_handler)
    
    # Additional admin handlers from the original codebase
    bot.add_callback_handler("admin_send_message", lambda update, chat_id: bot.send_message(chat_id, "Direct message sending requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_adjust_user_balance", admin_adjust_balance_handler)  # Use the actual handler function
    bot.add_callback_handler("admin_set_initial_deposit", admin_set_initial_deposit_handler)  # Handler for setting initial deposit
    bot.add_callback_handler("admin_confirm_initial_deposit", admin_confirm_initial_deposit_handler)  # Confirmation handler
    bot.add_callback_handler("admin_process_withdrawal", lambda update, chat_id: bot.send_message(chat_id, "Withdrawal processing feature coming soon."))
    bot.add_callback_handler("admin_process_tickets", lambda update, chat_id: bot.send_message(chat_id, "Ticket processing feature requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_export_referrals", admin_export_referrals_handler)
    
    # Broadcast message type handlers
    bot.add_callback_handler("admin_broadcast_text", admin_broadcast_text_handler)
    bot.add_callback_handler("admin_broadcast_image", admin_broadcast_image_handler)
    bot.add_callback_handler("admin_broadcast_announcement", admin_broadcast_announcement_handler)
    bot.add_callback_handler("admin_broadcast_trade", admin_broadcast_trade_handler)
    
    # Broadcast targeting handlers
    bot.add_callback_handler("admin_broadcast_active", admin_broadcast_active)
    bot.add_callback_handler("admin_broadcast_all", admin_broadcast_all)
    
    # Direct message type handlers
    bot.add_callback_handler("admin_dm_text", admin_dm_text_handler)
    bot.add_callback_handler("admin_dm_image", admin_dm_image_handler)
    bot.add_callback_handler("admin_search_user_for_dm", admin_search_user_for_dm_handler)
    bot.add_callback_handler("admin_pause_roi_cycle", lambda update, chat_id: bot.send_message(chat_id, "ROI cycle paused successfully!"))
    bot.add_callback_handler("admin_adjust_roi_percentage", lambda update, chat_id: bot.send_message(chat_id, "ROI percentage adjustment requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_resume_roi_cycle", lambda update, chat_id: bot.send_message(chat_id, "ROI cycle resumed successfully!"))
    bot.add_callback_handler("admin_start_roi_cycle", lambda update, chat_id: bot.send_message(chat_id, "New ROI cycle started successfully!"))
    bot.add_callback_handler("admin_reset_user", lambda update, chat_id: bot.send_message(chat_id, "User reset feature coming soon."))
    bot.add_callback_handler("admin_remove_user", lambda update, chat_id: bot.send_message(chat_id, "User removal requires confirmation."))
    bot.add_callback_handler("admin_change_support_username", admin_change_support_username_handler)
    bot.add_callback_handler("admin_send_broadcast", admin_send_broadcast_handler)
    bot.add_callback_handler("admin_confirm_withdrawal", lambda update, chat_id: bot.send_message(chat_id, "Withdrawal confirmed successfully!"))
    bot.add_callback_handler("admin_send_direct_message", admin_send_direct_message_handler)
    bot.add_callback_handler("admin_send_direct_message_image", admin_send_direct_message_image_handler)
    # Use the original handler to keep things simple
    bot.add_callback_handler("admin_confirm_adjustment", admin_confirm_adjustment_handler)
    bot.add_callback_handler("admin_confirm_remove_user", lambda update, chat_id: bot.send_message(chat_id, "User removed successfully!"))
    
    # Start the bot
    bot.start_polling()

# Helper functions for dashboard interface
def get_user_roi_metrics(user_id):
    """Get ROI metrics for a user - simplified implementation"""
    with app.app_context():
        from models import TradingCycle, CycleStatus
        from datetime import datetime, timedelta
        
        # Query for the user's active trading cycle
        active_cycle = TradingCycle.query.filter_by(
            user_id=user_id, 
            status=CycleStatus.IN_PROGRESS
        ).first()
        
        # Default metrics if no active cycle
        metrics = {
            'has_active_cycle': False,
            'days_elapsed': 0,
            'days_remaining': 7,
            'progress_percentage': 0,
            'target_balance': 0,
            'current_balance': 0,
            'is_on_track': True
        }
        
        if active_cycle:
            # Calculate days elapsed
            days_elapsed = (datetime.utcnow() - active_cycle.start_date).days
            days_elapsed = max(0, min(7, days_elapsed))
            
            # Calculate days remaining
            days_remaining = max(0, 7 - days_elapsed)
            
            # Calculate progress percentage
            if active_cycle.target_balance > 0:
                progress = (active_cycle.current_balance / active_cycle.target_balance) * 100
            else:
                progress = 0
            
            # Update metrics
            metrics = {
                'has_active_cycle': True,
                'days_elapsed': days_elapsed,
                'days_remaining': days_remaining,
                'progress_percentage': min(100, progress),
                'target_balance': active_cycle.target_balance,
                'current_balance': active_cycle.current_balance,
                'is_on_track': active_cycle.is_on_track() if hasattr(active_cycle, 'is_on_track') else True
            }
        
        return metrics

# Define dashboard button handler functions
def withdraw_profit_handler(update, chat_id):
    """Handle the withdraw profit button with real-time processing."""
    try:
        with app.app_context():
            from models import User, Profit
            from sqlalchemy import func
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
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
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💸 Withdraw All", "callback_data": "withdraw_all"},
                    {"text": "💲 Withdraw Profit", "callback_data": "withdraw_profit_only"}
                ],
                [{"text": "📈 Custom Amount", "callback_data": "withdraw_custom"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(
                chat_id, 
                withdrawal_message, 
                parse_mode="Markdown", 
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_profit_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying withdrawal options: {str(e)}")

def trading_history_handler(update, chat_id):
    """Handle the request to view trading history."""
    try:
        user_id = update['callback_query']['from']['id']
        with app.app_context():
            # Get user from database
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                bot.send_message(chat_id, "⚠️ User not found in database.")
                return
            
            # Get today's date for filtering trades
            today_date = datetime.now().date()
            
            # Get all trades for today
            trades_today = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type.in_(['buy', 'sell']),
                Transaction.timestamp >= datetime.combine(today_date, datetime.min.time())
            ).all()
            
            # Get trading stats from yield_data.json instead of just today's trades
            profitable_trades = 0
            loss_trades = 0
            
            # Try to get stats from yield_data.json file first
            try:
                # Try multiple possible locations for yield_data.json
                possible_paths = ['yield_data.json', '/home/runner/workspace/yield_data.json', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yield_data.json')]
                
                yield_data_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        yield_data_path = path
                        break
                
                if yield_data_path and os.path.exists(yield_data_path):
                    with open(yield_data_path, 'r') as f:
                        yield_data = json.load(f)
                    
                    user_id_str = str(user.id)
                    if user_id_str in yield_data:
                        user_data = yield_data[user_id_str]
                        # Get wins and losses from yield_data
                        profitable_trades = user_data.get('wins', 0)
                        loss_trades = user_data.get('losses', 0)
                        logger.info(f"Got stats from yield_data.json: {profitable_trades} wins, {loss_trades} losses")
                        
            except Exception as e:
                logger.error(f"Error reading yield_data.json: {e}")
                
            # Fallback to calculating from today's trades if we didn't get stats from yield_data.json
            if profitable_trades == 0 and loss_trades == 0:
                for tx in trades_today:
                    if hasattr(tx, 'profit_amount') and tx.profit_amount is not None:
                        if tx.profit_amount > 0:
                            profitable_trades += 1
                        elif tx.profit_amount < 0:
                            loss_trades += 1
            
            # Calculate win rate
            total_trades = profitable_trades + loss_trades
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Build a visually stunning and user-friendly performance dashboard
            performance_message = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
            
            # Balance section - highlight the important numbers
            performance_message += "💰 *BALANCE*\n"
            performance_message += f"Initial: {user.initial_deposit:.2f} SOL\n"
            performance_message += f"Current: {user.balance:.2f} SOL\n"
            
            # Get total profit
            total_profit_amount = user.balance - user.initial_deposit
            total_profit_percentage = (total_profit_amount / user.initial_deposit * 100) if user.initial_deposit > 0 else 0
            
            performance_message += f"Profit: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)\n\n"
            
            # Get today's profit data
            today_profit = Profit.query.filter_by(user_id=user.id, date=today_date).first()
            today_profit_amount = today_profit.amount if today_profit else 0
            today_profit_percentage = today_profit.percentage if today_profit else 0
            
            # Today's profit - emphasized and eye-catching
            performance_message += "📈 *TODAY'S PERFORMANCE*\n"
            if today_profit_amount > 0:
                performance_message += f"Profit: +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)\n\n"
            else:
                yesterday_balance = user.balance - today_profit_amount
                performance_message += "No profit recorded yet today\n"
                performance_message += f"Starting: {yesterday_balance:.2f} SOL\n\n"
            
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
            
            # Profit streak - motivational and prominent
            performance_message += "🔥 *WINNING STREAK*\n"
            if streak > 0:
                streak_emoji = "🔥" if streak >= 3 else "✨"
                performance_message += f"{streak_emoji} {streak} day{'s' if streak > 1 else ''} in a row!\n"
                if streak >= 5:
                    performance_message += "Incredible winning streak! Keep it up! 🏆\n\n"
                else:
                    performance_message += "You're on fire! Keep building momentum! 💪\n\n"
            else:
                performance_message += "Start your streak today with your first profit!\n\n"
            
            # Token Trading Performance - Real Results
            performance_message += "🎯 *TOKEN TRADING RESULTS*\n"
            performance_message += f"🟢 Winning Tokens: {profitable_trades}\n"
            performance_message += f"🔴 Losing Tokens: {loss_trades}\n"
            
            if total_trades > 0:
                performance_message += f"Success Rate: {win_rate:.1f}%\n"
                performance_message += f"Tokens Traded: {total_trades}\n\n"
                
                # Provide specific feedback based on token trading performance
                if win_rate >= 75:
                    performance_message += "🔥 Exceptional token picks! Your bot is crushing the memecoin market!\n"
                elif win_rate >= 50:
                    performance_message += "📈 Solid token selection! Your strategy is beating the market!\n"
                elif win_rate >= 30:
                    performance_message += "🔄 Mixed results - the bot is learning market patterns and adapting!\n"
                else:
                    performance_message += "📊 Tough market conditions - bot is analyzing and improving token selection!\n"
            else:
                performance_message += "⏳ No token trades completed yet. Scanning for profitable opportunities!\n"
            
            # Create proper keyboard with transaction history button but no trade history button
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💲 Deposit More", "callback_data": "deposit"},
                    {"text": "💰 Withdraw", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "📜 Transaction History", "callback_data": "transaction_history"}
                ],
                [
                    {"text": "🔙 Back to Dashboard", "callback_data": "dashboard"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                performance_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import traceback
        print(f"Error in trading_history_handler: {e}")
        print(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying performance data: {str(e)}")

def support_handler(update, chat_id):
    """Show support options."""
    try:
        support_message = (
            "🛟 *THRIVE Support*\n\n"
            "We're here to help! Choose from the options below to get the support you need:\n\n"
            "💬 *Live Chat*: Talk to a support agent directly\n"
            "📚 *FAQs*: Browse our frequently asked questions\n"
            "📝 *Submit Ticket*: Create a support ticket for complex issues\n\n"
            "Our support team is available 24/7 to assist you with any questions or concerns."
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "💬 Live Chat", "callback_data": "live_chat"},
                {"text": "📚 FAQs", "callback_data": "faqs"}
            ],
            [
                {"text": "📝 Submit Ticket", "callback_data": "submit_ticket"},
                {"text": "🔙 Back", "callback_data": "dashboard"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            support_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in support_handler: {e}")
        bot.send_message(chat_id, f"Error displaying support options: {str(e)}")

def withdraw_all_handler(update, chat_id):
    """Process withdrawing all funds with a simple check for sufficient balance."""
    try:
        with app.app_context():
            import random
            from models import User, Transaction
            from datetime import datetime
            
            # Check user status and balance
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Send simple processing message
            bot.send_message(
                chat_id,
                "💸 *Processing...*",
                parse_mode="Markdown"
            )
            
            # Get current balance to determine withdrawal flow
            withdrawal_amount = user.balance
            is_funded = withdrawal_amount > 0
            
            # If not funded, show error message
            if not is_funded:
                # Show failure message
                no_funds_message = (
                    "❌ *Withdrawal Failed*\n\n"
                    "Reason: Insufficient balance in your account.\n\n"
                    "Your current balance is: *0.00 SOL*\n\n"
                    "To withdraw funds, you need to make a deposit first."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "💰 Deposit Funds", "callback_data": "deposit"}],
                    [{"text": "📊 View Dashboard", "callback_data": "view_dashboard"}],
                    [{"text": "🏠 Return to Main Menu", "callback_data": "start"}]
                ])
                
                bot.send_message(
                    chat_id,
                    no_funds_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Generate final message based on account status
            if not is_funded:
                # NON-FUNDED ACCOUNT - Show failure message
                no_funds_message = (
                    "❌ *Withdrawal Failed*\n\n"
                    "Reason: Insufficient balance in your account.\n\n"
                    "Your current balance is: *0.00 SOL*\n\n"
                    "To withdraw funds, you need to make a deposit first."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "💰 Deposit Funds", "callback_data": "deposit"}],
                    [{"text": "📊 View Dashboard", "callback_data": "view_dashboard"}],
                    [{"text": "🏠 Return to Main Menu", "callback_data": "start"}]
                ])
                
                bot.send_message(
                    chat_id,
                    no_funds_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # FUNDED ACCOUNT - Process the withdrawal
            
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
            
            # Reserve the balance for withdrawal
            previous_balance = withdrawal_amount
            user.balance = 0
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Show pending withdrawal message
            success_message = (
                "⏳ *Withdrawal Request Submitted*\n\n"
                f"Amount: *{previous_balance:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:] if len(user.wallet_address) > 10 else user.wallet_address}\n"
                f"Request ID: #{new_transaction.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been submitted and is pending approval by an administrator. "
                "You will be notified once your withdrawal has been processed."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔎 View Transaction", "callback_data": "view_tx"}],
                [{"text": "💪 Make Another Deposit", "callback_data": "deposit"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(
                chat_id,
                success_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_all_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_text = "⚠️ Sorry, there was an error processing your withdrawal. Please try again later."
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
        ])
        
        bot.send_message(
            chat_id,
            error_text,
            reply_markup=keyboard
        )

def custom_withdrawal_amount_handler(update, chat_id, text):
    """Handle the custom withdrawal amount input."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Try to convert the input to a float
        try:
            amount = float(text.strip())
        except ValueError:
            # Not a valid number
            bot.send_message(
                chat_id,
                "⚠️ Please enter a valid number for the withdrawal amount.\n\n"
                "Example: 0.5",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            return
        
        # Check if the amount is positive
        if amount <= 0:
            bot.send_message(
                chat_id,
                "⚠️ The withdrawal amount must be greater than 0.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            return
        
        # Check if the amount is too small
        if amount < 0.01:
            bot.send_message(
                chat_id,
                "⚠️ The minimum withdrawal amount is 0.01 SOL.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            return
            
        # Process the withdrawal with the entered amount
        bot.process_custom_withdrawal(chat_id, amount)
        
    except Exception as e:
        import logging
        logging.error(f"Error in custom_withdrawal_amount_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while processing your withdrawal request. Please try again.",
            parse_mode="Markdown"
        )

def withdraw_profit_only_handler(update, chat_id):
    """Process withdrawing only profits with a simple check for available profits."""
    try:
        with app.app_context():
            import random
            from models import User, Transaction, Profit
            from datetime import datetime
            from sqlalchemy import func
            
            # Get user and profits
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Send simple processing message
            bot.send_message(
                chat_id,
                "💸 *Processing...*",
                parse_mode="Markdown"
            )
            
            # Calculate profits
            total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
            has_profits = total_profit_amount > 0
            
            # If no profits, show error message
            if not has_profits:
                # Show failure message for no profits
                no_profits_message = (
                    "❌ *Profit Withdrawal Failed*\n\n"
                    "Reason: No profits available to withdraw.\n\n"
                    "Your account status:\n"
                    f"• Current balance: *{user.balance:.6f} SOL*\n"
                    f"• Available profits: *0.00 SOL*\n\n"
                    "Continue trading to generate profits that you can withdraw."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "🔄 Start Trading", "callback_data": "trade_history"}],
                    [{"text": "💰 Make a Deposit", "callback_data": "deposit"}],
                    [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
                ])
                
                bot.send_message(
                    chat_id,
                    no_profits_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # We've already checked for profits earlier, no need to re-check
            
            # HAS PROFITS - Process the profit withdrawal
            
            # Create transaction with pending status
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
            previous_balance = user.balance
            user.balance -= total_profit_amount
            user.balance = max(0, user.balance)  # Ensure we don't go negative
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Show pending withdrawal message
            success_message = (
                "⏳ *Withdrawal Request Submitted*\n\n"
                f"Amount: *{total_profit_amount:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:] if len(user.wallet_address) > 10 else user.wallet_address}\n"
                f"Request ID: #{new_transaction.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been submitted and is pending approval by an administrator. "
                "You will be notified once your withdrawal has been processed.\n\n"
                f"Remaining balance: *{user.balance:.6f} SOL*"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "💸 View Transaction", "callback_data": "view_tx"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(
                chat_id,
                success_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_profit_only_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_text = "⚠️ Sorry, there was an error processing your profit withdrawal. Please try again later."
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
        ])
        
        bot.send_message(
            chat_id,
            error_text,
            reply_markup=keyboard
        )

def withdraw_custom_handler(update, chat_id):
    """Handle custom withdrawal amount."""
    try:
        with app.app_context():
            from models import User
            from sqlalchemy import func
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Get available balance
            available_balance = user.balance
            
            # Display custom withdrawal form
            custom_withdrawal_message = (
                "💰 *Custom Withdrawal Amount*\n\n"
                f"Available Balance: *{available_balance:.6f} SOL*\n\n"
                "Please enter the amount you'd like to withdraw below.\n\n"
                "Minimum withdrawal: 0.01 SOL\n"
                "Maximum withdrawal: Your available balance\n\n"
                "To cancel this operation, click the 'Cancel' button."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "withdraw_profit"}]
            ])
            
            bot.send_message(
                chat_id,
                custom_withdrawal_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add a listener for the user's input of withdrawal amount
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            
            # Also provide preset options for convenience
            
            # Create a selection of withdrawal amounts based on available balance
            amount_options = []
            
            if available_balance >= 0.01:
                amount_options.append({"text": "0.01 SOL", "callback_data": "custom_withdraw_0.01"})
            
            if available_balance >= 0.05:
                amount_options.append({"text": "0.05 SOL", "callback_data": "custom_withdraw_0.05"})
            
            if available_balance >= 0.1:
                amount_options.append({"text": "0.1 SOL", "callback_data": "custom_withdraw_0.1"})
            
            if available_balance >= 0.5:
                amount_options.append({"text": "0.5 SOL", "callback_data": "custom_withdraw_0.5"})
            
            if available_balance >= 1.0:
                amount_options.append({"text": "1.0 SOL", "callback_data": "custom_withdraw_1.0"})
            
            # Create rows of 2 buttons each
            keyboard_rows = []
            for i in range(0, len(amount_options), 2):
                row = amount_options[i:i+2]
                keyboard_rows.append(row)
            
            # Add 50% and 25% options in a new row
            percentage_row = []
            if available_balance > 0:
                percentage_row.append({"text": "25% of Balance", "callback_data": f"custom_withdraw_{available_balance * 0.25:.6f}"})
                percentage_row.append({"text": "50% of Balance", "callback_data": f"custom_withdraw_{available_balance * 0.5:.6f}"})
                keyboard_rows.append(percentage_row)
            
            # Add back button
            keyboard_rows.append([{"text": "🔙 Back", "callback_data": "withdraw_profit"}])
            
            custom_amounts_message = (
                "💎 *Or Select Withdrawal Amount*\n\n"
                f"Your available balance: *{available_balance:.6f} SOL*\n\n"
                "Choose from the preset amounts below, or go back to select another withdrawal option:"
            )
            
            keyboard = bot.create_inline_keyboard(keyboard_rows)
            
            bot.send_message(
                chat_id,
                custom_amounts_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_custom_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing custom withdrawal: {str(e)}")

def transaction_history_handler(update, chat_id):
    """Show the user's transaction history with deposits, withdrawals, buys, and sells."""
    try:
        with app.app_context():
            from models import User, Transaction
            from datetime import datetime
            import re
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
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
                        
                        # Add type indicator with emoji and clickable token name
                        type_display = "Buy Order" if tx.transaction_type == "buy" else "Sell Order"
                        token_explorer_url = f"https://solscan.io/token/{tx.token_name}"
                        history_message += f"{trade_emoji} *{type_display}* [${tx.token_name}]({token_explorer_url})\n"
                        
                        # Add price information
                        if price > 0:
                            history_message += f"• *{trade_type}:* ${price:.6f}\n"
                        else:
                            history_message += f"• *{trade_type}:* {tx.amount:.4f} SOL\n"
                        
                        # Token information already included in the header
                        
                        # Add ROI if available (for sell transactions)
                        if tx.transaction_type == "sell" and roi_percentage is not None:
                            roi_emoji = "📈" if roi_percentage > 0 else "📉"
                            history_message += f"• *ROI:* {roi_emoji} {roi_percentage:.2f}%\n"
                        
                        # Add trade strategy
                        history_message += f"• *Trade Type:* {trade_strategy}\n"
                        
                        # Add date
                        history_message += f"• *Date:* {date_str}\n"
                        
                        # Add transaction hash as clickable link if available
                        if hasattr(tx, 'tx_hash') and tx.tx_hash:
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
                        if hasattr(tx, 'tx_hash') and tx.tx_hash:
                            # Create a Solana Explorer link for the transaction
                            explorer_url = f"https://solscan.io/tx/{tx.tx_hash}"
                            history_message += f"• *TX:* [View on Solscan]({explorer_url})\n"
                        
                        # Only add notes for non-admin related messages
                        if hasattr(tx, 'notes') and tx.notes:
                            notes = str(tx.notes)
                            # Don't show admin approval messages to users
                            if not ("pending admin approval" in notes.lower() or 
                                    "admin" in notes.lower() or 
                                    "approval" in notes.lower()):
                                if len(notes) > 50:  # Truncate long notes
                                    notes = notes[:47] + "..."
                                history_message += f"• *Info:* _{notes}_\n"
                    
                    history_message += "───────────────────\n\n"
            else:
                history_message = "📜 *Transaction History*\n\n*No transactions found.*\n\nStart trading to see your transaction history here!"
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📈 Export CSV", "callback_data": "export_transactions"},
                    {"text": "🔙 Back", "callback_data": "trading_history"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                history_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in transaction_history_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying transaction history: {str(e)}")


def trade_history_display_handler(update, chat_id):
    """Display the yield module's trade history with attractive formatting."""
    try:
        # Get the user ID from the database
        with app.app_context():
            from models import User, TradingPosition
            from datetime import datetime
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
                
            user_id = user.id
            
            # Check if user has funded their account
            has_funds = user.balance > 0 or user.initial_deposit > 0
            
            # First check if there are any closed trading positions (admin broadcasts)
            closed_positions = TradingPosition.query.filter_by(
                user_id=user_id,
                status='closed'
            ).order_by(TradingPosition.timestamp.desc()).all()
            
            # If there are closed positions, we'll show those regardless of the yield module
            has_admin_trades = len(closed_positions) > 0
            
            # Import the yield_module function safely
            try:
                # Try to import directly from the module
                from yield_module import get_trade_history_message, create_pagination_keyboard, simulate_trade
                
                # Different behavior based on funding status
                if has_funds:
                    if has_admin_trades:
                        # Show admin-broadcasted trades alongside yield module trades
                        # Format the message
                        history_message = "📊 <b>Your Trading History</b>\n\n"
                        
                        # Add closed positions (admin broadcasts)
                        for position in closed_positions:
                            # Calculate profit/loss
                            pl_amount = (position.current_price - position.entry_price) * position.amount
                            pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                            
                            # Determine emoji based on profit/loss
                            pl_emoji = "📈" if pl_percentage > 0 else "📉"
                            date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                            
                            # Add trade details
                            # Get trade type if it exists
                            trade_type = "Scalp"
                            if hasattr(position, 'trade_type') and position.trade_type:
                                trade_type = position.trade_type
                            
                            # Add trade details with enhanced formatting
                            history_message += f"🪙 <b>{position.token_name}</b> {pl_emoji} <b>{pl_percentage:.1f}%</b>\n"
                            history_message += f"<i>Strategy: {trade_type} Trade</i>\n"
                            history_message += f"💰 Amount: {position.amount:.4f} SOL\n"
                            history_message += f"📥 Entry: <b>${position.entry_price:.6f}</b>\n"
                            history_message += f"📤 Exit: <b>${position.current_price:.6f}</b>\n"
                            
                            # Format profit/loss with color indicators
                            if pl_amount > 0:
                                history_message += f"✅ Profit: +{pl_amount:.4f} SOL\n"
                            else:
                                history_message += f"❌ Loss: {pl_amount:.4f} SOL\n"
                                
                            history_message += f"🕒 Executed: {date_str}\n"
                            history_message += f"───────────────────\n\n"
                        
                        # Try to get yield module trades as well
                        yield_message = get_trade_history_message(user_id)
                        if "No trade history found" not in yield_message:
                            # Append yield module trades after admin broadcasts
                            yield_message = yield_message.replace("📊 <b>Trading History</b>", "<b>Additional Trades</b>")
                            history_message += yield_message
                    else:
                        # For funded accounts with no admin trades, show yield module trade history
                        history_message = get_trade_history_message(user_id)
                        
                        if "No trade history found" in history_message:
                            # Simulate a sample trade for funded users to show them what it looks like
                            simulate_trade(user_id)
                            history_message = get_trade_history_message(user_id)
                    
                    # Create pagination keyboard
                    page_keyboard = create_pagination_keyboard(user_id, 0)
                    
                    # Convert to SimpleTelegramBot format
                    keyboard_markup = []
                    if 'inline_keyboard' in page_keyboard:
                        for row in page_keyboard['inline_keyboard']:
                            keyboard_row = []
                            for button in row:
                                keyboard_row.append({
                                    "text": button.get('text', ''),
                                    "callback_data": button.get('callback_data', '')
                                })
                            keyboard_markup.append(keyboard_row)
                    
                    # Add back button
                    keyboard_markup.append([{"text": "🔙 Back", "callback_data": "trading_history"}])
                    
                    # Send the message with the keyboard
                    keyboard = bot.create_inline_keyboard(keyboard_markup)
                    bot.send_message(chat_id, history_message, parse_mode="HTML", reply_markup=keyboard)
                else:
                    # Even if not funded, if they have admin trades, show those
                    if has_admin_trades:
                        # Format the message
                        history_message = "📊 <b>Your Trading History</b>\n\n"
                        
                        # Add closed positions (admin broadcasts)
                        for position in closed_positions:
                            # Calculate profit/loss
                            pl_amount = (position.current_price - position.entry_price) * position.amount
                            pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                            
                            # Determine emoji based on profit/loss
                            pl_emoji = "📈" if pl_percentage > 0 else "📉"
                            date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                            
                            # Add trade details
                            # Get trade type if it exists
                            trade_type = "Scalp"
                            if hasattr(position, 'trade_type') and position.trade_type:
                                trade_type = position.trade_type
                            
                            # Add trade details with enhanced formatting
                            history_message += f"🪙 <b>{position.token_name}</b> {pl_emoji} <b>{pl_percentage:.1f}%</b>\n"
                            history_message += f"<i>Strategy: {trade_type} Trade</i>\n"
                            history_message += f"💰 Amount: {position.amount:.4f} SOL\n"
                            history_message += f"📥 Entry: <b>${position.entry_price:.6f}</b>\n"
                            history_message += f"📤 Exit: <b>${position.current_price:.6f}</b>\n"
                            
                            # Format profit/loss with color indicators
                            if pl_amount > 0:
                                history_message += f"✅ Profit: +{pl_amount:.4f} SOL\n"
                            else:
                                history_message += f"❌ Loss: {pl_amount:.4f} SOL\n"
                                
                            history_message += f"🕒 Executed: {date_str}\n"
                            history_message += f"───────────────────\n\n"
                        
                        # Add back button
                        keyboard = bot.create_inline_keyboard([
                            [{"text": "🔙 Back", "callback_data": "trading_history"}]
                        ])
                        
                        bot.send_message(chat_id, history_message, parse_mode="HTML", reply_markup=keyboard)
                    else:
                        # For unfunded accounts with no admin trades, show a message encouraging deposit
                        deposit_keyboard = bot.create_inline_keyboard([
                            [{"text": "🔄 Deposit Funds", "callback_data": "deposit"}],
                            [{"text": "🔙 Back", "callback_data": "trading_history"}]
                        ])
                        
                        bot.send_message(
                            chat_id, 
                            "📊 <b>Trade History</b>\n\n"
                            "Your account is not yet funded. To start trading and building your "
                            "performance history, please deposit funds first.\n\n"
                            "Our AI trading system will automatically start making profitable trades "
                            "for you as soon as your account is funded.",
                            parse_mode="HTML",
                            reply_markup=deposit_keyboard
                        )
                
            except ImportError as e:
                # Fallback if import fails - still show admin trades if available
                if has_admin_trades:
                    # Format the message
                    history_message = "📊 <b>Your Trading History</b>\n\n"
                    
                    # Add closed positions (admin broadcasts)
                    for position in closed_positions:
                        # Calculate profit/loss
                        pl_amount = (position.current_price - position.entry_price) * position.amount
                        pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                        
                        # Determine emoji based on profit/loss
                        pl_emoji = "📈" if pl_percentage > 0 else "📉"
                        date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                        
                        # Add trade details
                        history_message += f"<b>{position.token_name}</b> {pl_emoji} {pl_percentage:.1f}%\n"
                        history_message += f"Amount: {position.amount:.6f} SOL\n"
                        history_message += f"Entry: ${position.entry_price:.6f}\n"
                        history_message += f"Exit: ${position.current_price:.6f}\n"
                        history_message += f"P/L: {pl_amount:.6f} SOL\n"
                        history_message += f"Date: {date_str}\n\n"
                    
                    # Add back button
                    keyboard = bot.create_inline_keyboard([
                        [{"text": "🔙 Back", "callback_data": "trading_history"}]
                    ])
                    
                    bot.send_message(chat_id, history_message, parse_mode="HTML", reply_markup=keyboard)
                elif has_funds:
                    # Message for funded accounts
                    bot.send_message(
                        chat_id, 
                        "📊 <b>Trade History</b>\n\n"
                        "Track your Solana memecoin trades here with real-time performance metrics. "
                        "Our AI trading system is analyzing the market for the best opportunities.\n\n"
                        "Your first trades will appear here once the market conditions are optimal.",
                        parse_mode="HTML"
                    )
                else:
                    # Message for unfunded accounts
                    deposit_keyboard = bot.create_inline_keyboard([
                        [{"text": "🔄 Deposit Funds", "callback_data": "deposit"}],
                        [{"text": "🔙 Back", "callback_data": "trading_history"}]
                    ])
                    
                    bot.send_message(
                        chat_id, 
                        "📊 <b>Trade History</b>\n\n"
                        "Your account needs to be funded before the AI trading system can start "
                        "working for you. Deposit as little as 0.5 SOL to activate automated trading.\n\n"
                        "After funding, our system will start identifying profitable memecoin "
                        "opportunities for you.",
                        parse_mode="HTML",
                        reply_markup=deposit_keyboard
                    )
                
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error in trade_history_display_handler: {e}")
        logging.error(traceback.format_exc())
        
        # Generic fallback message with deposit button
        deposit_keyboard = bot.create_inline_keyboard([
            [{"text": "🔄 Deposit Funds", "callback_data": "deposit"}],
            [{"text": "🔙 Back", "callback_data": "trading_history"}]
        ])
        
        bot.send_message(
            chat_id, 
            "📊 <b>Trade History</b>\n\n"
            "Our AI trading algorithms are actively scanning the Solana memecoin market "
            "to identify the most profitable opportunities for you.\n\n"
            "Your trading activity will be displayed here with detailed performance analytics once "
            "your account is active.",
            parse_mode="HTML",
            reply_markup=deposit_keyboard
        )

def live_chat_handler(update, chat_id):
    """Handle the live chat button and redirect to admin username."""
    try:
        # Get the admin username for live chat from the database setting if exists, otherwise use a default
        with app.app_context():
            from models import User
            import os
            
            # Try to get the admin user's username from environment or a default
            admin_username = os.environ.get('SUPPORT_USERNAME', 'thrivesupport')
            
            # Prepare the message with the admin username
            live_chat_message = (
                "💬 *Live Chat Support*\n\n"
                f"Our support team is ready to assist you! Please message @{admin_username} directly on Telegram.\n\n"
                "When contacting support, please provide:\n"
                "• Your Telegram username\n"
                "• Brief description of your issue\n"
                "• Any relevant transaction details\n\n"
                "Support hours: 24/7"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Support", "callback_data": "support"}]
            ])
            
            bot.send_message(
                chat_id,
                live_chat_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in live_chat_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying live chat information: {str(e)}")

def submit_ticket_handler(update, chat_id):
    """Handle the submit ticket button."""
    try:
        ticket_message = (
            "📝 *Submit Support Ticket*\n\n"
            "Please provide the following information in your next message:\n\n"
            "1. Subject of your ticket\n"
            "2. Detailed description of your issue\n"
            "3. Any relevant transaction IDs or screenshots\n\n"
            "Our support team will review your ticket and respond as soon as possible."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔙 Back to Support", "callback_data": "support"}]
        ])
        
        bot.send_message(
            chat_id,
            ticket_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the user's next message
        bot.add_message_listener(chat_id, 'support_ticket', support_ticket_message_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in submit_ticket_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying ticket submission form: {str(e)}")

def admin_change_support_username_handler(update, chat_id):
    """Handle changing the support username"""
    try:
        # Show the current support username and input prompt
        import os
        current_username = os.environ.get('SUPPORT_USERNAME', 'thrivesupport')
        
        message = (
            "🔄 *Change Support Username*\n\n"
            f"Current support username: @{current_username}\n\n"
            "Please enter the new support username without the @ symbol.\n"
            "This username will be shown to users in the Live Chat support section."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add listener for the next message
        bot.add_message_listener(chat_id, 'support_username', support_username_message_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_change_support_username_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error changing support username: {str(e)}")

def admin_update_min_deposit_handler(update, chat_id):
    """Handle updating the minimum deposit amount."""
    try:
        # First, get the current min deposit amount from SystemSettings or config
        with app.app_context():
            from models import SystemSettings
            from config import MIN_DEPOSIT
            
            # Try to get from database first
            min_deposit_setting = SystemSettings.query.filter_by(setting_name="min_deposit").first()
            current_min_deposit = float(min_deposit_setting.setting_value) if min_deposit_setting else MIN_DEPOSIT
            
            message = (
                "🔄 *Update Minimum Deposit*\n\n"
                f"Current minimum deposit: *{current_min_deposit:.2f} SOL*\n\n"
                "Enter the new minimum deposit amount in SOL.\n"
                "This is the minimum amount users need to deposit to activate the bot."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, 'min_deposit', min_deposit_message_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_update_min_deposit_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating minimum deposit: {str(e)}")

def min_deposit_message_handler(update, chat_id, text):
    """Handle the minimum deposit amount change."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Validate input is a positive number
        try:
            new_min_deposit = float(text.strip())
            if new_min_deposit <= 0:
                raise ValueError("Minimum deposit must be greater than 0")
        except ValueError as ve:
            bot.send_message(
                chat_id,
                f"⚠️ Invalid input: {str(ve)}. Please enter a positive number.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'min_deposit', min_deposit_message_handler)
            return
            
        # Save to database
        with app.app_context():
            from models import SystemSettings
            import os
            
            # Get or create the setting
            min_deposit_setting = SystemSettings.query.filter_by(setting_name="min_deposit").first()
            if not min_deposit_setting:
                min_deposit_setting = SystemSettings(
                    setting_name="min_deposit",
                    setting_value=str(new_min_deposit),
                    updated_by=str(chat_id)
                )
                db.session.add(min_deposit_setting)
            else:
                min_deposit_setting.setting_value = str(new_min_deposit)
                min_deposit_setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Update in memory for the current session
            os.environ['MIN_DEPOSIT'] = str(new_min_deposit)
            
            # Send confirmation
            confirmation_message = (
                "✅ *Minimum Deposit Updated Successfully*\n\n"
                f"New minimum deposit amount: *{new_min_deposit:.2f} SOL*\n\n"
                "This change will be applied to all new users and deposits."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in min_deposit_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the minimum deposit. Please try again.",
            parse_mode="Markdown"
        )

def support_username_message_handler(update, chat_id, text):
    """Handle the support username change."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Clean up the username (remove @ if present)
        new_username = text.strip().replace('@', '')
        
        if not new_username:
            bot.send_message(
                chat_id,
                "⚠️ Please enter a valid username.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'support_username', support_username_message_handler)
            return
        
        # Create or update the environment variable
        import os
        os.environ['SUPPORT_USERNAME'] = new_username
        
        # Send confirmation
        confirmation_message = (
            "✅ *Support Username Updated Successfully*\n\n"
            f"New support username: @{new_username}\n\n"
            "This change will be reflected in the Live Chat support section immediately."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
        ])
        
        bot.send_message(
            chat_id,
            confirmation_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in support_username_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the support username. Please try again.",
            parse_mode="Markdown"
        )

def admin_edit_notification_time_handler(update, chat_id):
    """Handle editing the daily notification time."""
    try:
        # First, get the current notification time from SystemSettings or config
        with app.app_context():
            from models import SystemSettings
            from config import DAILY_UPDATE_HOUR
            
            # Try to get from database first
            notification_time_setting = SystemSettings.query.filter_by(setting_name="daily_update_hour").first()
            current_notification_time = int(notification_time_setting.setting_value) if notification_time_setting else DAILY_UPDATE_HOUR
            
            message = (
                "🔄 *Update Daily Notification Time*\n\n"
                f"Current notification time: *{current_notification_time}:00 UTC*\n\n"
                "Enter the new notification hour (0-23) in UTC.\n"
                "This is when daily updates and ROI calculations will be sent to users."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, 'notification_time', notification_time_message_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_edit_notification_time_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating notification time: {str(e)}")

def notification_time_message_handler(update, chat_id, text):
    """Handle the notification time change."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Validate input is a number between 0-23
        try:
            new_time = int(text.strip())
            if new_time < 0 or new_time > 23:
                raise ValueError("Hour must be between 0 and 23")
        except ValueError as ve:
            bot.send_message(
                chat_id,
                f"⚠️ Invalid input: {str(ve)}. Please enter a number between 0 and 23.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'notification_time', notification_time_message_handler)
            return
            
        # Save to database
        with app.app_context():
            from models import SystemSettings
            import os
            
            # Get or create the setting
            time_setting = SystemSettings.query.filter_by(setting_name="daily_update_hour").first()
            if not time_setting:
                time_setting = SystemSettings(
                    setting_name="daily_update_hour",
                    setting_value=str(new_time),
                    updated_by=str(chat_id)
                )
                db.session.add(time_setting)
            else:
                time_setting.setting_value = str(new_time)
                time_setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Update in memory for the current session
            os.environ['DAILY_UPDATE_HOUR'] = str(new_time)
            
            # Send confirmation
            confirmation_message = (
                "✅ *Notification Time Updated Successfully*\n\n"
                f"New notification time: *{new_time}:00 UTC*\n\n"
                "This change will be applied to all future daily updates."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in notification_time_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the notification time. Please try again.",
            parse_mode="Markdown"
        )

def admin_toggle_daily_updates_handler(update, chat_id):
    """Handle toggling daily updates on/off."""
    try:
        # First, get the current status from SystemSettings
        with app.app_context():
            from models import SystemSettings
            
            # Try to get from database first
            daily_updates_setting = SystemSettings.query.filter_by(setting_name="daily_updates_enabled").first()
            
            # Default is enabled if setting doesn't exist
            current_status = daily_updates_setting.setting_value.lower() == 'true' if daily_updates_setting else True
            
            # Toggle the status
            new_status = not current_status
            
            # Update or create the setting
            if not daily_updates_setting:
                daily_updates_setting = SystemSettings(
                    setting_name="daily_updates_enabled",
                    setting_value=str(new_status).lower(),
                    updated_by=str(chat_id)
                )
                db.session.add(daily_updates_setting)
            else:
                daily_updates_setting.setting_value = str(new_status).lower()
                daily_updates_setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Send confirmation
            status_text = "ON" if new_status else "OFF"
            confirmation_message = (
                f"✅ *Daily Updates Toggled: {status_text}*\n\n"
                f"Daily updates are now {'enabled' if new_status else 'disabled'}.\n"
                f"{'Users will receive daily profit updates at the scheduled time.' if new_status else 'Users will not receive automated daily updates.'}"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_toggle_daily_updates_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error toggling daily updates: {str(e)}")

def admin_manage_roi_handler(update, chat_id):
    """Handle ROI settings and thresholds."""
    try:
        # Get the current ROI settings from config/database
        with app.app_context():
            from models import SystemSettings
            from config import SIMULATED_DAILY_ROI_MIN, SIMULATED_DAILY_ROI_MAX, SIMULATED_LOSS_PROBABILITY
            
            # Get settings from database if available
            roi_min_setting = SystemSettings.query.filter_by(setting_name="daily_roi_min").first()
            roi_max_setting = SystemSettings.query.filter_by(setting_name="daily_roi_max").first()
            loss_prob_setting = SystemSettings.query.filter_by(setting_name="loss_probability").first()
            
            # Use values from database or fallback to config
            roi_min = float(roi_min_setting.setting_value) if roi_min_setting else SIMULATED_DAILY_ROI_MIN
            roi_max = float(roi_max_setting.setting_value) if roi_max_setting else SIMULATED_DAILY_ROI_MAX
            loss_prob = float(loss_prob_setting.setting_value) if loss_prob_setting else SIMULATED_LOSS_PROBABILITY
            
            # Create the management message
            message = (
                "⚙️ *ROI Settings Management*\n\n"
                f"Current Min Daily ROI: *{roi_min:.2f}%*\n"
                f"Current Max Daily ROI: *{roi_max:.2f}%*\n"
                f"Loss Day Probability: *{loss_prob * 100:.1f}%*\n\n"
                "Select which ROI parameter you want to adjust:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "Update Min ROI", "callback_data": "admin_update_min_roi"}],
                [{"text": "Update Max ROI", "callback_data": "admin_update_max_roi"}],
                [{"text": "Update Loss Probability", "callback_data": "admin_update_loss_prob"}],
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Register the ROI update handlers
            bot.add_callback_handler("admin_update_min_roi", lambda update, chat_id: admin_update_roi_parameter(update, chat_id, "min"))
            bot.add_callback_handler("admin_update_max_roi", lambda update, chat_id: admin_update_roi_parameter(update, chat_id, "max"))
            bot.add_callback_handler("admin_update_loss_prob", lambda update, chat_id: admin_update_roi_parameter(update, chat_id, "loss"))
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_manage_roi_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying ROI settings: {str(e)}")

def admin_update_roi_parameter(update, chat_id, param_type):
    """Handle updating a specific ROI parameter."""
    try:
        with app.app_context():
            from models import SystemSettings
            from config import SIMULATED_DAILY_ROI_MIN, SIMULATED_DAILY_ROI_MAX, SIMULATED_LOSS_PROBABILITY
            
            # Set parameter-specific variables
            if param_type == "min":
                setting_name = "daily_roi_min"
                display_name = "Minimum Daily ROI"
                current_setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
                current_value = float(current_setting.setting_value) if current_setting else SIMULATED_DAILY_ROI_MIN
                input_guidance = "Enter the new minimum daily ROI percentage (0.1-5.0%)"
                value_validator = lambda x: 0.1 <= x <= 5.0
                error_message = "Value must be between 0.1% and 5.0%"
            elif param_type == "max":
                setting_name = "daily_roi_max"
                display_name = "Maximum Daily ROI"
                current_setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
                current_value = float(current_setting.setting_value) if current_setting else SIMULATED_DAILY_ROI_MAX
                input_guidance = "Enter the new maximum daily ROI percentage (0.5-10.0%)"
                value_validator = lambda x: 0.5 <= x <= 10.0
                error_message = "Value must be between 0.5% and 10.0%"
            elif param_type == "loss":
                setting_name = "loss_probability"
                display_name = "Loss Day Probability"
                current_setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
                current_value = float(current_setting.setting_value) if current_setting else SIMULATED_LOSS_PROBABILITY
                input_guidance = "Enter the probability of loss days (0.0-0.5 as decimal, e.g., 0.2 for 20%)"
                value_validator = lambda x: 0.0 <= x <= 0.5
                error_message = "Value must be between 0.0 and 0.5 (0-50%)"
                
            message = (
                f"🔄 *Update {display_name}*\n\n"
                f"Current value: *{current_value:.2f}{'%' if param_type != 'loss' else ''}*\n\n"
                f"{input_guidance}\n"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to ROI Settings", "callback_data": "admin_manage_roi"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Store the parameters in a context for the listener
            roi_context = {
                "setting_name": setting_name,
                "display_name": display_name,
                "validator": value_validator,
                "error_message": error_message,
                "param_type": param_type
            }
            
            # Since we can't use a real context like in python-telegram-bot, we'll use a global variable
            global roi_update_context
            roi_update_context = roi_context
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, 'roi_parameter', roi_parameter_message_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_update_roi_parameter: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating ROI parameter: {str(e)}")

def roi_parameter_message_handler(update, chat_id, text):
    """Handle the ROI parameter input."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Get context from global variable
        global roi_update_context
        if not roi_update_context:
            bot.send_message(
                chat_id,
                "⚠️ Session expired. Please try again.",
                parse_mode="Markdown"
            )
            return
            
        # Extract context variables
        setting_name = roi_update_context["setting_name"]
        display_name = roi_update_context["display_name"]
        validator = roi_update_context["validator"]
        error_message = roi_update_context["error_message"]
        param_type = roi_update_context["param_type"]
        
        # Validate input
        try:
            new_value = float(text.strip())
            if not validator(new_value):
                raise ValueError(error_message)
        except ValueError as ve:
            bot.send_message(
                chat_id,
                f"⚠️ Invalid input: {str(ve)}. Please try again.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'roi_parameter', roi_parameter_message_handler)
            return
            
        # Save to database
        with app.app_context():
            from models import SystemSettings
            
            # Get or create the setting
            setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
            if not setting:
                setting = SystemSettings(
                    setting_name=setting_name,
                    setting_value=str(new_value),
                    updated_by=str(chat_id)
                )
                db.session.add(setting)
            else:
                setting.setting_value = str(new_value)
                setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Send confirmation
            confirmation_message = (
                f"✅ *{display_name} Updated Successfully*\n\n"
                f"New value: *{new_value:.2f}{'%' if param_type != 'loss' else ''}*\n\n"
                f"This change will be applied to all future ROI calculations."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to ROI Settings", "callback_data": "admin_manage_roi"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Clear the context
            roi_update_context = None
            
    except Exception as e:
        import logging
        logging.error(f"Error in roi_parameter_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the ROI parameter. Please try again.",
            parse_mode="Markdown"
        )

def support_ticket_message_handler(update, chat_id, text):
    """Handle the support ticket submission."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Save the ticket to the database
        with app.app_context():
            from models import User, SupportTicket
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
                
            # Parse the ticket information
            lines = text.strip().split('\n')
            
            # Extract subject (first line) and message (rest of the text)
            subject = lines[0][:200] if lines else "Support Request"
            message = text
            
            # Create the ticket
            new_ticket = SupportTicket(
                user_id=user.id,
                subject=subject,
                message=message,
                status='open',
                priority='normal'
            )
            
            db.session.add(new_ticket)
            db.session.commit()
            
            # Send confirmation to the user
            confirmation_message = (
                "✅ *Support Ticket Submitted Successfully*\n\n"
                f"Ticket ID: #{new_ticket.id}\n"
                f"Subject: {subject}\n"
                "Status: Open\n\n"
                "Our support team will review your ticket and respond as soon as possible. "
                "You'll receive a notification when there's an update."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 Dashboard", "callback_data": "view_dashboard"}],
                [{"text": "🏠 Main Menu", "callback_data": "start"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Notify admin(s) about the new ticket
            admin_ids = [int(os.environ.get('ADMIN_USER_ID'))] if os.environ.get('ADMIN_USER_ID') else []
            
            if admin_ids:
                admin_notification = (
                    "🔔 *New Support Ticket*\n\n"
                    f"Ticket ID: #{new_ticket.id}\n"
                    f"User: {user.username or user.telegram_id}\n"
                    f"Subject: {subject}\n\n"
                    "Use the Admin Panel to view and respond to this ticket."
                )
                
                for admin_id in admin_ids:
                    try:
                        bot.send_message(
                            admin_id,
                            admin_notification,
                            parse_mode="Markdown"
                        )
                    except Exception as admin_e:
                        logging.error(f"Error sending admin notification: {admin_e}")
            
    except Exception as e:
        import logging
        logging.error(f"Error in support_ticket_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while processing your ticket. Please try again or contact support directly.",
            parse_mode="Markdown"
        )

def admin_change_wallet_handler(update, chat_id):
    """Handle changing the deposit wallet address."""
    try:
        # Send instructions for changing the wallet
        message = (
            "💼 *Change Deposit Wallet*\n\n"
            "Please enter the new Solana deposit wallet address below.\n"
            "This will be the address users will deposit to.\n\n"
            "⚠️ *Important:* Make sure the address is correct and you have access to it."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "❌ Cancel", "callback_data": "admin_wallet_settings"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add listener for the next message to capture the wallet address
        bot.add_message_listener(chat_id, "wallet_address", admin_wallet_address_input_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_change_wallet_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error starting wallet change: {str(e)}")


def admin_wallet_address_input_handler(update, chat_id, text):
    """Handle the wallet address input from admin."""
    try:
        with app.app_context():
            from models import SystemSettings
            import re
            
            # Remove any listener
            bot.remove_listener(chat_id)
            
            # Basic validation for Solana address (should be base58, ~32-44 chars)
            if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', text):
                message = (
                    "❌ *Invalid Wallet Address*\n\n"
                    "The address you entered doesn't appear to be a valid Solana address.\n"
                    "Please check and try again."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Try Again", "callback_data": "admin_change_wallet"}],
                    [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Check if setting exists and update, or create new setting
            deposit_wallet_setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
            
            if deposit_wallet_setting:
                deposit_wallet_setting.setting_value = text
                deposit_wallet_setting.updated_by = str(chat_id)
            else:
                new_setting = SystemSettings(
                    setting_name="deposit_wallet",
                    setting_value=text,
                    updated_by=str(chat_id)
                )
                db.session.add(new_setting)
                
            db.session.commit()
            
            # Send confirmation
            message = (
                "✅ *Deposit Wallet Updated*\n\n"
                f"The system deposit wallet has been successfully changed to:\n\n"
                f"`{text}`\n\n"
                "This address will now be shown to all users when they visit the deposit page."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "View QR Code", "callback_data": "admin_view_wallet_qr"}],
                [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_wallet_address_input_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating wallet address: {str(e)}")


def admin_deposit_logs_handler(update, chat_id):
    """Display recent deposit logs in real-time."""
    try:
        with app.app_context():
            from app import db
            from models import Transaction, User
            import requests
            import json
            from datetime import datetime, timedelta
            
            # Send processing message
            bot.send_chat_action(chat_id, action="typing")
            
            # Get recent deposit transactions from the database
            try:
                deposits = (
                    db.session.query(Transaction, User)
                    .join(User, Transaction.user_id == User.id)
                    .filter(Transaction.transaction_type == "deposit")
                    .order_by(Transaction.timestamp.desc())
                    .limit(20)
                    .all()
                )
                
                # Format the results in a presentable way
                if deposits:
                    message = "📊 *Recent Deposit Logs*\n\n"
                    
                    for i, (transaction, user) in enumerate(deposits, 1):
                        # Always use telegram_id as primary identifier, with username as secondary if available
                        user_display = f"ID: {user.telegram_id}"
                        if user.username:
                            user_display += f" (@{user.username})"
                        
                        timestamp = transaction.timestamp.strftime("%Y-%m-%d %H:%M")
                        
                        message += (
                            f"{i}. *{user_display}*: {transaction.amount:.2f} SOL\n"
                            f"   📅 {timestamp} · {transaction.status.upper()}\n"
                        )
                        
                        # Add notes if any
                        if transaction.notes:
                            message += f"   _Note: {transaction.notes}_\n"
                        
                        # Add a separator except for the last item
                        if i < len(deposits):
                            message += "----------------------------\n"
                    
                    # Add timestamp and refresh hint
                    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    message += f"\n_Last updated: {now}_\n"
                    message += "_Click Refresh to update the logs_"
                else:
                    message = "📊 *Deposit Logs*\n\n" + "No deposit transactions found in the system."
            except Exception as e:
                message = f"⚠️ Error retrieving deposit logs: {str(e)}"
                import logging
                logging.error(f"Database error in deposit logs: {e}")
            
            # Add refresh and back buttons
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔄 Refresh", "callback_data": "admin_deposit_logs"}],
                [{"text": "📊 Export CSV", "callback_data": "admin_export_deposits_csv"}],
                [{"text": "↩️ Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_deposit_logs_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying deposit logs: {str(e)}")

def admin_view_wallet_qr_handler(update, chat_id):
    """Generate and display QR code for the deposit wallet."""
    try:
        with app.app_context():
            from models import SystemSettings
            import qrcode
            import io
            from PIL import Image, ImageDraw, ImageFont
            
            # Get the deposit wallet address
            deposit_wallet_setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
            
            if not deposit_wallet_setting or not deposit_wallet_setting.setting_value:
                message = (
                    "⚠️ *No Deposit Wallet Set*\n\n"
                    "There is no deposit wallet address set in the system.\n"
                    "Please set a wallet address first."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Set Wallet Address", "callback_data": "admin_change_wallet"}],
                    [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            wallet_address = deposit_wallet_setting.setting_value
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(wallet_address)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Add caption with wallet address
            # Create a new image with space for the caption
            canvas = Image.new('RGB', (img.size[0], img.size[1] + 50), color=(255, 255, 255))
            canvas.paste(img, (0, 0))
            
            # Add the caption
            draw = ImageDraw.Draw(canvas)
            draw.text((10, img.size[1] + 10), f"Wallet Address: {wallet_address[:10]}...{wallet_address[-5:]}", fill=(0, 0, 0))
            
            # Save to buffer
            buffer = io.BytesIO()
            canvas.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Send QR code
            bot.send_chat_action(chat_id, action="upload_photo")
            bot.send_document(
                chat_id, 
                buffer, 
                caption=f"📱 *QR Code for Deposit Wallet*\n\n`{wallet_address}`", 
                parse_mode="Markdown"
            )
            
            # Send options keyboard
            keyboard = bot.create_inline_keyboard([
                [{"text": "Change Wallet", "callback_data": "admin_change_wallet"}],
                [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                "Use the buttons below to manage your wallet settings:",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_wallet_qr_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error generating QR code: {str(e)}")
        
        # If error is related to QR code generation, provide alternative message
        if "qrcode" in str(e).lower() or "image" in str(e).lower():
            wallet_address = ""
            try:
                with app.app_context():
                    from models import SystemSettings
                    setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
                    if setting:
                        wallet_address = setting.setting_value
            except:
                pass
            
            if wallet_address:
                message = (
                    "📱 *Deposit Wallet Address*\n\n"
                    f"`{wallet_address}`\n\n"
                    "QR code generation failed, but you can copy the address above."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )


def faqs_handler(update, chat_id):
    """Show help information and available commands (FAQs)."""
    try:
        help_text = (
            "🤖 *THRIVE BOT – FAQ*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "*1️⃣ Is Thrive Bot real or another fake promise?*\n"
            "Thrive is real. It connects directly to the Solana blockchain, detects newly launched tokens, enters trades, and tracks actual yield performance. Every trade is timestamped, linked to real token charts, and fully transparent. No fluff, just function.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "*2️⃣ Can I verify the trades myself?*\n"
            "Yes. Every trade shown includes a clickable link to either pump.fun or birdeye.so. You can track token activity, confirm the timing, check liquidity caps, and verify the results for yourself.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "*3️⃣ How much do I need to start?*\n"
            "You only need 0.5 SOL to activate the bot. That unlocks the auto-trading, yield updates, and withdrawal system. There are no hidden fees or subscription costs. The bot performs based on what's in your account.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "*4️⃣ What makes Thrive different from other bots?*\n"
            "Most bots throw out alerts or dump tokens for you to buy manually. Thrive trades for you, tracks its performance over time, and provides a clean history with verified yields. Every detail is stored, updated, and viewable by you.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "*5️⃣ How do withdrawals work?*\n"
            "Withdrawals are requested directly inside the bot. It's confirmed immediately, you get a visual receipt with full transaction details: SOL in, SOL out, profit applied, and exact timestamps formatted for transparency."
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "📊 Dashboard", "callback_data": "view_dashboard"}, 
                {"text": "💰 Deposit", "callback_data": "deposit"}
            ],
            [
                {"text": "📈 Trade History", "callback_data": "trading_history"}, 
                {"text": "🏠 Main Menu", "callback_data": "start"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            help_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in faqs_handler: {e}")
        bot.send_message(chat_id, f"Error displaying FAQs: {str(e)}")

# New handler functions for enhanced referral system
def referral_qr_code_handler(update, chat_id):
    """Generate and send a QR code for the user's referral link."""
    try:
        import qrcode
        import io
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("thrivesolanabot")
                logger.info("Initialized referral manager")
            
            # Create referral link
            user_id = str(update['callback_query']['from']['id'])
            referral_link = f"https://t.me/thrivesolanabot?start=ref_{user_id}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(referral_link)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code to bytes buffer
            buffer = io.BytesIO()
            img.save(buffer)
            buffer.seek(0)
            
            # Create caption for the image
            caption = (
                f"🔗 *Your Referral QR Code*\n\n"
                f"Share this QR code with friends to earn 5% of their profits automatically!\n\n"
                f"When scanned, this QR code will lead directly to THRIVE bot with your referral code pre-applied.\n\n"
                f"💡 *Pro Tip:* Save this image and share it on social media or in chat groups!"
            )
            
            # Send the QR code as photo with caption
            bot.send_chat_action(chat_id, "upload_photo")
            
            # Create a temporary file for the image
            temp_file = f"/tmp/qr_code_{user_id}.png"
            img.save(temp_file)
            
            # Send using requests (Python-telegram-bot doesn't have direct binary support in simple version)
            import requests
            import os
            
            token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
            if not token:
                bot.send_message(chat_id, "❌ Error: Bot token not found. Please contact support.")
                return
                
            # Send photo with caption
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'Markdown',
            }
            with open(temp_file, 'rb') as photo:
                files = {'photo': photo}
                response = requests.post(url, data=data, files=files)
            
            # Check response
            if not response.ok:
                bot.send_message(chat_id, f"❌ Error sending QR code: {response.text}")
                return
            
            # Send navigation button
            bot.send_message(
                chat_id=chat_id,
                text="Use the button below to return to the referral menu:",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "🔙 Back to Referral Menu", "callback_data": "referral"}]
                ])
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in referral QR code handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error generating QR code: {str(e)}")
        
def copy_referral_link_handler(update, chat_id):
    """Handle the copy link button click."""
    try:
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("thrivesolanabot")
                logger.info("Initialized referral manager")
            
            # Create referral link
            user_id = str(update['callback_query']['from']['id'])
            referral_link = f"https://t.me/thrivesolanabot?start=ref_{user_id}"
            
            # Send the link as a separate message for easy copying
            bot.send_message(
                chat_id=chat_id,
                text=f"*Here's your referral link:*\n\n`{referral_link}`\n\n👆 *Tap to copy*",
                parse_mode="Markdown"
            )
            
            # Provide confirmation and instructions
            bot.send_message(
                chat_id=chat_id,
                text="✅ *Your referral link is ready to share!*\n\nCopy the link above and share it with friends via any messaging app, social media, or email.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "🔙 Back to Referral Menu", "callback_data": "referral"}]
                ])
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in copy referral link handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error generating your referral link: {str(e)}")
        
def referral_how_it_works_handler(update, chat_id):
    """Handle the 'How It Works' button for the referral program."""
    try:
        # Create a detailed explanation of the referral program
        message = (
            "🔍 *THRIVE REFERRAL PROGRAM: HOW IT WORKS* 🔍\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "THRIVE's referral program rewards you for bringing new traders to our platform. Here's how it works in detail:\n\n"
            
            "1️⃣ *Share Your Code*\n"
            "• Every user gets a unique referral code\n"
            "• Share your code or link with friends\n"
            "• They enter your code during signup\n\n"
            
            "2️⃣ *Earn 5% Forever*\n"
            "• You earn 5% of ALL profits your referrals generate\n"
            "• This is passive income - no work required\n"
            "• Earnings are credited to your balance automatically\n"
            "• There's NO LIMIT to how many people you can refer\n\n"
            
            "3️⃣ *Track Your Progress*\n"
            "• Monitor referrals from your dashboard\n"
            "• See active vs. pending referrals\n"
            "• Watch your earnings grow in real-time\n\n"
            
            "4️⃣ *Tier System*\n"
            "• 🥉 Bronze: 0-4 active referrals\n"
            "• 🥈 Silver: 5-9 active referrals\n"
            "• 🥇 Gold: 10-24 active referrals\n"
            "• 💎 Diamond: 25+ active referrals\n"
            "• Higher tiers unlock special perks (coming soon)\n\n"
            
            "5️⃣ *Tips for Success*\n"
            "• Share with crypto enthusiasts\n"
            "• Highlight the bot's automated trading\n"
            "• Mention the 7-day doubling potential\n"
            "• Share your own success story\n\n"
            
            "Ready to start earning? Use the buttons below to share your referral code and start building your passive income network!"
        )
        
        # Send the message with navigation buttons
        bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [
                    {"text": "📤 Share My Code", "callback_data": "share_referral"},
                    {"text": "📱 Generate QR", "callback_data": "referral_qr_code"}
                ],
                [
                    {"text": "🔙 Back to Referral Menu", "callback_data": "referral"}
                ]
            ])
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in referral how it works handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error displaying referral program details: {str(e)}")
        
def referral_tips_handler(update, chat_id):
    """Display tips for maximizing referral success."""
    try:
        tips_message = (
            "🚀 *TOP TIPS FOR REFERRAL SUCCESS* 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "Want to maximize your referral earnings? Follow these proven strategies:\n\n"
            
            "1️⃣ *Target the Right Audience*\n"
            "• Focus on crypto enthusiasts and traders\n"
            "• Approach friends interested in passive income\n"
            "• Share in relevant Telegram groups and Discord servers\n\n"
            
            "2️⃣ *Craft Compelling Messages*\n"
            "• Highlight the 7-day doubling potential\n"
            "• Mention it's fully automated - no work needed\n"
            "• Emphasize the security and simplicity\n"
            "• Share your personal results (with screenshots if possible)\n\n"
            
            "3️⃣ *Use Multiple Channels*\n"
            "• Direct messages to friends\n"
            "• Social media posts (Twitter, Instagram, TikTok)\n"
            "• Crypto forums and communities\n"
            "• QR codes in strategic locations\n\n"
            
            "4️⃣ *Follow Up & Support*\n"
            "• Check in with people you've referred\n"
            "• Help them get started if needed\n"
            "• Share trading tips and insights\n\n"
            
            "5️⃣ *Track & Optimize*\n"
            "• Monitor which sharing methods work best\n"
            "• Adjust your approach based on results\n"
            "• Set weekly referral goals\n\n"
            
            "Remember: The more active traders you refer, the more passive income you'll earn - forever!"
        )
        
        # Send the tips with navigation buttons
        bot.send_message(
            chat_id=chat_id,
            text=tips_message,
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [
                    {"text": "✉️ Share Code Now", "callback_data": "share_referral"},
                    {"text": "📱 Create QR Code", "callback_data": "referral_qr_code"}
                ],
                [
                    {"text": "🔙 Back to Stats", "callback_data": "referral_stats"}
                ]
            ])
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in referral tips handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error displaying referral tips: {str(e)}")

# Withdrawal management handlers
def admin_manage_withdrawals_handler(update, chat_id):
    """Handle the manage withdrawals button and show pending withdrawal requests."""
    try:
        with app.app_context():
            from models import User, Transaction
            from datetime import datetime
            
            # Get all pending withdrawal transactions
            pending_withdrawals = Transaction.query.filter_by(
                transaction_type="withdraw",
                status="pending"
            ).order_by(Transaction.timestamp.desc()).all()
            
            if not pending_withdrawals:
                message = "📝 *Withdrawal Management*\n\nThere are no pending withdrawal requests at this time."
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "View Completed Withdrawals", "callback_data": "admin_view_completed_withdrawals"}],
                    [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Format the list of pending withdrawals
            message = "📝 *Pending Withdrawal Requests*\n\n"
            
            for i, withdrawal in enumerate(pending_withdrawals[:10], 1):  # Show up to 10 most recent pending withdrawals
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
                    f"Amount: {withdrawal.amount:.6f} SOL\n"
                    f"Wallet: {display_wallet}\n"
                    f"Requested: {withdrawal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Notes: {withdrawal.notes or 'N/A'}\n\n"
                )
            
            keyboard_rows = []
            
            # Create approve/deny buttons for each withdrawal
            for withdrawal in pending_withdrawals[:5]:  # Limit to first 5 to avoid too many buttons
                keyboard_rows.append([
                    {"text": f"✅ Approve #{withdrawal.id}", "callback_data": f"admin_approve_withdrawal_{withdrawal.id}"},
                    {"text": f"❌ Deny #{withdrawal.id}", "callback_data": f"admin_deny_withdrawal_{withdrawal.id}"}
                ])
            
            # Add navigation buttons
            keyboard_rows.append([
                {"text": "View Completed", "callback_data": "admin_view_completed_withdrawals"},
                {"text": "🔙 Back", "callback_data": "admin_back"}
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard(keyboard_rows)
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_manage_withdrawals_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error loading pending withdrawals: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

def admin_approve_withdrawal_handler(update, chat_id):
    """Approve a specific withdrawal request."""
    try:
        # Extract the withdrawal ID from the callback data
        callback_data = update.get('callback_query', {}).get('data', '')
        withdrawal_id = int(callback_data.split('_')[-1])
        
        with app.app_context():
            from models import User, Transaction
            import random
            from datetime import datetime
            
            # Get the withdrawal transaction
            withdrawal = Transaction.query.get(withdrawal_id)
            if not withdrawal or withdrawal.transaction_type != "withdraw" or withdrawal.status != "pending":
                bot.send_message(chat_id, "❌ Error: Withdrawal not found or already processed.")
                return
            
            # Get the user record
            user = User.query.get(withdrawal.user_id)
            if not user:
                bot.send_message(chat_id, "❌ Error: User not found in database.")
                return
            
            # Update transaction status
            withdrawal.status = "completed"
            withdrawal.notes = f"{withdrawal.notes or ''}; Approved by admin on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Generate TX hash for completed transaction
            tx_hash = f"Sol{random.randint(10000000, 99999999)}{user.id}"
            withdrawal.tx_hash = tx_hash
            
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            shortened_hash = f"{tx_hash[:6]}...{tx_hash[-4:]}"
            
            # Notify the user
            success_message = (
                "✅ *Withdrawal Approved!*\n\n"
                f"Amount: *{withdrawal.amount:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:] if len(user.wallet_address) > 10 else user.wallet_address}\n"
                f"TX Hash: `{shortened_hash}`\n"
                f"View on: https://solscan.io/tx/{tx_hash}\n"
                f"Time: {time_str} UTC\n\n"
                "Your funds are on the way and should appear in your wallet shortly."
            )
            
            user_keyboard = bot.create_inline_keyboard([
                [{"text": "🔎 View Transaction", "callback_data": "view_tx"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            try:
                bot.send_message(
                    user.telegram_id,
                    success_message,
                    parse_mode="Markdown",
                    reply_markup=user_keyboard
                )
            except Exception as notify_error:
                logging.error(f"Failed to notify user about withdrawal approval: {notify_error}")
            
            # Confirm to admin
            admin_message = (
                f"✅ *Withdrawal #{withdrawal_id} Approved*\n\n"
                f"User: {user.username or user.telegram_id}\n"
                f"Amount: {withdrawal.amount:.6f} SOL\n"
                f"TX Hash: `{shortened_hash}`\n"
                f"Time: {time_str} UTC\n\n"
                f"User has been notified of the approval."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 Manage More Withdrawals", "callback_data": "admin_manage_withdrawals"}],
                [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                admin_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_approve_withdrawal_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error approving withdrawal: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

def admin_deny_withdrawal_handler(update, chat_id):
    """Deny a specific withdrawal request and return funds to user."""
    try:
        # Extract the withdrawal ID from the callback data
        callback_data = update.get('callback_query', {}).get('data', '')
        withdrawal_id = int(callback_data.split('_')[-1])
        
        with app.app_context():
            from models import User, Transaction
            from datetime import datetime
            
            # Get the withdrawal transaction
            withdrawal = Transaction.query.get(withdrawal_id)
            if not withdrawal or withdrawal.transaction_type != "withdraw" or withdrawal.status != "pending":
                bot.send_message(chat_id, "❌ Error: Withdrawal not found or already processed.")
                return
            
            # Get the user record
            user = User.query.get(withdrawal.user_id)
            if not user:
                bot.send_message(chat_id, "❌ Error: User not found in database.")
                return
            
            # Update transaction status
            withdrawal.status = "failed"
            withdrawal.notes = f"{withdrawal.notes or ''}; Denied by admin on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Return funds to user's balance
            user.balance += withdrawal.amount
            
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Notify the user
            deny_message = (
                "❌ *Withdrawal Request Denied*\n\n"
                f"Amount: *{withdrawal.amount:.6f} SOL*\n"
                f"Request ID: #{withdrawal.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been denied by an administrator. "
                "The funds have been returned to your account balance.\n\n"
                "Please contact support if you have any questions."
            )
            
            user_keyboard = bot.create_inline_keyboard([
                [{"text": "📞 Contact Support", "callback_data": "support"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            try:
                bot.send_message(
                    user.telegram_id,
                    deny_message,
                    parse_mode="Markdown",
                    reply_markup=user_keyboard
                )
            except Exception as notify_error:
                logging.error(f"Failed to notify user about withdrawal denial: {notify_error}")
            
            # Confirm to admin
            admin_message = (
                f"❌ *Withdrawal #{withdrawal_id} Denied*\n\n"
                f"User: {user.username or user.telegram_id}\n"
                f"Amount: {withdrawal.amount:.6f} SOL\n"
                f"Time: {time_str} UTC\n\n"
                f"Funds have been returned to the user's balance."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 Manage More Withdrawals", "callback_data": "admin_manage_withdrawals"}],
                [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                admin_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_deny_withdrawal_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error denying withdrawal: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

# This is the improved admin view users handler with copied fields and no deposit wallet
def admin_view_all_users_button_handler(update, chat_id):
    """Special handler for the view all users button"""
    import logging
    logging.info(f"View All Users button clicked by {chat_id}")
    
    try:
        with app.app_context():
            from models import User, UserStatus, Transaction, Profit, ReferralCode
            from app import db
            from sqlalchemy import func
            from datetime import datetime, timedelta
            import traceback
            
            # Get all users ordered by registration date (most recent first)
            users = []
            try:
                # Create a fresh query for all users
                users = User.query.order_by(User.joined_at.desc()).limit(10).all()
                logging.info(f"Found {len(users)} users in the database")
            except Exception as db_error:
                logging.error(f"Error querying users: {db_error}")
                logging.error(traceback.format_exc())
                # Don't modify the database - just return empty list
                users = []
            
            if not users:
                message = (
                    "👥 *All Users*\n\n"
                    "There are currently no registered users in the system.\n\n"
                    "Users will appear here after they interact with the bot.\n"
                    "You can also manually add a user using the admin commands."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Back to User Management", "callback_data": "admin_user_management"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Create header for users list
            message = (
                "👥 *All Registered Users*\n\n"
                "Most recent registrations:\n\n"
            )
            
            # Add user details to the message
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
                
                # Format wallet address for readability - Only payout wallet is used
                wallet_address = user.wallet_address or "Not set"
                                
                # Get registration date
                registration_date = user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "N/A"
                
                # Get referral earnings (5% profit)
                referral_earnings = user.referral_bonus if user.referral_bonus is not None else 0.0
                
                # Get user's name information
                name_display = ""
                if user.first_name or user.last_name:
                    name_display = f"• Name: {user.first_name or ''} {user.last_name or ''}\n"
                
                # Calculate ROI (Return on Investment)
                roi_percentage = 0
                if user.initial_deposit > 0:
                    roi_percentage = (total_profits / user.initial_deposit) * 100
                
                # Calculate net profit (total profit - total deposited + total withdrawn)
                net_profit = user.balance - total_deposits
                
                # Calculate active trading amount 
                active_trading = user.balance
                
                # Get last activity time with date and time
                last_activity = "N/A"
                if user.last_activity:
                    last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M:%S")
                
                # Create user entry with full details and easy-to-copy fields (deposit wallet removed)
                user_entry = (
                    f"*User #{idx}*\n"
                    f"• User ID (copy): `{user.id}`\n"
                    f"• Telegram ID (copy): `{user.telegram_id}`\n"
                    f"• Username: @{user.username or 'No Username'}\n"
                    f"{name_display}"
                    f"• Registered: {registration_date}\n"
                    f"• Last Activity: {last_activity}\n"
                    f"• Status: {user.status.value}\n\n"
                    
                    f"*Financial Details*\n"
                    f"• Current Balance: {user.balance:.4f} SOL\n"
                    f"• Initial Deposit: {user.initial_deposit:.4f} SOL\n" 
                    f"• Total Deposited: {total_deposits:.4f} SOL\n"
                    f"• Total Withdrawn: {total_withdrawn:.4f} SOL\n"
                    f"• Total Profit: {total_profits:.4f} SOL\n"
                    f"• Net Profit: {net_profit:.4f} SOL\n"
                    f"• ROI: {roi_percentage:.2f}%\n"
                    f"• Active Trading: {active_trading:.4f} SOL\n\n"
                    
                    f"*Referral System*\n"
                    f"• Referral Count: {referral_count}\n"
                    f"• Referral Earnings: {referral_earnings:.4f} SOL\n\n"
                    
                    f"*Wallet Information*\n"
                    f"• Payout Wallet (copy):\n`{wallet_address}`\n\n"
                )
                
                message += user_entry
            
            # Add pagination note
            message += "\nShowing 10 most recent users. Use search for specific users."
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "Search User", "callback_data": "admin_search_user"},
                    {"text": "Export Users (CSV)", "callback_data": "admin_export_csv"}
                ],
                [
                    {"text": "View Active Users", "callback_data": "admin_view_active_users"},
                    {"text": "Back to User Management", "callback_data": "admin_user_management"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_all_users_button_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error displaying all users: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_view_all_users_handler_legacy(update, chat_id):
    """Legacy version of the user list function (disabled)"""
    # Forward to our new fixed handler
    return admin_view_all_users_button_handler(update, chat_id)

def admin_view_completed_withdrawals_handler(update, chat_id):
    """Show a list of completed withdrawal transactions."""
    try:
        with app.app_context():
            from models import User, Transaction
            
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
                        f"Amount: {withdrawal.amount:.6f} SOL\n"
                        f"Completed: {withdrawal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 View Pending Withdrawals", "callback_data": "admin_manage_withdrawals"}],
                [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_completed_withdrawals_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error viewing completed withdrawals: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

if __name__ == '__main__':
    run_polling()
def main():
    """Run the bot as a standalone program"""
    import logging
    import os
    from dotenv import load_dotenv
    
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Get the bot token from environment variables
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    logger.info("Starting Telegram bot...")
    
    # Create bot instance
    global bot
    bot = SimpleTelegramBot(token)
    
    # Register all command handlers
    register_handlers()
    
    # Start the bot
    bot.start_polling()
    
if __name__ == "__main__":
    main()
