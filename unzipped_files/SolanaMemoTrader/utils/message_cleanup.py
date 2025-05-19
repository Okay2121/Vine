"""
Message Cleanup Module for Telegram Bot

This module handles automatic deletion of old messages to keep the user's chat clean
and reduce clutter, especially for repetitive notification types like trading updates.
It also includes functionality to automatically delete messages after a specified delay.
"""

import logging
import os
import asyncio
from datetime import datetime
import requests
from threading import Lock
import time

# Import required for timeout parameter
import aiohttp

# Define a generic Bot interface for type checking that doesn't depend on imports
class TelegramBotInterface:
    """Interface for Telegram bot operations that doesn't depend on telegram imports"""
    async def delete_message(self, chat_id, message_id):
        """Delete a message"""
        pass
    
    async def send_message(self, chat_id, text, **kwargs):
        """Send a message"""
        pass
    
    async def edit_message_text(self, chat_id, message_id, text, **kwargs):
        """Edit a message"""
        pass

# Configure logging
logger = logging.getLogger(__name__)

# Dictionary to track message IDs by chat_id and message type
# Structure: {chat_id: {message_type: {'id': message_id, 'timestamp': datetime}}}
message_tracking = {}
message_lock = Lock()

# Dictionary to track user flow state
# Structure: {chat_id: {'state': current_state, 'messages': [message_ids]}}
user_flow_state = {}
flow_lock = Lock()

# Message types that should be tracked and cleaned up
TRACKED_MESSAGE_TYPES = [
    'trading_update',       # Auto-trading updates
    'balance_update',       # Balance notifications
    'roi_streak',           # ROI streak updates
    'inactivity_nudge',     # Reminders to deposit/interact
    'dashboard',            # Dashboard displays
    'settings_menu',        # Settings menus
    'referral_menu',        # Referral program menus
    'help_menu',            # Help/FAQ displays
    'main_menu',            # Main menu displays
    'welcome_message',      # Initial greeting before /start
    'start_message',        # Response to /start command
    'deposit_instruction',  # Instructions for deposits
    'deposit_pending',      # Pending deposit confirmation
    'deposit_confirmation', # User confirmed deposit was made
    'wallet_request',       # Requesting wallet address
    'referral_stats',       # Referral program statistics
    'referral_info',        # Referral program information
    'settings_update',      # Settings update confirmation
    'withdraw_instruction', # Withdrawal instructions
    'withdraw_pending',     # Pending withdrawal confirmation
    'custom_amount_request', # Request for custom amount input
    'user_message'          # Messages from users
]

# Message types that should persist (never delete)
PERSISTENT_MESSAGE_TYPES = [
    'deposit_receipt',      # Deposit confirmations after processing
    'withdrawal_receipt',   # Withdrawal confirmations after processing
    'trade_history',        # Trade history records
    'transaction_history',  # Transaction records
    'important_notice',     # Critical system notifications
    'support_ticket',       # Support ticket submissions
    'admin_message'         # Messages from admins
]

# User flow states and their corresponding message types to delete when transitioning
FLOW_TRANSITIONS = {
    'welcome_to_start': ['welcome_message'],
    'start_to_dashboard': ['start_message'],
    'dashboard_to_deposit': ['dashboard'],
    'deposit_to_confirmation': ['deposit_instruction', 'wallet_request'],
    'confirmation_to_dashboard': ['deposit_pending', 'deposit_confirmation'],
    'dashboard_to_withdraw': ['dashboard'],
    'withdraw_to_confirmation': ['withdraw_instruction', 'custom_amount_request'],
    'any_to_referral': ['dashboard', 'deposit_instruction', 'withdraw_instruction'],
    'any_to_settings': ['dashboard', 'referral_menu', 'help_menu'],
    'any_to_dashboard': ['settings_menu', 'referral_menu', 'help_menu', 'withdraw_pending']
}

def track_message(chat_id, message_id, message_type):
    """
    Track a message sent to a user for potential future deletion
    
    Args:
        chat_id (int): Telegram chat ID
        message_id (int): Telegram message ID
        message_type (str): Type of message for categorization
    """
    if message_type not in TRACKED_MESSAGE_TYPES:
        return
        
    with message_lock:
        # Initialize chat tracking if needed
        if chat_id not in message_tracking:
            message_tracking[chat_id] = {}
            
        # Track the message
        message_tracking[chat_id][message_type] = {
            'id': message_id,
            'timestamp': datetime.utcnow()
        }
        
    logger.debug(f"Tracked message {message_id} of type {message_type} for chat {chat_id}")

