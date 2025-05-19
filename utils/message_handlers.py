"""
Message Handlers Utility

This module provides helper functions for handling message sending with automatic cleanup
to maintain a clean chat interface as users move through different conversation flows.
"""

import logging
import asyncio

# Handle different telegram library versions gracefully
try:
    # Try importing from python-telegram-bot v20+
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import ContextTypes
except ImportError:
    # Create mock classes for type checking when imports fail
    class Update:
        """Mock Update class for type checking"""
        pass
    
    class InlineKeyboardMarkup:
        """Mock InlineKeyboardMarkup class for type checking"""
        pass
    
    class InlineKeyboardButton:
        """Mock InlineKeyboardButton class for type checking"""
        pass
    
    class ContextTypes:
        """Mock ContextTypes class for type checking"""
        DEFAULT_TYPE = None

# Import the message cleanup system
from utils.message_cleanup import (
    send_message_with_flow_transition,
    transition_flow_state,
    track_flow_message,
    delete_old_message,
    delete_message_after_delay,
    edit_message_with_timed_deletion,
    track_and_delete_user_message
)

logger = logging.getLogger(__name__)

async def send_or_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             text: str, message_type: str, flow_state: str = "",
                             reply_markup = None, parse_mode: str = "Markdown", 
                             delete_after: int = 30) -> None:
    """
    Send a new message or edit the existing message from a callback query
    with automatic message cleanup.
    
    Args:
        update (Update): The update object from Telegram
        context (ContextTypes.DEFAULT_TYPE): The context object
        text (str): The message text
        message_type (str): The type of message for cleanup tracking
        flow_state (str, optional): The flow state to transition to
        reply_markup: Optional keyboard markup
        parse_mode (str): The parse mode for the message
        delete_after (int): Number of seconds to wait before auto-deleting the message (0 to disable)
    """
    # Check if this is a message type that should not auto-delete
    persistent_message_types = [
        'deposit_receipt',      # Deposit confirmations after processing
        'withdrawal_receipt',   # Withdrawal confirmations after processing
        'trade_history',        # Trade history records
        'transaction_history',  # Transaction records
        'important_notice',     # Critical system notifications
        'support_ticket',       # Support ticket submissions
        'admin_message'         # Messages from admins
    ]
    
    # Don't auto-delete persistent message types
    if message_type in persistent_message_types:
        delete_after = 0
        
    if update.callback_query:
        # This is a callback query, edit the message
        query = update.callback_query
        await query.answer()
        
        # If we're transitioning flow state, clean up old messages first
        if flow_state:
            await transition_flow_state(query.message.chat_id, flow_state, context.bot)
            
        # Edit the message with auto-deletion if needed
        if delete_after > 0:
            await edit_message_with_timed_deletion(
                context.bot,
                query.message.chat_id,
                query.message.message_id,
                text,
                parse_mode,
                reply_markup,
                delete_after
            )
        else:
            # Use regular edit without auto-deletion
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        
        # Track the edited message for future cleanup
        if flow_state:
            await track_flow_message(query.message.chat_id, query.message.message_id, flow_state)
    else:
        # This is a direct command, send a new message with cleanup
        try:
            result = await send_message_with_flow_transition(
                context.bot,
                update.effective_chat.id,
                text,
                message_type,
                flow_state,
                parse_mode,
                reply_markup,
                cleanup_old=True,
                delete_after=delete_after
            )
            return result
        except Exception as e:
            logger.error(f"Error sending message with flow transition: {e}")
            # Fallback to regular send_message
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            
            # Schedule deletion if needed (even in fallback case)
            if delete_after > 0 and message and hasattr(message, 'message_id'):
                await delete_message_after_delay(
                    context.bot, 
                    update.effective_chat.id, 
                    message.message_id, 
                    delete_after
                )
                
            return message
            
async def cleanup_previous_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  message_types: list) -> None:
    """
    Clean up previous messages of specific types.
    
    Args:
        update (Update): The update object from Telegram
        context (ContextTypes.DEFAULT_TYPE): The context object  
        message_types (list): List of message types to clean up
    """
    chat_id = update.effective_chat.id
    for msg_type in message_types:
        await delete_old_message(chat_id, msg_type)

# Simplified handler functions for integration with all parts of the bot

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             text: str, reply_markup=None):
    """Send welcome message with cleanup of any previous welcome messages"""
    return await send_or_edit_message(
        update, context, text, 'welcome_message', 'welcome', reply_markup
    )

async def send_start_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           text: str, reply_markup=None):
    """Send start command response with transition from welcome to start state"""
    return await send_or_edit_message(
        update, context, text, 'start_message', 'start', reply_markup
    )

async def send_dashboard_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               text: str, reply_markup=None):
    """Send dashboard message with transition to dashboard state"""
    return await send_or_edit_message(
        update, context, text, 'dashboard', 'dashboard', reply_markup
    )

async def send_deposit_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  text: str, reply_markup=None):
    """Send deposit instructions with transition to deposit state"""
    return await send_or_edit_message(
        update, context, text, 'deposit_instruction', 'deposit', reply_markup
    )

async def send_deposit_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  text: str, reply_markup=None):
    """Send deposit confirmation with transition to confirmation state"""
    return await send_or_edit_message(
        update, context, text, 'deposit_confirmation', 'deposit_confirmation', reply_markup
    )

async def send_withdraw_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   text: str, reply_markup=None):
    """Send withdrawal instructions with transition to withdraw state"""
    return await send_or_edit_message(
        update, context, text, 'withdraw_instruction', 'withdraw', reply_markup
    )

async def send_referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           text: str, reply_markup=None):
    """Send referral program information with transition to referral state"""
    return await send_or_edit_message(
        update, context, text, 'referral_info', 'referral', reply_markup
    )

async def send_settings_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              text: str, reply_markup=None):
    """Send settings information with transition to settings state"""
    return await send_or_edit_message(
        update, context, text, 'settings_menu', 'settings', reply_markup
    )

async def send_help_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          text: str, reply_markup=None):
    """Send help information with transition to help state"""
    return await send_or_edit_message(
        update, context, text, 'help_menu', 'help', reply_markup
    )

async def handle_user_message_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE, delay_seconds: int = 30) -> None:
    """
    Track and schedule auto-deletion of a user's message
    
    Args:
        update (Update): The update object from Telegram
        context (ContextTypes.DEFAULT_TYPE): The context object
        delay_seconds (int): Number of seconds to wait before deleting
    """
    # Only process if we have a message from the user
    if not update.message:
        return
    
    try:
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        
        # Schedule the message for auto-deletion
        await track_and_delete_user_message(context.bot, chat_id, message_id, delay_seconds)
        logger.debug(f"Scheduled user message {message_id} for deletion after {delay_seconds}s")
    except Exception as e:
        logger.error(f"Error in handle_user_message_cleanup: {e}")