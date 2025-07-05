#!/usr/bin/env python
"""
Telegram Bot Runner - Environment-Aware Startup
===============================================
This script implements a dual startup system:
1. AWS: Manual execution with .env loading via `python bot_v20_runner.py`
2. Replit: Auto-start when remixed (handled by main.py)

The bot detects the environment and loads configuration accordingly.
"""
import logging
import os
import sys
import requests
import time
import json
import random
import tempfile
import traceback
from datetime import datetime, timedelta
from threading import Thread

# Environment detection and .env loading
def setup_environment():
    """Setup environment variables based on execution context with enhanced detection"""
    
    # Import environment detector
    from environment_detector import get_environment_info, is_direct_execution, is_aws_environment
    
    # Get comprehensive environment info
    env_info = get_environment_info()
    
    # Configure logging based on environment
    logging.basicConfig(
        format=f'%(asctime)s [{env_info["environment_type"].upper()}] %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    logger = logging.getLogger(__name__)
    
    # Load .env file only for AWS/production environments
    if env_info["environment_type"] == "aws" or env_info["env_file_exists"]:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✅ AWS Environment: Loaded .env file successfully")
        except ImportError:
            logger.warning("⚠️  python-dotenv not installed, install with: pip install python-dotenv")
        except Exception as e:
            logger.error(f"❌ Error loading .env file: {e}")
    elif env_info["environment_type"] == "replit":
        logger.info("🎯 Replit Environment: Using Replit's built-in environment variables")
    else:
        logger.info("💻 Local Environment: Using system environment variables")
    
    # Log startup mode
    if env_info["is_direct_execution"]:
        logger.info("🚀 Direct Execution Mode: Bot started via 'python bot_v20_runner.py'")
    else:
        logger.info("📦 Import Mode: Bot imported by another module (main.py)")
    
    return env_info

# Setup environment before other imports
env_info = setup_environment()

from config import BOT_TOKEN, MIN_DEPOSIT

# Import enhanced duplicate handler
from duplicate_fix import enhanced_duplicate_manager as duplicate_manager
from graceful_duplicate_handler import handle_telegram_api_error, safe_telegram_request, safe_methods

# Import Flask app context
from app import app, db
from models import User, UserStatus, Profit, Transaction, TradingPosition, ReferralCode, CycleStatus, BroadcastMessage, AdminMessage

# Import smart balance allocation system
from smart_balance_allocator import process_smart_buy_broadcast, process_smart_sell_broadcast

# Import price fetcher for real-time USD conversion
from utils.price_fetcher import format_balance_with_usd, sol_to_usd, get_sol_price_usd, get_price_change_indicator

# Global bot instance management
_bot_instance = None
_bot_running = False

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
        self._processed_messages = set()  # Cache for processed message IDs
        self._processed_callbacks = set()  # Cache for processed callback query IDs
        self._recent_callbacks = {}  # Track recent callbacks for duplicate prevention
        self.offset = 0
        self.handlers = {}
        self.user_states = {}  # Track conversation states for each user
        self.wallet_listeners = {}  # Users waiting to provide a wallet
        # Clear any existing offset to start fresh
        self.clear_pending_updates()
        logger.info(f"Bot initialized with token ending in ...{self.token[-5:]}")
    
    def clear_pending_updates(self):
        """Clear any pending updates and webhooks to start fresh."""
        try:
            # First, remove any existing webhook
            webhook_response = requests.post(f"{self.api_url}/deleteWebhook")
            if webhook_response.status_code == 200:
                logger.info("Webhook removed successfully")
            
            # Get and discard all pending updates
            response = requests.get(f"{self.api_url}/getUpdates?offset=-1")
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    last_update_id = data['result'][-1]['update_id']
                    # Clear all updates up to this point
                    requests.get(f"{self.api_url}/getUpdates?offset={last_update_id + 1}")
                    logger.info("Cleared pending updates")
        except Exception as e:
            logger.warning(f"Could not clear pending updates: {e}")
    
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
        # Remove existing listener if exists to prevent duplicates
        if chat_id in self.wallet_listeners:
            logger.debug(f"Replacing existing listener for chat {chat_id}")
        self.wallet_listeners[chat_id] = (listener_type, callback)
        logger.info(f"Added {listener_type} listener for chat {chat_id}")
    
    def remove_listener(self, chat_id):
        """Remove a listener for a chat."""
        if chat_id in self.wallet_listeners:
            del self.wallet_listeners[chat_id]
            logger.info(f"Removed listener for chat {chat_id}")
    
    def send_message(self, chat_id, text, parse_mode="Markdown", reply_markup=None, disable_web_page_preview=False):
        """Send a message to a chat with graceful error handling."""
        payload = {
            'chat_id': chat_id,
            'text': text
        }
        
        if parse_mode:
            payload['parse_mode'] = parse_mode
        
        if reply_markup:
            payload['reply_markup'] = reply_markup
            
        if disable_web_page_preview:
            payload['disable_web_page_preview'] = True
            
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            
            # Handle HTTP 409 errors gracefully
            if response.status_code == 409:
                logger.debug(f"HTTP 409 for message to {chat_id} - treating as success")
                return {"ok": True, "result": {"message_id": 0, "duplicate_handled": True}}
            elif response.status_code == 429:
                logger.warning(f"Rate limited for message to {chat_id} - backing off")
                time.sleep(1)
                return {"ok": False, "error": "Rate limited"}
            elif response.status_code != 200:
                error_details = ""
                try:
                    error_json = response.json()
                    error_details = f" - {error_json.get('description', 'No details')}"
                except:
                    error_details = f" - Response: {response.text[:200]}"
                logger.error(f"HTTP {response.status_code} for message to {chat_id}{error_details}")
                return {"ok": False, "error": f"HTTP {response.status_code}", "details": error_details}
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return {"ok": False, "error": str(e)}
    
    def edit_message(self, message_id, chat_id, text, parse_mode="Markdown", reply_markup=None, disable_web_page_preview=False):
        """Edit an existing message with graceful error handling."""
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup:
            payload['reply_markup'] = reply_markup
            
        if disable_web_page_preview:
            payload['disable_web_page_preview'] = True
            
        try:
            response = requests.post(
                f"{self.api_url}/editMessageText",
                json=payload,
                timeout=10
            )
            
            # Handle HTTP 409 errors gracefully
            if response.status_code == 409:
                logger.debug(f"HTTP 409 for edit message {message_id} in chat {chat_id} - treating as success")
                return {"ok": True, "result": {"message_id": message_id, "duplicate_handled": True}}
            elif response.status_code == 429:
                logger.warning(f"Rate limited for edit message {message_id} in chat {chat_id}")
                time.sleep(1)
                return {"ok": False, "error": "Rate limited"}
            elif response.status_code != 200:
                logger.error(f"HTTP {response.status_code} for edit message {message_id} in chat {chat_id}")
                return {"ok": False, "error": f"HTTP {response.status_code}"}
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error editing message {message_id} in chat {chat_id}: {e}")
            return {"ok": False, "error": str(e)}
        
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
        """Get updates from Telegram API with aggressive duplicate prevention."""
        try:
            response = requests.get(
                f"{self.api_url}/getUpdates",
                params={
                    'offset': self.offset,
                    'timeout': 30,  # Optimized long polling
                    'limit': 50,   # Reduced limit for better control
                    'allowed_updates': ['message', 'callback_query']  # Only needed types
                },
                timeout=35  # 5 seconds read latency
            )
            
            # Handle HTTP 409 errors gracefully
            if response.status_code == 409:
                logger.debug("HTTP 409 (Conflict) from Telegram API - handling gracefully")
                time.sleep(0.5)  # Brief pause to avoid rapid retries
                return []
            elif response.status_code == 429:
                logger.warning("Rate limited by Telegram API - backing off")
                time.sleep(2)
                return []
            elif response.status_code != 200:
                logger.error(f"HTTP {response.status_code} from Telegram API")
                return []
                
            data = response.json()
            
            if not data.get('ok', False):
                logger.error(f"Telegram API error: {data}")
                return []
                
            updates = data.get('result', [])
            
            if updates:
                # Immediately update offset to acknowledge ALL received updates
                last_update_id = updates[-1]['update_id']
                self.offset = last_update_id + 1
                
                # Immediately confirm these updates are processed
                requests.get(f"{self.api_url}/getUpdates?offset={self.offset}&limit=1")
                
                logger.debug(f"Received {len(updates)} updates, confirmed offset: {self.offset}")
            
            return updates
            
        except requests.exceptions.Timeout:
            logger.debug("Polling timeout (normal)")
            return []
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []
    
    def create_inline_keyboard(self, buttons):
        """Create an inline keyboard."""
        return {
            'inline_keyboard': buttons
        }
    
    def process_update(self, update):
        """Process a single update with enhanced duplicate protection."""
        try:
            # Generate unique update ID for complete deduplication
            update_id = update.get('update_id')
            if not update_id:
                logger.warning("Received update without update_id")
                return
                
            # Simple but effective duplicate check using a set
            if update_id in self._processed_messages:
                logger.debug(f"Skipping already processed update {update_id}")
                return
                
            # Add to processed set immediately to prevent any duplicate processing
            self._processed_messages.add(update_id)
            
            # Clean old processed messages to prevent memory issues (keep last 1000)
            if len(self._processed_messages) > 1000:
                # Remove oldest half
                oldest_messages = sorted(self._processed_messages)[:500]
                for old_id in oldest_messages:
                    self._processed_messages.discard(old_id)
            
            # Log that we're processing this update
            logger.info(f"Processing update {update_id}")
            
            # Handle callback queries
            if "callback_query" in update:
                callback_id = update["callback_query"]["id"]
                user_id = update["callback_query"]["from"]["id"]
                
                # Simple rate limiting - prevent rapid clicking
                if duplicate_manager.is_rate_limited(user_id, "callback", 0.5):
                    logger.debug(f"Rate limiting callback from user {user_id}")
                    return
                    
            # Handle messages
            if 'message' in update and 'text' in update['message']:
                message = update['message']
                user_id = message['from']['id']
                
                # Rate limiting for messages (1 second cooldown)
                if duplicate_manager.is_rate_limited(user_id, "message", 1.0):
                    logger.debug(f"Rate limiting message from user {user_id}")
                    return
                
                text = message['text']
                chat_id = message['chat']['id']
                user_id = str(user_id)
                
                # Check for custom auto trading input first
                if process_custom_user_input(update, chat_id, text):
                    return
                
                # Check for Buy/Sell trade messages (new format)
                if text.strip().lower().startswith('buy ') or text.strip().lower().startswith('sell '):
                    # Only process if from admin
                    if is_admin(update['message']['from']['id']):
                        import re
                        
                        # Parse trade message
                        buy_pattern = re.compile(r'^buy\s+(\$[a-zA-Z0-9]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)
                        sell_pattern = re.compile(r'^sell\s+(\$[a-zA-Z0-9]+)\s+([0-9.]+)\s+(https?://[^\s]+)$', re.IGNORECASE)
                        
                        buy_match = buy_pattern.match(text.strip())
                        sell_match = sell_pattern.match(text.strip())
                        
                        if buy_match:
                            token, price, tx_link = buy_match.groups()
                            self.send_message(chat_id, "💱 *Processing BUY order...*", parse_mode="Markdown")
                            
                            try:
                                # Add pending trade to database
                                with app.app_context():
                                    from models import TradingPosition
                                    
                                    # Check if transaction already exists
                                    tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
                                    existing = TradingPosition.query.filter_by(buy_tx_hash=tx_hash).first()
                                    
                                    if existing:
                                        self.send_message(
                                            chat_id, 
                                            f"⚠️ *Duplicate Transaction*\n\nThis BUY transaction has already been processed for {existing.token_name}",
                                            parse_mode="Markdown"
                                        )
                                        return
                                    
                                    # Create new position
                                    position = TradingPosition()
                                    position.user_id = 1  # Placeholder - will be updated when matched with SELL
                                    position.token_name = token.replace('$', '')
                                    position.amount = 1.0  # Placeholder
                                    position.entry_price = float(price)
                                    position.current_price = float(price)
                                    position.timestamp = datetime.utcnow()
                                    position.status = 'open'
                                    position.trade_type = 'scalp'
                                    position.buy_tx_hash = tx_hash
                                    position.buy_timestamp = datetime.utcnow()
                                    
                                    db.session.add(position)
                                    db.session.commit()
                                    
                                    self.send_message(
                                        chat_id,
                                        f"✅ *BUY Order Recorded*\n\n"
                                        f"• *Token:* {token}\n"
                                        f"• *Entry Price:* {price}\n"
                                        f"• *Transaction:* [View on Explorer]({tx_link})\n"
                                        f"• *Timestamp:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                        f"_This BUY will be matched with a future SELL order._",
                                        parse_mode="Markdown"
                                    )
                            except Exception as e:
                                logging.error(f"Error processing BUY trade: {e}")
                                import traceback
                                logging.error(traceback.format_exc())
                                self.send_message(chat_id, f"⚠️ Error processing BUY trade: {str(e)}")
                            
                            return
                            
                        elif sell_match:
                            token, price, tx_link = sell_match.groups()
                            self.send_message(chat_id, "💱 *Processing SELL order...*", parse_mode="Markdown")
                            
                            try:
                                # Match with open position and calculate profit
                                with app.app_context():
                                    from models import TradingPosition, Transaction, Profit, User
                                    
                                    # Check if transaction already exists
                                    tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
                                    existing = TradingPosition.query.filter_by(sell_tx_hash=tx_hash).first()
                                    
                                    if existing:
                                        self.send_message(
                                            chat_id, 
                                            f"⚠️ *Duplicate Transaction*\n\nThis SELL transaction has already been processed",
                                            parse_mode="Markdown"
                                        )
                                        return
                                    
                                    # Find matching open position
                                    clean_token = token.replace('$', '')
                                    position = TradingPosition.query.filter_by(
                                        token_name=clean_token,
                                        status='open'
                                    ).order_by(TradingPosition.buy_timestamp.asc()).first()
                                    
                                    if not position:
                                        self.send_message(
                                            chat_id,
                                            f"⚠️ *No Matching Position*\n\nNo open BUY order found for {token}",
                                            parse_mode="Markdown"
                                        )
                                        return
                                    
                                    # Calculate ROI percentage
                                    sell_price = float(price)
                                    entry_price = position.entry_price
                                    roi_percentage = ((sell_price - entry_price) / entry_price) * 100
                                    
                                    # Update position
                                    position.current_price = sell_price
                                    position.sell_tx_hash = tx_hash
                                    position.sell_timestamp = datetime.utcnow()
                                    position.status = 'closed'
                                    position.roi_percentage = roi_percentage
                                    
                                    # Apply profit to active users
                                    users = User.query.filter(User.balance > 0).all()
                                    updated_count = 0
                                    
                                    for user in users:
                                        try:
                                            # Calculate profit
                                            profit_amount = user.balance * (roi_percentage / 100)
                                            
                                            # Update balance
                                            previous_balance = user.balance
                                            user.balance += profit_amount
                                            

                                            
                                            # Create user position record
                                            user_position = TradingPosition()
                                            user_position.user_id = user.id
                                            user_position.token_name = clean_token
                                            user_position.amount = abs(profit_amount / (sell_price - entry_price)) if sell_price != entry_price else 1.0
                                            user_position.entry_price = entry_price
                                            user_position.current_price = sell_price
                                            user_position.timestamp = datetime.utcnow()
                                            user_position.status = 'closed'
                                            user_position.trade_type = position.trade_type if position.trade_type else 'scalp'
                                            user_position.buy_tx_hash = position.buy_tx_hash
                                            user_position.sell_tx_hash = tx_hash
                                            user_position.buy_timestamp = position.buy_timestamp
                                            user_position.sell_timestamp = datetime.utcnow()
                                            user_position.roi_percentage = roi_percentage
                                            user_position.paired_position_id = position.id
                                            
                                            # Add profit record
                                            profit_record = Profit()
                                            profit_record.user_id = user.id
                                            profit_record.amount = profit_amount
                                            profit_record.percentage = roi_percentage
                                            profit_record.date = datetime.utcnow().date()

                                            db.session.add(user_position)
                                            db.session.add(profit_record)
                                            
                                            # Send notification to user
                                            try:
                                                emoji = "📈" if roi_percentage >= 0 else "📉"
                                                message = (
                                                    f"{emoji} *Trade Alert*\n\n"
                                                    f"• *Token:* {clean_token}\n"
                                                    f"• *Entry:* {entry_price:.8f}\n"
                                                    f"• *Exit:* {sell_price:.8f}\n"
                                                    f"• *ROI:* {roi_percentage:.2f}%\n"
                                                    f"• *Your Profit:* {profit_amount:.4f} SOL\n"
                                                    f"• *New Balance:* {user.balance:.4f} SOL\n\n"
                                                    f"_Your dashboard has been updated with this trade._"
                                                )
                                                self.send_message(user.telegram_id, message, parse_mode="Markdown")
                                            except Exception as notify_error:
                                                logging.error(f"Error notifying user {user.id}: {str(notify_error)}")
                                            
                                            updated_count += 1
                                        except Exception as user_error:
                                            logging.error(f"Error updating user {user.id}: {str(user_error)}")
                                            continue
                                    
                                    # Commit all changes
                                    db.session.commit()
                                    
                                    # Send confirmation to admin
                                    self.send_message(
                                        chat_id,
                                        f"✅ *SELL Order Processed*\n\n"
                                        f"• *Token:* {token}\n"
                                        f"• *Exit Price:* {price}\n"
                                        f"• *Entry Price:* {position.entry_price}\n"
                                        f"• *ROI:* {roi_percentage:.2f}%\n"
                                        f"• *Users Updated:* {updated_count}\n"
                                        f"• *Transaction:* [View on Explorer]({tx_link})\n\n"
                                        f"_Trade profit has been applied to all active users._",
                                        parse_mode="Markdown"
                                    )
                            except Exception as e:
                                logging.error(f"Error processing SELL trade: {e}")
                                import traceback
                                logging.error(traceback.format_exc())
                                self.send_message(chat_id, f"⚠️ Error processing SELL trade: {str(e)}")
                            
                            return
                
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
                user_id = update['callback_query']['from']['id']
                
                # Check if this exact callback query ID was already processed
                if query_id in self._processed_callbacks:
                    logger.debug(f"Skipping duplicate callback query ID: {query_id}")
                    # Still answer the callback to prevent loading state
                    requests.post(
                        f"{self.api_url}/answerCallbackQuery",
                        json={'callback_query_id': query_id}
                    )
                    return
                
                # Add to processed callbacks immediately
                self._processed_callbacks.add(query_id)
                
                # Keep only recent callback IDs to prevent memory issues
                if len(self._processed_callbacks) > 1000:
                    # Remove oldest half
                    oldest_callbacks = sorted(self._processed_callbacks)[:500]
                    for old_id in oldest_callbacks:
                        self._processed_callbacks.discard(old_id)
                
                # Answer the callback query to stop the loading indicator
                requests.post(
                    f"{self.api_url}/answerCallbackQuery",
                    json={'callback_query_id': query_id}
                )
                
                # Process the callback data
                if data in self.handlers:
                    logger.info(f"Processing callback: {data} for chat {chat_id}")
                    try:
                        self.handlers[data](update, chat_id)
                    except Exception as callback_error:
                        logger.error(f"Error in callback handler {data}: {callback_error}")
                        import traceback
                        logger.error(traceback.format_exc())
                        self.send_message(chat_id, f"Error processing request: {str(callback_error)}")
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
                else:
                    logger.warning(f"No handler found for callback: {data}")
                    self.send_message(chat_id, f"Unknown action: {data}")
                
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    def start_polling(self):
        """Start polling for updates with aggressive duplicate elimination."""
        self.running = True
        logger.info("Starting polling for updates")
        
        # Clear pending updates to start completely fresh
        self.clear_pending_updates()
        
        while self.running:
            try:
                updates = self.get_updates()
                if updates:
                    logger.info(f"Processing {len(updates)} updates")
                    for update in updates:
                        update_id = update.get('update_id')
                        logger.info(f"Processing update {update_id}")
                        
                        # Process this update
                        self.process_update(update)
                        
                        # Immediately acknowledge this update to remove it from Telegram's queue
                        # This prevents any possibility of redelivery
                        requests.get(
                            f"{self.api_url}/getUpdates?offset={update_id + 1}&limit=1&timeout=0"
                        )
                        
                        # Update our local offset
                        self.offset = max(self.offset, update_id + 1)
                        
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            time.sleep(0.3)  # Reduced polling interval
    
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
from models import User, UserStatus, ReferralCode, Transaction
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
                    
                    # Process referral if applicable using simplified referral system
                    if start_parameter and start_parameter.startswith('ref_'):
                        try:
                            # Extract referrer ID from parameter
                            referrer_id = start_parameter.replace('ref_', '')
                            
                            # Use simplified referral system
                            from simple_referral_system import simple_referral_manager
                            success = simple_referral_manager.process_referral_signup(user_id, referrer_id)
                            
                            if success:
                                logger.info(f"Successfully processed referral: {user_id} referred by {referrer_id}")
                                
                                # Send welcome message mentioning the referral
                                referrer_user = User.query.filter_by(telegram_id=referrer_id).first()
                                if referrer_user:
                                    welcome_with_referral = (
                                        f"🎉 Welcome {first_name}!\n\n"
                                        f"You were invited by {referrer_user.first_name or referrer_user.username or 'a friend'}! "
                                        f"You're both eligible for referral rewards when you start trading.\n\n"
                                        f"When you make profits, your referrer will earn 5% as a bonus, "
                                        f"and you'll start earning when you refer others too!"
                                    )
                                    bot.send_message(chat_id, welcome_with_referral)
                            else:
                                logger.warning(f"Failed to process referral: {user_id} -> {referrer_id}")
                                
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
        # Use simplified referral system - same as referral_command
        from simple_referral_system import simple_referral_manager
        
        with app.app_context():
            user_id = str(update['callback_query']['from']['id'])
            
            # Get the referral link using the simple system (already has correct bot username)
            stats = simple_referral_manager.get_referral_stats(user_id)
            referral_link = stats['referral_link']
            
            # Send the referral link as a separate message for easy copying
            bot.send_message(
                chat_id,
                f"`{referral_link}`",
                parse_mode="Markdown"
            )
            
            bot.send_message(
                chat_id,
                "✅ Your referral link is ready! Share with friends to earn 5% of their profits."
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
                referral_manager.set_bot_username("ThriveQuantbot")
                logger.info("Initialized referral manager")
            
            user_id = str(update['callback_query']['from']['id'])
            
            # Get the referral link
            stats = referral_manager.get_referral_stats(user_id)
            
            # Generate the referral code if needed
            if not stats['has_code']:
                code = referral_manager.generate_or_get_referral_code(user_id)
                if code:
                    stats['has_code'] = True
            
            # Create a shareable message with the referral link - matching the expected format
            referral_link = f"https://t.me/ThriveQuantbot?start=ref_{user_id}"
            
            # First message: The shareable content (like in the image)
            share_message = (
                "🚀 Join me on THRIVE!\n\n"
                "I've been using this amazing crypto trading bot that's helping me "
                "grow my portfolio automatically.\n\n"
                "💰 What THRIVE does:\n"
                "• Trades live Solana memecoins 24/7\n"
                "• Tracks all profits transparently\n"
                "• Lets you withdraw anytime with proof\n\n"
                "🎁 Special offer: Use my link and we both get referral bonuses when "
                "you start trading!\n\n"
                "👇 Start here:\n"
                f"{referral_link}\n\n"
                "No subscriptions, no empty promises - just real trading results."
            )
            
            # Send the shareable message with COPY CODE button
            keyboard = bot.create_inline_keyboard([
                [{"text": "📋 COPY CODE", "callback_data": "copy_referral_message"}]
            ])
            
            # Send without parse_mode to avoid formatting issues
            bot.send_message(
                chat_id,
                share_message,
                reply_markup=keyboard
            )
            
            # Second message: Instructions on how to share
            instructions_message = (
                "🔗 Share Your Referral\n\n"
                "Copy the message above and share it anywhere:\n\n"
                "💡 Share on:\n"
                "• Telegram groups\n"
                "• WhatsApp\n"
                "• Twitter/X\n"
                "• Discord servers\n"
                "• Any social platform!\n\n"
                "💰 You'll earn 5% of all their trading profits!"
            )
            
            # Navigation keyboard
            nav_keyboard = bot.create_inline_keyboard([
                [{"text": "📋 COPY CODE", "callback_data": "copy_referral_message"}],
                [{"text": "🔙 Back to Referrals", "callback_data": "referral"}]
            ])
            
            bot.send_message(
                chat_id,
                instructions_message,
                reply_markup=nav_keyboard
            )
            
    except Exception as e:
        logger.error(f"Error in share_referral_handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sharing referral link: {str(e)}")

def copy_referral_message_handler(update, chat_id):
    """Handle the copy referral message button press."""
    try:
        # Use simplified referral system for consistency
        from simple_referral_system import simple_referral_manager
        
        with app.app_context():
            user_id = str(update['callback_query']['from']['id'])
            
            # Get the referral link using the simple system (already has correct bot username)
            stats = simple_referral_manager.get_referral_stats(user_id)
            referral_link = stats['referral_link']
            
            # Create the exact same shareable message
            share_message = (
                "🚀 Join me on THRIVE!\n\n"
                "I've been using this amazing crypto trading bot that's helping me "
                "grow my portfolio automatically.\n\n"
                "💰 What THRIVE does:\n"
                "• Trades live Solana memecoins 24/7\n"
                "• Tracks all profits transparently\n"
                "• Lets you withdraw anytime with proof\n\n"
                "🎁 Special offer: Use my link and we both get referral bonuses when "
                "you start trading!\n\n"
                "👇 Start here:\n"
                f"{referral_link}\n\n"
                "No subscriptions, no empty promises - just real trading results."
            )
            
            # Send the message for copying (without buttons for clean forwarding)
            bot.send_message(
                chat_id,
                share_message
            )
            
            # Send confirmation message
            bot.send_message(
                chat_id,
                "✅ Message copied! Forward the message above to share your referral link.\n\n"
                "💰 You'll earn 5% of all referred users' trading profits!"
            )
            
    except Exception as e:
        logger.error(f"Error in copy_referral_message_handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error copying referral message: {str(e)}")

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
                referral_manager.set_bot_username("ThriveQuantbot")
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
            from utils.solana import link_sender_wallet_to_user
            user = User.query.filter_by(telegram_id=user_id).first()
            if user:
                user.wallet_address = text
                
                # CRITICAL: Link this wallet as a sender wallet for auto deposit detection
                # This enables the system to match incoming deposits to this user
                link_success = link_sender_wallet_to_user(user.id, text)
                if link_success:
                    logger.info(f"Linked sender wallet {text} to user {user.id} for auto deposit detection")
                else:
                    logger.warning(f"Failed to link sender wallet {text} to user {user.id}")
                
                db.session.commit()
                
                # Sequence of messages exactly like in the original
                
                # First confirmation message
                wallet_updated_message = (
                    f"Payout wallet address updated to {text[:6]}..."
                    f"{text[-6:]}.\n\n"
                    f"It will be used for all future deposit payouts and auto-detection."
                )
                bot.send_message(chat_id, wallet_updated_message, parse_mode="Markdown")
                
                # Second message - deposit instructions with updated minimum amount
                deposit_instructions = (
                    f"Please send a minimum of *0.5 SOL (Solana)*\n"
                    f"and maximum *5000 SOL* to the following\n"
                    f"address.\n\n"
                    f"Once your deposit is received, it will be\n"
                    f"processed and your trading journey will begin.\n"
                    f"The following wallet address is your deposit wallet:"
                )
                bot.send_message(chat_id, deposit_instructions, parse_mode="Markdown")
                
                # Use the global admin deposit wallet address
                from helpers import get_global_deposit_wallet
                deposit_wallet = get_global_deposit_wallet()
                
                # Update user record with the global deposit wallet
                try:
                    user.deposit_wallet = deposit_wallet
                    db.session.commit()
                except:
                    pass
                
                # Display the global deposit wallet address
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
    """Handle the /help command with professional memecoin trader focus."""
    try:
        help_message = (
            "🤖 *THRIVE TRADING BOT HELP*\n\n"
            
            "📋 *MAIN COMMANDS*\n"
            "`/start` - Start the bot and create your account\n"
            "`/dashboard` - View your balance and trading performance\n"
            "`/deposit` - Add SOL to start trading\n"
            "`/withdraw` - Withdraw your profits\n"
            "`/referral` - Get your referral link and earnings\n"
            "`/help` - Show this help message\n\n"
            
            "⚙️ *TRADING FEATURES*\n"
            "• *Auto Trading Settings* - Configure automated trading\n"
            "  - Set position sizes and risk levels\n"
            "  - Choose signal sources (Pump.fun, whale tracking)\n"
            "  - Set stop loss and take profit levels\n"
            "  - Manage daily trade limits\n\n"
            
            "• *Sniper Mode* - Fast token buying\n"
            "  - Monitor new token launches\n"
            "  - Quick buy opportunities\n"
            "  - Real-time market scanning\n\n"
            
            "• *Performance Tracking* - View your results\n"
            "  - Daily and total P/L\n"
            "  - Trading history\n"
            "  - Success rate statistics\n\n"
            
            "💰 *HOW IT WORKS*\n"
            "1. Deposit SOL to activate trading\n"
            "2. Configure your auto trading settings\n"
            "3. Bot monitors markets and executes trades\n"
            "4. View profits in your dashboard\n"
            "5. Withdraw anytime\n\n"
            
            "🎁 *REFERRAL PROGRAM*\n"
            "• Earn 5% of your friends' profits\n"
            "• Share your referral link\n"
            "• Track your referral earnings\n\n"
            
            "💡 *GETTING STARTED*\n"
            "Use the buttons below to access main features or type any command above."
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "📊 Dashboard", "callback_data": "view_dashboard"},
                {"text": "⚙️ Auto Trading Settings", "callback_data": "auto_trading_settings"}
            ],
            [
                {"text": "🎯 Sniper Mode", "callback_data": "sniper_mode"},
                {"text": "💰 Deposit", "callback_data": "deposit"}
            ],
            [
                {"text": "💸 Withdraw", "callback_data": "withdraw"},
                {"text": "👥 Referral Program", "callback_data": "referral"}
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
                
                # Update initial deposit to include all deposits (cumulative total)
                user.initial_deposit += deposit_amount
                
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
                bot.send_message(chat_id, "Please initiate platform access with /start first.")
                return
            
            # Get system deposit wallet address from settings
            deposit_setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
            
            # If no wallet is configured in system settings, use a default address
            if deposit_setting and deposit_setting.setting_value:
                deposit_wallet = deposit_setting.setting_value
            else:
                deposit_wallet = "2pWHfMgpLtcnJpeFRzuRqXxAxBs2qjhU46xkdb5dCSzD"  # Primary custody wallet
            
            # Send the institutional-grade deposit message
            deposit_message = (
                "💎 *INSTITUTIONAL CAPITAL DEPOSIT*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                "*🏛️ CUSTODY INFRASTRUCTURE ACCESS*\n\n"
                
                "To begin algorithmic trading operations, transfer capital to our institutional-grade custody infrastructure:\n\n"
                
                "*Enterprise-Grade Custody Infrastructure*\n"
                "Multi-signature wallet architecture with institutional security protocols.\n\n"
                
                "*📊 INSTITUTIONAL PARAMETERS*\n\n"
                
                "• **Minimum Capital:** 0.5 SOL (institutional threshold)\n"
                "• **Network Protocol:** Solana mainnet with sub-second finality\n"
                "• **Processing Timeline:** Real-time detection (30-120 seconds)\n"
                "• **Custody Security:** Multi-signature with time-locked withdrawals\n"
                "• **Trading Activation:** Immediate algorithmic deployment upon confirmation\n\n"
                
                "*🔐 INSTITUTIONAL SECURITY STANDARDS*\n\n"
                
                "Your capital is secured through enterprise-grade protocols including multi-signature custody, hardware security modules, and institutional cold storage integration. All fund movements are recorded on-chain with full transaction transparency.\n\n"
                
                "*Upon deposit confirmation, our algorithmic trading infrastructure will immediately deploy your capital using our institutional-grade memecoin trading strategies with real-time risk management.*"
            )
            
            # Create professional keyboard interface
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📋 Copy Custody Address", "callback_data": "copy_address"},
                    {"text": "✅ Capital Transferred", "callback_data": "deposit_confirmed"}
                ],
                [
                    {"text": "🔐 Verify Custody Wallet", "callback_data": "verify_wallet"},
                    {"text": "📋 Platform Documentation", "callback_data": "faqs"}
                ],
                [
                    {"text": "🏛️ Trading Platform", "callback_data": "start"}
                ]
            ])
            
            bot.send_message(chat_id, deposit_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in deposit command: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error accessing deposit interface: {str(e)}")

def dashboard_command(update, chat_id):
    """Handle the /dashboard command - show simple Autopilot Dashboard matching the user's screenshot."""
    try:
        from datetime import datetime, timedelta
        
        with app.app_context():
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
                
            # Get real-time performance data
            from performance_tracking import get_performance_data, get_days_with_balance
            performance_data = get_performance_data(user.id)
            
            if performance_data:
                total_profit_amount = performance_data['total_profit']
                total_profit_percentage = performance_data['total_percentage']
                today_profit_amount = performance_data['today_profit']
                today_profit_percentage = performance_data['today_percentage']
                streak = performance_data['streak_days']
                current_balance = performance_data['current_balance']
                days_with_balance = get_days_with_balance(user.id)
            else:
                # Fallback values
                total_profit_amount = 0
                total_profit_percentage = 0
                today_profit_amount = 0
                today_profit_percentage = 0
                streak = 0
                days_with_balance = 0
                current_balance = user.balance
            
            # Dashboard message with USD for balance only, SOL for P/L
            balance_with_usd = format_balance_with_usd(current_balance)
            
            # Get current SOL price and change indicator for realism
            sol_price = get_sol_price_usd()
            price_change = get_price_change_indicator()
            
            dashboard_message = (
                "📊 *Autopilot Dashboard*\n\n"
                f"• *Balance:* {balance_with_usd}\n"
                f"• *Today's P/L:* {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}%)\n"
                f"• *Total P/L:* +{total_profit_percentage:.1f}% (+{total_profit_amount:.2f} SOL)\n"
                f"• *Profit Streak:* {streak} Days\n"
                f"• *Mode:* Autopilot Trader (Fully Automated)\n"
                f"• *Day:* {days_with_balance}\n\n"
                
                "💡 *Thrive automatically manages your portfolio to optimize profit and reduce risk.*\n\n"
                "⚠️ *Note: 2% fee applies to profits only (not deposits)*"
            )
            
            # Dynamic sniper button based on user status
            sniper_button_text = "🎯 Start Sniper"
            sniper_callback = "start_sniper"
            
            if hasattr(user, 'sniper_active') and user.sniper_active:
                sniper_button_text = "⏹️ Stop Sniper"
                sniper_callback = "stop_sniper"
            
            # Create keyboard matching the screenshot with dynamic sniper button
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
                    {"text": "⚙️ Auto Trading", "callback_data": "auto_trading_settings"},
                    {"text": "📈 Sniper Stats", "callback_data": "sniper_stats"}
                ],
                [
                    {"text": "📍 Live Positions", "callback_data": "live_positions"},
                    {"text": "🛟 Customer Support", "callback_data": "support"}
                ],
                [
                    {"text": sniper_button_text, "callback_data": sniper_callback}
                ],
                [
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
                f"*Account Status:* {'Active' if user.balance > 0 else 'Not Active'}\n"
                f"*Payout Wallet:* `{display_wallet}`\n"
                f"*Joined:* {user.joined_at.strftime('%Y-%m-%d')}\n"
                f"*Auto-Trades:* {'Enabled' if user.balance > 0 else 'Disabled'}\n\n"
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
    """Handle the /referral command with simplified system - no referral codes needed."""
    try:
        # Use simplified referral system
        from simple_referral_system import simple_referral_manager
        
        with app.app_context():
            user_id = str(update['message']['from']['id']) if 'message' in update else str(update['callback_query']['from']['id'])
            
            # Get the user's referral stats
            stats = simple_referral_manager.get_referral_stats(user_id)
            
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
                
                f"📱 *YOUR REFERRAL LINK*\n"
                f"`{stats['referral_link']}`\n"
            )
            
            # Create enhanced keyboard with all options
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📋 Copy Link", "callback_data": "copy_referral_link"},
                    {"text": "📱 Generate QR", "callback_data": "referral_qr_code"}
                ],
                [
                    {"text": "📊 View Stats", "callback_data": "referral_stats"}
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
            # Count active users (users with SOL balance > 0)
            active_users = User.query.filter(User.balance > 0).count()
            
            message = (
                f"👥 User Management\n\n"
                f"Total users: {total_users}\n"
                f"Active users: {active_users}\n\n"
                f"Select an action below:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "View All Users", "callback_data": "admin_view_all_users"},
                    {"text": "View Active Users", "callback_data": "admin_view_active_users"}
                ],
                [
                    {"text": "Search User", "callback_data": "admin_search_user"},
                    {"text": "Export CSV", "callback_data": "admin_export_csv"}
                ],
                [
                    {"text": "Back to Admin", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                message,
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
                # Fixed: Count users with balance > 0 as active users
                active_users = User.query.filter(User.balance > 0).count()
                
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
    """Handle the adjust balance button with completely safe text formatting."""
    try:
        # Send a simple, safe message without user suggestions to avoid parsing errors
        message = (
            "ADJUST USER BALANCE\n\n"
            "Enter the Telegram ID or username of the user whose balance you want to adjust.\n\n"
            "Examples:\n"
            "- 1234567890 for Telegram ID\n"
            "- @username\n"
            "- username\n\n"
            "Type cancel to go back."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Refresh", "callback_data": "admin_adjust_balance"}],
            [{"text": "Back", "callback_data": "admin_back"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            reply_markup=keyboard
        )
        
        # Add listener for the next message (user ID input)
        bot.add_message_listener(chat_id, "text", admin_adjust_balance_user_id_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_adjust_balance_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Send a simple error message without any special formatting
        try:
            bot.send_message(chat_id, "Error: Cannot display balance adjustment menu")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def admin_adjust_balance_user_id_handler(update, chat_id, message_text):
    """Process the user ID for balance adjustment."""
    try:
        # Extract the actual text from the message if it's not already a string
        if isinstance(message_text, str):
            user_input = message_text
        else:
            # Fallback: extract text from update if message_text is not a string
            user_input = update.get('message', {}).get('text', str(message_text))
        
        # Check for cancellation
        if user_input.lower() == 'cancel':
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
            from sqlalchemy import func, text as sql_text
            import logging
            
            # Test database connection first (same as working View All Users)
            try:
                db.session.execute(sql_text('SELECT 1'))
                logging.info("Database connection verified for balance adjustment")
            except Exception as conn_error:
                logging.error(f"Database connection failed in balance adjustment: {conn_error}")
                bot.send_message(chat_id, f"❌ Database connection error: {str(conn_error)}")
                return
            
            # Enhanced user search with better error handling and logging
            user = None
            search_input = user_input.strip()
            
            logging.info(f"Searching for user with input: '{search_input}'")
            
            # Method 1: Try as telegram_id (string) - database stores as VARCHAR
            try:
                user = User.query.filter_by(telegram_id=search_input).first()
                if user:
                    logging.info(f"Found user by telegram_id (string): {user.telegram_id}")
            except Exception as e:
                logging.error(f"Error searching by telegram_id (string): {e}")
            
            # Method 2: Try casting database field to string for comparison (fallback)
            if not user and search_input.isdigit():
                try:
                    from sqlalchemy import cast, String
                    user = User.query.filter(cast(User.telegram_id, String) == search_input).first()
                    if user:
                        logging.info(f"Found user by telegram_id (cast): {user.telegram_id}")
                except Exception as e:
                    logging.error(f"Error searching by telegram_id (cast): {e}")
            
            # Method 3: Try by username (with @ prefix)
            if not user and search_input.startswith('@'):
                try:
                    username = search_input[1:]  # Remove @ prefix
                    user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
                    if user:
                        logging.info(f"Found user by username (with @): {user.username}")
                except Exception as e:
                    logging.error(f"Error searching by username (with @): {e}")
            
            # Method 4: Try username without @ prefix
            if not user:
                try:
                    user = User.query.filter(func.lower(User.username) == func.lower(search_input)).first()
                    if user:
                        logging.info(f"Found user by username (without @): {user.username}")
                except Exception as e:
                    logging.error(f"Error searching by username (without @): {e}")
            
            # Method 5: Last resort - search all users and check partial matches
            if not user:
                try:
                    # Check if it might be a partial telegram_id or username
                    all_users = User.query.all()
                    for u in all_users:
                        if (str(u.telegram_id) == search_input or 
                            (u.username and u.username.lower() == search_input.lower())):
                            user = u
                            logging.info(f"Found user via full scan: {u.telegram_id}")
                            break
                except Exception as e:
                    logging.error(f"Error in full user scan: {e}")
            
            if not user:
                error_msg = (
                    f"⚠️ User not found with input: '{search_input}'\n\n"
                    "Please try:\n"
                    "• Valid Telegram ID (e.g., 7611754415)\n"
                    "• Username with @ (e.g., @username)\n"
                    "• Username without @ (e.g., username)\n"
                    "• Type 'cancel' to go back"
                )
                logging.warning(f"User not found with any method for input: '{search_input}'")
                bot.send_message(chat_id, error_msg)
                return
            
            # Store user info in global variables
            global admin_target_user_id
            admin_target_user_id = user.id
            
            # Also store user telegram_id and current balance for later reference
            global admin_adjust_telegram_id, admin_adjust_current_balance
            admin_adjust_telegram_id = user.telegram_id
            admin_adjust_current_balance = user.balance
            
            # Create a safe message without complex Markdown formatting
            if user.username:
                # Remove problematic characters from username
                clean_username = user.username.replace('_', '').replace('.', '').replace('*', '').replace('[', '').replace(']', '').replace('`', '').replace('(', '').replace(')', '').replace('~', '').replace('>', '').replace('#', '').replace('+', '').replace('=', '').replace('|', '').replace('{', '').replace('}', '').replace('!', '')
                username_display = f"@{clean_username}"
            else:
                username_display = "No username"
            
            # Use plain text to avoid Markdown parsing issues
            message_text = (
                "USER FOUND\n\n"
                f"User: {username_display}\n"
                f"Telegram ID: {user.telegram_id}\n"
                f"Current Balance: {user.balance:.0f} SOL\n\n"
                "Enter adjustment amount:\n"
                "Positive number to add example 5\n"
                "Negative number to remove example -3\n"
                "Type cancel to abort"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "admin_back"}]
            ])
            
            # Send without parse_mode to avoid Markdown issues
            bot.send_message(
                chat_id,
                message_text,
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
            
            # Create confirmation message with plain text formatting
            global admin_adjust_telegram_id, admin_adjust_current_balance
            
            new_balance = (admin_adjust_current_balance or 0.0) + adjustment
            action = "add" if adjustment > 0 else "deduct"
            
            confirmation_message = (
                "CONFIRM BALANCE ADJUSTMENT\n\n"
                f"User ID: {admin_adjust_telegram_id or 'Unknown'}\n"
                f"Current Balance: {admin_adjust_current_balance or 0.0:.4f} SOL\n"
                f"Adjustment: {action} {abs(adjustment):.4f} SOL\n"
                f"New Balance: {new_balance:.4f} SOL\n"
                f"Reason: {admin_adjustment_reason or 'Admin adjustment'}\n\n"
                "Are you sure you want to proceed?"
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
    """Fixed balance adjustment handler with complete message sequence restoration."""
    import logging
    
    try:
        # Capture all global variables locally
        global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
        global admin_adjustment_amount, admin_adjustment_reason
        
        logging.info("Admin confirm adjustment handler called")
        
        # Check if we already have data to process
        if admin_target_user_id is None or admin_adjustment_amount is None:
            logging.warning("Missing adjustment data in confirm handler")
            bot.send_message(
                chat_id,
                "No pending balance adjustment found. Please try again.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            return
            
        # Store values locally before resetting globals
        tg_id = admin_adjust_telegram_id
        amount = admin_adjustment_amount
        reason = admin_adjustment_reason or "Admin adjustment"
        current_balance = admin_adjust_current_balance or 0
        
        logging.info(f"Processing adjustment: User {tg_id}, Amount {amount}, Reason {reason}")
        
        # Step 1: Send initial processing message
        processing_msg = bot.send_message(
            chat_id,
            "✅ Processing your balance adjustment request...",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
            ])
        )
        
        # Reset globals to prevent duplicate processing
        admin_target_user_id = None
        admin_adjust_telegram_id = None
        admin_adjust_current_balance = None
        admin_adjustment_amount = None
        admin_adjustment_reason = None
        
        # Process the adjustment
        try:
            # Use the working balance manager
            from working_balance_manager import adjust_balance_fixed
            
            # Process the adjustment
            success, detailed_message = adjust_balance_fixed(str(tg_id), amount, reason)
            
            if success:
                # Step 2: Send completion message
                action = "added" if amount > 0 else "deducted"
                completion_message = (
                    "BALANCE ADJUSTMENT COMPLETED\n\n"
                    f"Amount: {abs(amount):.4f} SOL {action}"
                )
                
                bot.send_message(
                    chat_id,
                    completion_message,
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
                
                # Step 3: Send detailed success message (plain text format to avoid parsing errors)
                success_message = detailed_message.replace('(', '').replace(')', '').replace('*', '').replace('_', '').replace('`', '')
                
                bot.send_message(
                    chat_id,
                    success_message,
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
                
                logging.info(f"Balance adjustment successful for {tg_id}")
            else:
                # Handle failure case
                error_message = (
                    "BALANCE ADJUSTMENT FAILED\n\n"
                    f"Error: {detailed_message}"
                )
                
                bot.send_message(
                    chat_id,
                    error_message,
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
                
                logging.error(f"Balance adjustment failed for {tg_id}: {detailed_message}")
            
        except Exception as process_error:
            logging.error(f"Error during balance adjustment processing: {process_error}")
            error_message = f"Error processing adjustment: {str(process_error)}"
            
            bot.send_message(
                chat_id,
                error_message,
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
        
        logging.info("Balance adjustment handler completed successfully")
        return
    
    except Exception as e:
        logging.error(f"Error in balance adjustment handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
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
            
            # Get users with positive balances (truly active users) ordered by balance (highest first)
            active_users = User.query.filter(User.balance > 0).order_by(User.balance.desc()).limit(10).all()
            
            if not active_users:
                message = (
                    "👥 *Active Users*\n\n"
                    "There are currently no users with balances in the system."
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
                "Users with balances (sorted by highest balance):\n\n"
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
                
                # Escape special characters for Markdown safety
                def escape_markdown(text):
                    """Escape special Markdown characters"""
                    if not text:
                        return "Not set"
                    special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                    escaped = str(text)
                    for char in special_chars:
                        escaped = escaped.replace(char, f'\\{char}')
                    return escaped
                
                # Safely format username and wallet
                safe_username = escape_markdown(user.username) if user.username else "Not set"
                safe_wallet = escape_markdown(display_wallet)
                
                # Create user entry with escaped content
                user_entry = (
                    f"*User #{idx}*\n"
                    f"• ID: `{user.telegram_id}`\n"
                    f"• Username: @{safe_username}\n"
                    f"• Wallet: `{safe_wallet}`\n"
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
    global _bot_instance
    import logging
    import traceback
    logging.info(f"View All Users button clicked by chat_id: {chat_id}")
    
    try:
        # Get the global bot instance
        if _bot_instance is None:
            logging.error("Bot instance not available")
            return
        
        bot = _bot_instance
        
        # Verify admin access first
        if not is_admin(chat_id):
            bot.send_message(chat_id, "❌ Access denied. Admin permissions required.")
            return
            
        # Send loading message
        bot.send_message(chat_id, "📊 Loading user data...")
        
        with app.app_context():
            from models import User, UserStatus, Transaction, Profit, ReferralCode
            from app import db
            from sqlalchemy import func, desc
            from datetime import datetime, timedelta
            
            logging.info(f"Starting database query for all users")
            
            # Test database connection first
            try:
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
                logging.info("Database connection verified")
            except Exception as conn_error:
                logging.error(f"Database connection failed: {conn_error}")
                bot.send_message(chat_id, f"❌ Database connection error: {str(conn_error)}")
                return
            
            # Get all users with detailed information
            try:
                users = User.query.order_by(desc(User.joined_at)).limit(15).all()
                logging.info(f"Successfully queried {len(users)} users from database")
                
                if not users:
                    message = (
                        "👥 *All Users*\n\n"
                        "No registered users found in the system.\n\n"
                        "Users will appear here after they start the bot with /start command."
                    )
                    
                    keyboard = bot.create_inline_keyboard([
                        [{"text": "🔙 Back to User Management", "callback_data": "admin_user_management"}]
                    ])
                    
                    bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
                    return
                
                # Build user list with enhanced formatting
                message = "👥 *All Registered Users*\n\n"
                
                for idx, user in enumerate(users, 1):
                    # Safe data extraction with defaults
                    try:
                        registration_date = user.joined_at.strftime("%m/%d/%Y") if user.joined_at else "Unknown"
                        username_display = f"@{user.username}" if user.username else "No Username"
                        status_display = user.status.value if hasattr(user, 'status') and user.status else "unknown"
                        balance = getattr(user, 'balance', 0.0)
                        
                        # Get additional stats for this user
                        try:
                            total_deposits = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter_by(
                                user_id=user.id, transaction_type='deposit'
                            ).scalar() or 0
                            
                            referral_count = ReferralCode.query.filter_by(referrer_id=user.id).count()
                        except Exception as stats_error:
                            logging.warning(f"Error getting stats for user {user.id}: {stats_error}")
                            total_deposits = 0
                            referral_count = 0
                        
                        message += (
                            f"*{idx}. {username_display}*\n"
                            f"• ID: `{user.telegram_id}`\n"
                            f"• Balance: {balance:.4f} SOL\n"
                            f"• Deposits: {total_deposits:.4f} SOL\n"
                            f"• Referrals: {referral_count}\n"
                            f"• Status: {status_display}\n"
                            f"• Joined: {registration_date}\n\n"
                        )
                        
                    except Exception as user_error:
                        logging.warning(f"Error processing user {user.id}: {user_error}")
                        message += f"*{idx}. Error loading user data*\n\n"
                        continue
                
                message += f"📊 *Total: {len(users)} users shown (most recent first)*"
                
                # Create navigation keyboard
                keyboard = bot.create_inline_keyboard([
                    [
                        {"text": "🔍 Search User", "callback_data": "admin_search_user"},
                        {"text": "📊 Active Only", "callback_data": "admin_view_active_users"}
                    ],
                    [
                        {"text": "📄 Export CSV", "callback_data": "admin_export_csv"},
                        {"text": "🔄 Refresh", "callback_data": "admin_view_all_users"}
                    ],
                    [
                        {"text": "🔙 Back to User Management", "callback_data": "admin_user_management"}
                    ]
                ])
                
                bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
                logging.info(f"Successfully sent user list to admin {chat_id}")
                
            except Exception as query_error:
                logging.error(f"Database query error: {query_error}")
                logging.error(traceback.format_exc())
                bot.send_message(
                    chat_id, 
                    f"❌ *Database Query Error*\n\n{str(query_error)}\n\nPlease try again or contact system administrator.",
                    parse_mode="Markdown"
                )
                
    except Exception as e:
        logging.error(f"Critical error in admin_view_all_users_handler: {e}")
        logging.error(traceback.format_exc())
        
        try:
            if _bot_instance is not None:
                _bot_instance.send_message(
                    chat_id, 
                    f"❌ *System Error*\n\nUnexpected error occurred: {str(e)}\n\nPlease try again later.",
                    parse_mode="Markdown",
                    reply_markup=_bot_instance.create_inline_keyboard([
                        [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
        except Exception as send_error:
            logging.error(f"Failed to send error message: {send_error}")

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
            temp_file_path = os.path.join(tempfile.gettempdir(), filename)
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
        
        # Get current active user count
        with app.app_context():
            from models import User
            active_count = User.query.filter(User.balance > 0).count()
        
        message = (
            "📊 *Broadcast Target Selected*\n\n"
            f"You've chosen to send this broadcast to *active users only* ({active_count} users).\n\n"
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

def live_positions_handler(update, chat_id):
    """Handle the Position button - Display professional LIVE POSITIONS DASHBOARD."""
    try:
        with app.app_context():
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Get live trading positions from TradingPosition table
            from models import TradingPosition
            from datetime import datetime, timedelta
            from sqlalchemy import desc
            import random
            
            # Get recent positions (both buys and sells) ordered by most recent
            recent_positions = TradingPosition.query.filter_by(user_id=user.id).order_by(desc(TradingPosition.timestamp)).limit(8).all()
            
            # Professional dashboard header
            current_time = datetime.utcnow().strftime("%b %d – %H:%M UTC")
            position_message = (
                "🎯 *LIVE POSITIONS DASHBOARD*\n\n"
                "⚡️ *Sniper Feed: Real-Time Auto Updates* ⚡️\n"
                f"Last sync: {current_time}\n\n\n\n"
            )
            
            if not recent_positions:
                position_message += (
                    "🔍 *No active positions yet*\n\n"
                    "Your live sniper feed will appear here instantly when trades execute.\n\n"
                    "• LIVE SNIPE entries show immediately\n"
                    "• EXIT SNIPE auto-calculates P/L\n"
                    "• Real TX mapping with Solscan links\n\n"
                    "_Deposit SOL to activate live trading_"
                )
            else:
                # Sort positions to show EXIT trades first, then LIVE trades
                exit_positions = []
                live_positions = []
                
                for position in recent_positions:
                    if hasattr(position, 'sell_timestamp') and position.sell_timestamp and hasattr(position, 'roi_percentage') and position.roi_percentage is not None:
                        exit_positions.append(position)
                    else:
                        live_positions.append(position)
                
                # Display EXIT SNIPE trades first
                for position in exit_positions:
                    time_str = position.sell_timestamp.strftime("%b %d – %H:%M UTC") if position.sell_timestamp else position.timestamp.strftime("%b %d – %H:%M UTC")
                    
                    # Calculate financials
                    entry_price = position.entry_price or 0
                    exit_price = position.current_price or position.exit_price or 0
                    amount = position.amount or 0
                    spent_sol = amount * entry_price if entry_price > 0 else 0
                    returned_sol = amount * exit_price if exit_price > 0 else 0
                    pl_sol = returned_sol - spent_sol
                    roi_pct = position.roi_percentage if hasattr(position, 'roi_percentage') and position.roi_percentage is not None else 0
                    
                    # Emoji and formatting
                    roi_emoji = "🟢" if roi_pct >= 0 else "🔴"
                    roi_sign = "+" if roi_pct >= 0 else ""
                    pl_sign = "+" if pl_sol >= 0 else "–"
                    

                    
                    # Get TX link with embedded text format
                    tx_display = "Transaction: unavailable"
                    if hasattr(position, 'sell_tx_hash') and position.sell_tx_hash:
                        if position.sell_tx_hash.startswith('http'):
                            tx_url = position.sell_tx_hash
                        else:
                            tx_url = f"https://solscan.io/tx/{position.sell_tx_hash}"
                        tx_display = f"[Transaction]({tx_url})"
                    
                    position_message += (
                        f"✅ *EXIT SNIPE - ${position.token_name}*\n\n"
                        f"Sell @: {exit_price:.6f} | Qty: {amount:,.0f} {position.token_name}\n"
                        f"Spent: {spent_sol:.2f} SOL | Returned: {returned_sol:.3f} SOL\n"
                        f"Profit: {roi_emoji} {roi_sign}{roi_pct:.2f}% (Auto) | P/L: {pl_sign}{abs(pl_sol):.3f} SOL\n"
                        f"{tx_display}\n"
                        f"Closed: {time_str}\n\n\n\n"
                    )
                
                # Display LIVE SNIPE trades
                for position in live_positions:
                    time_str = position.buy_timestamp.strftime("%b %d – %H:%M UTC") if hasattr(position, 'buy_timestamp') and position.buy_timestamp else position.timestamp.strftime("%b %d – %H:%M UTC")
                    
                    # Calculate financials
                    entry_price = position.entry_price or 0
                    amount = position.amount or 0
                    spent_sol = amount * entry_price if entry_price > 0 else 0
                    

                    
                    # Get TX link with embedded text format
                    tx_display = "Transaction: unavailable"
                    if hasattr(position, 'buy_tx_hash') and position.buy_tx_hash:
                        if position.buy_tx_hash.startswith('http'):
                            tx_url = position.buy_tx_hash
                        else:
                            tx_url = f"https://solscan.io/tx/{position.buy_tx_hash}"
                        tx_display = f"[Transaction]({tx_url})"
                    
                    position_message += (
                        f"🟡 *LIVE SNIPE - ${position.token_name}*\n\n"
                        f"Buy @: {entry_price:.6f} | Qty: {amount:,.0f} {position.token_name}\n"
                        f"Spent: {spent_sol:.2f} SOL\n"
                        f"{tx_display}\n"
                        f"Status: Holding\n"
                        f"Opened: {time_str}\n\n\n\n"
                    )
                

            
            # Create keyboard with professional styling
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "🔄 Refresh Feed", "callback_data": "live_positions"},
                    {"text": "📊 Performance", "callback_data": "trading_history"}
                ],
                [
                    {"text": "🏠 Dashboard", "callback_data": "view_dashboard"}
                ]
            ])
            
            bot.send_message(chat_id, position_message, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)
            
    except Exception as e:
        import logging
        logging.error(f"Error in live_positions_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying live positions: {str(e)}")

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
    Handle BUY/SELL trade posting with automatic profit calculation.
    
    BUY Format: /admin_buy [UserID] [TokenName] [EntryPrice] [TxHash]
    SELL Format: /admin_sell [UserID] [TokenName] [SellPrice] [TxHash]
    
    Examples:
    /admin_buy 123456789 $ZING 0.0051 0xabc123
    /admin_sell 123456789 $ZING 0.0057 0xdef456
    
    The bot automatically matches SELL orders with unmatched BUY orders
    and calculates profit: ((Sell - Buy) / Buy) * 100
    """
    try:
        # Determine if this is a BUY or SELL command
        command_text = update['message']['text'].lower()
        is_buy_command = '/admin_buy' in command_text
        is_sell_command = '/admin_sell' in command_text
        
        if not (is_buy_command or is_sell_command):
            # Show new format instructions
            instructions = (
                "📈 *New Trade System - BUY/SELL Format*\n\n"
                "**BUY Trade:**\n"
                "`/admin_buy [UserID] $TOKEN [EntryPrice] [TxHash]`\n\n"
                "**SELL Trade:**\n"
                "`/admin_sell [UserID] $TOKEN [SellPrice] [TxHash]`\n\n"
                "**Examples:**\n"
                "`/admin_buy 123456789 $ZING 0.0051 0xabc123`\n"
                "`/admin_sell 123456789 $ZING 0.0057 0xdef456`\n\n"
                "✅ Profit calculated automatically: ((Sell - Buy) / Buy) × 100\n"
                "✅ SELL orders matched with unmatched BUY orders\n"
                "✅ No manual ROI input needed"
            )
            bot.send_message(chat_id, instructions, parse_mode="Markdown")
            return
        
        # Check for admin privileges
        if not is_admin(update['message']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return
            
        # Parse parameters for new format
        text_parts = update['message']['text'].split()
        if len(text_parts) < 5:  # Command + 4 parameters
            bot.send_message(chat_id, "⚠️ Invalid format. Use the examples shown above.", parse_mode="Markdown")
            return
            
        # Parse the parameters for new BUY/SELL format
        user_id = text_parts[1]
        token_name = text_parts[2]
        price = float(text_parts[3])
        tx_hash = text_parts[4]
        
        if is_buy_command:
            from admin_buy_sell_system import process_buy_trade
            process_buy_trade(user_id, token_name, price, tx_hash, bot, chat_id)
        elif is_sell_command:
            from admin_buy_sell_system import process_sell_trade
            process_sell_trade(user_id, token_name, price, tx_hash, bot, chat_id)
            
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
            
        # Show input form with instructions for new BUY/SELL format
        instructions = (
            "📈 *Broadcast Trade Alert - New Format*\n\n"
            "Send the trade details in one of these formats:\n\n"
            "`Buy $TOKEN PRICE AMOUNT TX_LINK`\n"
            "`Sell $TOKEN PRICE AMOUNT TX_LINK`\n\n"
            "Examples:\n"
            "`Buy $ZING 0.004107 812345 https://solscan.io/tx/abc123`\n"
            "`Sell $ZING 0.006834 812345 https://solscan.io/tx/def456`\n\n"
            "*Format Breakdown:*\n"
            "• Buy/Sell — trade type\n"
            "• $ZING — token symbol\n"
            "• 812345 — amount of tokens\n"
            "• 0.0041 / 0.0068 — token price (entry or exit)\n"
            "• Transaction Link — proof of trade (Solscan)\n\n"
            "For Buy orders: Records the transaction for future matching\n"
            "For Sell orders: Matches with previous Buy and calculates ROI\n\n"
            "✅ ROI calculated automatically when matching Buy/Sell pairs\n"
            "✅ Timestamps recorded for entry/exit timing analysis\n\n"
            "After entering trade details, you'll choose the broadcast time (auto or custom)."
        )
        
        # Set the global state to listen for the broadcast text
        global broadcast_target
        broadcast_target = "active"  # Send only to active users
        
        # Add listener for the admin's next message (trade input)
        bot.add_message_listener(chat_id, "broadcast_trade_input", admin_broadcast_trade_input_handler)
        
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

def admin_broadcast_trade_input_handler(update, chat_id, text):
    """Handle trade input and show time selection options."""
    try:
        # Remove the message listener
        bot.remove_listener(chat_id)
        
        # Store the trade data temporarily
        global admin_pending_trade_data
        admin_pending_trade_data = {
            'trade_text': text,
            'admin_id': str(update.get('message', {}).get('from', {}).get('id', 'admin'))
        }
        
        # Show time selection options
        from datetime import datetime, timedelta
        
        current_time = datetime.utcnow()
        time_message = (
            "⏰ *Select Broadcast Time*\n\n"
            f"Trade: `{text[:50]}{'...' if len(text) > 50 else ''}`\n\n"
            "Choose when this trade was executed:"
        )
        
        # Create time selection keyboard
        keyboard = bot.create_inline_keyboard([
            [{"text": "🤖 Auto (Now)", "callback_data": "time_auto"}],
            [
                {"text": "⏰ 5 min ago", "callback_data": "time_5m"},
                {"text": "⏰ 15 min ago", "callback_data": "time_15m"}
            ],
            [
                {"text": "⏰ 1 hour ago", "callback_data": "time_1h"},
                {"text": "⏰ 3 hours ago", "callback_data": "time_3h"}
            ],
            [
                {"text": "⏰ 6 hours ago", "callback_data": "time_6h"},
                {"text": "⏰ 12 hours ago", "callback_data": "time_12h"}
            ],
            [{"text": "📅 Custom Time", "callback_data": "time_custom"}],
            [{"text": "❌ Cancel", "callback_data": "admin_broadcast"}]
        ])
        
        bot.send_message(chat_id, time_message, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_input_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing trade input: {str(e)}")

def time_selection_handler(update, chat_id):
    """Handle time selection for trade broadcasts."""
    try:
        callback_data = update['callback_query']['data']
        
        # Get the stored trade data
        global admin_pending_trade_data
        if 'admin_pending_trade_data' not in globals() or not admin_pending_trade_data:
            bot.send_message(chat_id, "❌ Trade data not found. Please start over.")
            return
        
        trade_text = admin_pending_trade_data['trade_text']
        admin_id = admin_pending_trade_data['admin_id']
        
        # Calculate the custom timestamp based on selection
        from datetime import datetime, timedelta
        
        if callback_data == "time_auto":
            custom_timestamp = datetime.utcnow()
            time_description = "now (auto)"
        elif callback_data == "time_5m":
            custom_timestamp = datetime.utcnow() - timedelta(minutes=5)
            time_description = "5 minutes ago"
        elif callback_data == "time_15m":
            custom_timestamp = datetime.utcnow() - timedelta(minutes=15)
            time_description = "15 minutes ago"
        elif callback_data == "time_1h":
            custom_timestamp = datetime.utcnow() - timedelta(hours=1)
            time_description = "1 hour ago"
        elif callback_data == "time_3h":
            custom_timestamp = datetime.utcnow() - timedelta(hours=3)
            time_description = "3 hours ago"
        elif callback_data == "time_6h":
            custom_timestamp = datetime.utcnow() - timedelta(hours=6)
            time_description = "6 hours ago"
        elif callback_data == "time_12h":
            custom_timestamp = datetime.utcnow() - timedelta(hours=12)
            time_description = "12 hours ago"
        elif callback_data == "time_custom":
            # For custom time, ask for manual input
            bot.send_message(
                chat_id,
                "📅 *Enter Custom Time*\n\n"
                "Format: `YYYY-MM-DD HH:MM` (24-hour format)\n"
                "Example: `2025-06-30 14:30`\n\n"
                "Or type 'now' for current time.",
                parse_mode="Markdown"
            )
            bot.add_message_listener(chat_id, "custom_time_input", custom_time_input_handler)
            return
        else:
            bot.send_message(chat_id, "❌ Invalid time selection.")
            return
        
        # Process the trade with the selected timestamp
        success = process_trade_broadcast_with_timestamp(trade_text, admin_id, custom_timestamp)
        
        if success:
            bot.send_message(
                chat_id,
                f"✅ *Trade broadcast successful!*\n\n"
                f"Trade time: {time_description}\n"
                f"Trade: {trade_text[:50]}{'...' if len(trade_text) > 50 else ''}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(chat_id, "❌ Failed to process trade broadcast.")
        
        # Clear the pending trade data
        admin_pending_trade_data = None
        
    except Exception as e:
        import logging
        logging.error(f"Error in time_selection_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing time selection: {str(e)}")

def custom_time_input_handler(update, chat_id, text):
    """Handle custom time input for trade broadcasts."""
    try:
        # Remove the message listener
        bot.remove_listener(chat_id)
        
        # Get the stored trade data
        global admin_pending_trade_data
        if 'admin_pending_trade_data' not in globals() or not admin_pending_trade_data:
            bot.send_message(chat_id, "❌ Trade data not found. Please start over.")
            return
        
        trade_text = admin_pending_trade_data['trade_text']
        admin_id = admin_pending_trade_data['admin_id']
        
        # Parse the custom time input
        from datetime import datetime
        
        if text.lower() == 'now':
            custom_timestamp = datetime.utcnow()
            time_description = "now"
        else:
            try:
                # Try parsing the input time
                custom_timestamp = datetime.strptime(text, "%Y-%m-%d %H:%M")
                time_description = text
            except ValueError:
                bot.send_message(
                    chat_id,
                    "❌ Invalid time format. Please use: YYYY-MM-DD HH:MM\n"
                    "Example: 2025-06-30 14:30"
                )
                return
        
        # Process the trade with the custom timestamp
        success = process_trade_broadcast_with_timestamp(trade_text, admin_id, custom_timestamp)
        
        if success:
            bot.send_message(
                chat_id,
                f"✅ *Trade broadcast successful!*\n\n"
                f"Trade time: {time_description}\n"
                f"Trade: {trade_text[:50]}{'...' if len(trade_text) > 50 else ''}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(chat_id, "❌ Failed to process trade broadcast.")
        
        # Clear the pending trade data
        admin_pending_trade_data = None
        
    except Exception as e:
        import logging
        logging.error(f"Error in custom_time_input_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing custom time: {str(e)}")

def process_trade_broadcast_with_timestamp(trade_text, admin_id, custom_timestamp):
    """Process trade broadcast with a custom timestamp."""
    try:
        # Import required modules
        import re
        import random
        from datetime import datetime
        
        with app.app_context():
            # Parse the trade message using the existing patterns
            buy_pattern = re.compile(r'^Buy\s+\$([A-Za-z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)', re.IGNORECASE)
            sell_pattern = re.compile(r'^Sell\s+\$([A-Za-z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)', re.IGNORECASE)
            
            buy_match = buy_pattern.match(trade_text.strip())
            sell_match = sell_pattern.match(trade_text.strip())
            
            if buy_match:
                token_name, price_str, amount_str, tx_link = buy_match.groups()
                entry_price = float(price_str)
                token_amount = float(amount_str)
                tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
                
                # Create BUY transaction records with custom timestamp
                from models import User, TradingPosition, Transaction
                
                users = User.query.filter(User.balance > 0).all()
                created_count = 0
                
                for user in users:
                    try:
                        # Calculate realistic allocation
                        if user.balance >= 10:
                            risk_percent = random.uniform(5, 15)
                        elif user.balance >= 5:
                            risk_percent = random.uniform(8, 25)
                        elif user.balance >= 2:
                            risk_percent = random.uniform(15, 35)
                        elif user.balance >= 0.5:
                            risk_percent = random.uniform(25, 50)
                        else:
                            risk_percent = random.uniform(40, 70)
                        
                        spent_sol = round(user.balance * (risk_percent / 100), 4)
                        realistic_amount = int(spent_sol / entry_price) if entry_price > 0 else 0
                        
                        if realistic_amount <= 0:
                            continue
                        
                        # Create TradingPosition with custom timestamp
                        position = TradingPosition(
                            user_id=user.id,
                            token_name=token_name.replace('$', ''),
                            amount=realistic_amount,
                            entry_price=entry_price,
                            current_price=entry_price,
                            timestamp=custom_timestamp,  # Use custom timestamp here
                            buy_timestamp=custom_timestamp,  # Also set buy_timestamp
                            status='open',
                            trade_type='snipe',
                            buy_tx_hash=tx_hash,
                            admin_id=admin_id
                        )
                        
                        db.session.add(position)
                        created_count += 1
                        
                    except Exception as e:
                        import logging
                        logging.error(f"Error creating position for user {user.id}: {e}")
                        continue
                
                db.session.commit()
                return created_count > 0
                
            elif sell_match:
                token_name, price_str, amount_str, tx_link = sell_match.groups()
                exit_price = float(price_str)
                token_amount = float(amount_str)
                tx_hash = tx_link.split('/')[-1] if '/' in tx_link else tx_link
                
                # Process SELL orders with custom timestamp
                from models import User, TradingPosition, Transaction, Profit
                
                # Find matching BUY positions
                open_positions = TradingPosition.query.filter_by(
                    token_name=token_name.replace('$', ''),
                    status='open'
                ).all()
                
                processed_count = 0
                
                for position in open_positions:
                    try:
                        # Calculate profit
                        roi_percentage = ((exit_price - position.entry_price) / position.entry_price) * 100
                        profit_amount = position.amount * (exit_price - position.entry_price)
                        
                        # Update position with custom timestamp
                        position.current_price = exit_price
                        position.exit_price = exit_price
                        position.sell_timestamp = custom_timestamp  # Use custom timestamp
                        position.sell_tx_hash = tx_hash
                        position.roi_percentage = roi_percentage
                        position.status = 'closed'
                        
                        # Update user balance
                        user = User.query.get(position.user_id)
                        if user:
                            user.balance += profit_amount
                            
                            # Create profit record with custom date
                            profit_record = Profit(
                                user_id=user.id,
                                amount=profit_amount,
                                percentage=roi_percentage,
                                date=custom_timestamp.date()  # Use custom date
                            )
                            db.session.add(profit_record)
                            
                            # Create transaction record with custom timestamp
                            transaction = Transaction(
                                user_id=user.id,
                                transaction_type='trade_profit' if profit_amount > 0 else 'trade_loss',
                                amount=profit_amount,
                                token_name=token_name.replace('$', ''),
                                price=exit_price,
                                timestamp=custom_timestamp,  # Use custom timestamp
                                status='completed',
                                tx_hash=tx_hash,
                                related_trade_id=position.id
                            )
                            db.session.add(transaction)
                            
                            processed_count += 1
                        
                    except Exception as e:
                        import logging
                        logging.error(f"Error processing sell for position {position.id}: {e}")
                        continue
                
                db.session.commit()
                return processed_count > 0
            
            return False
            
    except Exception as e:
        import logging
        logging.error(f"Error in process_trade_broadcast_with_timestamp: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False
        
def admin_broadcast_trade_message_handler(update, chat_id, text):
    """
    Process and send the trade information broadcast to all active users with personalized profit calculations.
    Enhanced Format: Buy $TOKEN CONTRACT_ADDRESS PRICE AMOUNT TX_LINK or Sell $TOKEN CONTRACT_ADDRESS PRICE AMOUNT TX_LINK
    
    Example: Buy $SCAI E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump 0.000002782 45000 https://solscan.io/tx/abc123
    """
    try:
        # Remove the message listener
        bot.remove_listener(chat_id)
        
        # Show processing message
        processing_msg = "⏳ Processing enhanced trade broadcast with market data..."
        bot.send_message(chat_id, processing_msg)
        
        # Import enhanced trade processor
        try:
            from utils.enhanced_trade_processor import enhanced_trade_processor
        except ImportError:
            bot.send_message(chat_id, "❌ Enhanced trade processor not available. Please check system.")
            return
        
        # Get admin ID from the update
        admin_id = str(update.get('message', {}).get('from', {}).get('id', 'admin'))
        
        # Parse trade message using enhanced processor
        trade_data = enhanced_trade_processor.parse_trade_message(text.strip())
        
        if not trade_data:
            error_msg = (
                "❌ *Invalid Trade Format*\n\n"
                "Please use the enhanced format:\n"
                "`Buy $SYMBOL CONTRACT_ADDRESS PRICE AMOUNT TX_LINK`\n"
                "`Sell $SYMBOL CONTRACT_ADDRESS PRICE AMOUNT TX_LINK`\n\n"
                "Example:\n"
                "`Buy $SCAI E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump 0.000002782 45000 https://solscan.io/tx/abc123`"
            )
            bot.send_message(chat_id, error_msg, parse_mode="Markdown")
            return
        
        success = False
        response = ""
        
        # Check if custom timestamp was set from time selection
        custom_timestamp = None
        if hasattr(bot, '_custom_timestamp') and bot._custom_timestamp:
            custom_timestamp = bot._custom_timestamp
            bot._custom_timestamp = None  # Clear after use
        
        # Process trade using enhanced system
        if trade_data['trade_type'] == 'buy':
            # Process BUY trade with DEX Screener integration
            success, response, affected_count = enhanced_trade_processor.process_buy_trade(
                trade_data, admin_id, custom_timestamp
            )
            
            if success:
                response = (
                    f"✅ *Enhanced BUY Order Executed*\n\n"
                    f"🎯 *Token:* {trade_data['symbol']}\n"
                    f"📊 *Contract:* {trade_data['contract_address'][:8]}...{trade_data['contract_address'][-8:]}\n"
                    f"💰 *Entry Price:* {trade_data['price']:.8f} SOL\n"
                    f"👥 *Users Affected:* {affected_count}\n"
                    f"🔗 [Transaction]({trade_data['tx_link']})\n\n"
                    f"*All positions now enriched with real market data from DEX Screener!*"
                )
                
        elif trade_data['trade_type'] == 'sell':
            # Process SELL trade with DEX Screener integration
            success, response, affected_count = enhanced_trade_processor.process_sell_trade(
                trade_data, admin_id, custom_timestamp
            )
            
            if success:
                response = (
                    f"✅ *Enhanced SELL Order Executed*\n\n"
                    f"🎯 *Token:* {trade_data['symbol']}\n"
                    f"📊 *Contract:* {trade_data['contract_address'][:8]}...{trade_data['contract_address'][-8:]}\n"
                    f"💰 *Exit Price:* {trade_data['price']:.8f} SOL\n"
                    f"👥 *Positions Closed:* {affected_count}\n"
                    f"🔗 [Transaction]({trade_data['tx_link']})\n\n"
                    f"*All exits now include authentic market data and realistic ownership metrics!*"
                )
        else:
            response = "❌ Invalid trade format. Please check your message format."
        
        # Send the response to the admin
        bot.send_message(chat_id, response, parse_mode="Markdown")
        
        # If successful, add a button to return to the admin panel
        if success:
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_broadcast"}]
            ])
            
            bot.send_message(
                chat_id,
                "What would you like to do next?",
                reply_markup=keyboard
            )
    
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_trade_message_handler: {str(e)}")
        bot.send_message(chat_id, f"❌ Error processing trade: {str(e)}")