async def delete_old_message(chat_id, message_type):
    """
    Delete the previous message of a specific type for a chat
    
    Args:
        chat_id (int): Telegram chat ID
        message_type (str): Type of message to delete
        
    Returns:
        bool: True if a message was deleted, False otherwise
    """
    if message_type in PERSISTENT_MESSAGE_TYPES:
        return False
        
    with message_lock:
        # Check if we have a message to delete
        if (chat_id not in message_tracking or 
            message_type not in message_tracking[chat_id]):
            return False
            
        # Get the message ID to delete
        old_message = message_tracking[chat_id][message_type]
        old_message_id = old_message['id']
        
        # Remove the message from tracking
        del message_tracking[chat_id][message_type]
        
    # Delete the message via Telegram API
    success = await delete_telegram_message(chat_id, old_message_id)
    
    if success:
        logger.debug(f"Deleted old message {old_message_id} of type {message_type} for chat {chat_id}")
    
    return success

async def delete_telegram_message(chat_id, message_id):
    """
    Delete a message using the Telegram Bot API
    
    Args:
        chat_id (int): Telegram chat ID
        message_id (int): Telegram message ID to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("No Telegram bot token available for message deletion")
            return False
        
        # Skip trying to use bot method directly since we're using the API call anyway
        # This avoids import errors when bot libraries are not available
        logger.debug(f"Using direct API call to delete message {message_id} for chat {chat_id}")
        
        # Direct API call fallback        
        url = f"https://api.telegram.org/bot{token}/deleteMessage"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=timeout) as response:
                success = response.status == 200
                
                if not success:
                    response_json = await response.json()
                    # Don't log errors for messages that are already deleted or too old
                    if ('description' in response_json and 
                        ('message to delete not found' in response_json['description'].lower() or
                         'message can\'t be deleted' in response_json['description'].lower())):
                        # This is normal, message may already be deleted or too old
                        return True
                    else:
                        logger.warning(f"Failed to delete message {message_id}: {await response.text()}")
                
                return success
    
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {e}")
        return False

async def send_message_with_cleanup(bot, chat_id, text, message_type, parse_mode="Markdown", reply_markup=None):
    """
    Send a message and clean up any previous message of the same type
    
    Args:
        bot: Telegram bot instance with send_message method
        chat_id (int): Telegram chat ID
        text (str): Message text
        message_type (str): Type of message for categorization
        parse_mode (str): Telegram parse mode (Markdown or HTML)
        reply_markup: Optional keyboard markup
        
    Returns:
        The result of the send_message call
    """
    # Delete old message of the same type if it exists
    await delete_old_message(chat_id, message_type)
    
    # Send the new message
    result = await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    
    # Track this new message
    if result and hasattr(result, 'message_id'):
        track_message(chat_id, result.message_id, message_type)
    
    return result

async def edit_message_with_cleanup(bot, chat_id, message_id, text, message_type, parse_mode="Markdown", reply_markup=None):
    """
    Edit a message and track it for future cleanup
    
    Args:
        bot: Telegram bot instance with edit_message_text method
        chat_id (int): Telegram chat ID
        message_id (int): Message ID to edit
        text (str): New message text
        message_type (str): Type of message for categorization
        parse_mode (str): Telegram parse mode (Markdown or HTML)
        reply_markup: Optional keyboard markup
        
    Returns:
        The result of the edit_message_text call
    """
    # Edit the message
    result = await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup
    )
    
    # Track this edited message
    if result and hasattr(result, 'message_id'):
        track_message(chat_id, result.message_id, message_type)
    
    return result

async def track_flow_message(chat_id, message_id, flow_state=None):
    """
    Track a message in the user's flow
    
    Args:
        chat_id (int): Telegram chat ID
        message_id (int): Telegram message ID
        flow_state (str): Optional current flow state of the user
    """
    with flow_lock:
        # Initialize user flow tracking if needed
        if chat_id not in user_flow_state:
            user_flow_state[chat_id] = {
                'state': flow_state,
                'messages': []
            }
        
        # Update the state if provided
        if flow_state:
            user_flow_state[chat_id]['state'] = flow_state
            
        # Track the message
        if message_id not in user_flow_state[chat_id]['messages']:
            user_flow_state[chat_id]['messages'].append(message_id)
    
    logger.debug(f"Tracked flow message {message_id} for user {chat_id}, state: {flow_state}")

async def get_user_flow_state(chat_id):
    """
    Get the current flow state for a user
    
    Args:
        chat_id (int): Telegram chat ID
        
    Returns:
        str: Current flow state or None if not tracked
    """
    with flow_lock:
        if chat_id in user_flow_state:
            return user_flow_state[chat_id]['state']
    return None

async def transition_flow_state(chat_id, new_state, bot=None):
    """
    Transition a user to a new flow state and clean up messages from previous state
    
    Args:
        chat_id (int): Telegram chat ID
        new_state (str): New flow state for the user
        bot: Optional Telegram bot instance with delete_message method
        
    Returns:
        bool: Success of the transition
    """
    current_state = await get_user_flow_state(chat_id)
    transition_key = f"{current_state}_to_{new_state}" if current_state else f"any_to_{new_state}"
    
    # Check if we have a defined transition
    if transition_key not in FLOW_TRANSITIONS and f"any_to_{new_state}" not in FLOW_TRANSITIONS:
        logger.debug(f"No transition defined from {current_state} to {new_state}")
        with flow_lock:
            if chat_id in user_flow_state:
                user_flow_state[chat_id]['state'] = new_state
        return False
    
    # Get the list of message types to delete from our transition map
    message_types_to_delete = FLOW_TRANSITIONS.get(transition_key, 
                                                FLOW_TRANSITIONS.get(f"any_to_{new_state}", []))
    
    # Delete old messages of the specified types
    for msg_type in message_types_to_delete:
        await delete_old_message(chat_id, msg_type)
    
    # Update the user's flow state
    with flow_lock:
        if chat_id in user_flow_state:
            user_flow_state[chat_id]['state'] = new_state
            # Optionally clean up old tracked messages with bot reference
            if bot and user_flow_state[chat_id]['messages']:
                old_messages = user_flow_state[chat_id]['messages'].copy()
                user_flow_state[chat_id]['messages'] = []
                
                for msg_id in old_messages:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    except Exception as e:
                        # Ignore errors for messages that can't be deleted
                        pass
        else:
            user_flow_state[chat_id] = {'state': new_state, 'messages': []}
    
    logger.info(f"Transitioned user {chat_id} from {current_state} to {new_state}")
    return True

async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds=30):
    """
    Delete a message after a specified delay
    
    Args:
        bot: Telegram bot instance with delete_message method
        chat_id (int): Telegram chat ID
        message_id (int): Message ID to delete
        delay_seconds (int): Number of seconds to wait before deleting
        
    Returns:
        bool: True if message was deleted successfully, False otherwise
    """
    logger.debug(f"Scheduled message {message_id} for deletion after {delay_seconds} seconds")
    
    # Wait for the specified delay
    await asyncio.sleep(delay_seconds)
    
    try:
        # Try to delete the message
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"Successfully deleted message {message_id} after {delay_seconds} second delay")
        return True
    except Exception as e:
        # Message might already be deleted or too old
        if "message to delete not found" in str(e).lower() or "message can't be deleted" in str(e).lower():
            logger.debug(f"Message {message_id} already deleted or too old")
            return True
        logger.error(f"Failed to delete message {message_id} after delay: {e}")
        return False

async def send_message_with_timed_deletion(bot, chat_id, text, parse_mode="Markdown", 
                                     reply_markup=None, delete_after=30):
    """
    Send a message that will be automatically deleted after a specified time period
    
    Args:
        bot: Telegram bot instance with send_message method
        chat_id (int): Telegram chat ID
        text (str): Message text
        parse_mode (str): Telegram parse mode (Markdown or HTML)
        reply_markup: Optional keyboard markup
        delete_after (int): Seconds to wait before deleting the message (0 to disable)
        
    Returns:
        The result of the send_message call
    """
    # Send the message
    result = await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    
    # Schedule deletion if requested
    if delete_after > 0 and result and hasattr(result, 'message_id'):
        # Start deletion task in background
        asyncio.create_task(delete_message_after_delay(bot, chat_id, result.message_id, delete_after))
    
    return result

async def edit_message_with_timed_deletion(bot, chat_id, message_id, text, parse_mode="Markdown", 
                                     reply_markup=None, delete_after=30):
    """
    Edit a message and schedule it to be automatically deleted after a specified time period
    
    Args:
        bot: Telegram bot instance with edit_message_text and delete_message methods
        chat_id (int): Telegram chat ID
        message_id (int): Message ID to edit
        text (str): New message text
        parse_mode (str): Telegram parse mode (Markdown or HTML)
        reply_markup: Optional keyboard markup
        delete_after (int): Seconds to wait before deleting the message (0 to disable)
        
    Returns:
        The result of the edit_message_text call
    """
    # Edit the message
    try:
        result = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        
        # Schedule deletion if requested
        if delete_after > 0:
            # Start deletion task in background
            asyncio.create_task(delete_message_after_delay(bot, chat_id, message_id, delete_after))
        
        return result
    except Exception as e:
        logger.error(f"Failed to edit message with timed deletion: {e}")
        return None

async def delete_user_message_after_delay(bot, chat_id, user_message_id, delay_seconds=30):
    """
    Delete a user's message after a specified delay
    
    Args:
        bot: Telegram bot instance with delete_message method
        chat_id (int): Telegram chat ID
        user_message_id (int): User's message ID to delete
        delay_seconds (int): Number of seconds to wait before deleting
        
    Returns:
        bool: True if message was deleted successfully, False otherwise
    """
    logger.debug(f"Scheduled user message {user_message_id} for deletion after {delay_seconds} seconds")
    
    # Wait for the specified delay
    await asyncio.sleep(delay_seconds)
    
    try:
        # Try to delete the user's message
        await bot.delete_message(chat_id=chat_id, message_id=user_message_id)
        logger.debug(f"Successfully deleted user message {user_message_id} after {delay_seconds} second delay")
        return True
    except Exception as e:
        # Message might already be deleted or too old
        if "message to delete not found" in str(e).lower() or "message can't be deleted" in str(e).lower():
            logger.debug(f"User message {user_message_id} already deleted or too old")
            return True
        # Permission error is common for user messages
        elif "not enough rights to delete" in str(e).lower():
            logger.warning(f"Bot doesn't have permission to delete user message {user_message_id}")
            return False
        logger.error(f"Failed to delete user message {user_message_id} after delay: {e}")
        return False

async def track_and_delete_user_message(bot, chat_id, user_message_id, delay_seconds=30):
    """
    Track and schedule deletion of a user's message
    
    Args:
        bot: Telegram bot instance with delete_message method
        chat_id (int): Telegram chat ID
        user_message_id (int): User's message ID to delete
        delay_seconds (int): Number of seconds to wait before deleting
        
    Returns:
        None
    """
    # Track the user message for potential future reference
    track_message(chat_id, user_message_id, 'user_message')
    
    # Schedule its deletion
    if delay_seconds > 0:
        asyncio.create_task(delete_user_message_after_delay(bot, chat_id, user_message_id, delay_seconds))

async def send_message_with_flow_transition(bot, chat_id, text, message_type, flow_state=None, 
                                         parse_mode="Markdown", reply_markup=None, cleanup_old=True,
                                         delete_after=30):
    """
    Send a message with flow state transition and automatic cleanup
    
    Args:
        bot: Telegram bot instance with necessary methods
        chat_id (int): Telegram chat ID
        text (str): Message text
        message_type (str): Type of message for categorization
        flow_state (str): Optional new flow state to transition to
        parse_mode (str): Telegram parse mode (Markdown or HTML)
        reply_markup: Optional keyboard markup
        cleanup_old (bool): Whether to clean up old messages
        delete_after (int): Seconds to wait before deleting (0 to disable)
        
    Returns:
        The result of the send_message call
    """
    # If cleaning up old messages is requested
    if cleanup_old:
        await delete_old_message(chat_id, message_type)
    
    # If transitioning flow state, handle that
    if flow_state:
        await transition_flow_state(chat_id, flow_state, bot)
    
    # Send the message with auto-deletion if requested
    if delete_after > 0:
        result = await send_message_with_timed_deletion(
            bot, chat_id, text, parse_mode, reply_markup, delete_after
        )
    else:
        # Send without auto-deletion
        result = await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    
    # Track the message
    if result and hasattr(result, 'message_id'):
        track_message(chat_id, result.message_id, message_type)
        
        # If in a flow, track it there too
        if flow_state:
            await track_flow_message(chat_id, result.message_id, flow_state)
    
    return result