"""
Telegram Message Formatter - Safe Markdown Handling
==================================================
This module provides robust message formatting for Telegram bot messages,
ensuring special characters are properly escaped to prevent HTTP 400 errors.
"""

import re
import logging
from typing import Optional, Dict, Any


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for MarkdownV2 format.
    
    Args:
        text (str): Text to escape
        
    Returns:
        str: Escaped text safe for MarkdownV2
    """
    if not text:
        return ""
    
    # Characters that need escaping in MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    escaped_text = str(text)
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    
    return escaped_text


def escape_markdown_v1(text: str) -> str:
    """
    Escape special characters for Markdown format.
    
    Args:
        text (str): Text to escape
        
    Returns:
        str: Escaped text safe for Markdown
    """
    if not text:
        return ""
    
    # Characters that need escaping in Markdown
    special_chars = ['_', '*', '[', ']', '`']
    
    escaped_text = str(text)
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    
    return escaped_text


def format_balance_adjustment_user_found(username: str, telegram_id: str, balance: float) -> tuple:
    """
    Format user found message for balance adjustment.
    
    Args:
        username (str): User's username (may contain special chars)
        telegram_id (str): User's telegram ID
        balance (float): Current balance
        
    Returns:
        tuple: (message_text, parse_mode)
    """
    try:
        # Try Markdown format first
        username_display = f"@{username}" if username else "No username"
        escaped_username = escape_markdown_v1(username_display)
        escaped_telegram_id = escape_markdown_v1(str(telegram_id))
        
        markdown_message = (
            f"🔍 *USER FOUND*\n\n"
            f"User: {escaped_username}\n"
            f"Telegram ID: `{escaped_telegram_id}`\n"
            f"Current Balance: *{balance:.4f} SOL*\n\n"
            f"💰 Enter adjustment amount:\n"
            f"• Positive number to add (e.g., 5.5)\n"
            f"• Negative number to remove (e.g., -3.2)\n"
            f"• Type 'cancel' to abort"
        )
        
        return markdown_message, "Markdown"
        
    except Exception as e:
        logging.warning(f"Failed to create Markdown message: {e}. Using plain text.")
        
        # Fallback to plain text
        username_display = f"@{username}" if username else "No username"
        plain_message = (
            f"USER FOUND\n\n"
            f"User: {username_display}\n"
            f"Telegram ID: {telegram_id}\n"
            f"Current Balance: {balance:.4f} SOL\n\n"
            f"Enter adjustment amount:\n"
            f"+ for add funds (e.g. 5.5)\n"
            f"- for remove funds (e.g. -3.2)\n"
            f"Type 'cancel' to abort"
        )
        
        return plain_message, None


def format_balance_adjustment_confirmation(telegram_id: str, current_balance: float, 
                                         adjustment_amount: float, reason: str) -> tuple:
    """
    Format confirmation message for balance adjustment.
    
    Args:
        telegram_id (str): User's telegram ID
        current_balance (float): Current balance
        adjustment_amount (float): Adjustment amount
        reason (str): Reason for adjustment
        
    Returns:
        tuple: (message_text, parse_mode)
    """
    try:
        # Calculate new balance
        new_balance = current_balance + adjustment_amount
        plus_minus = '➕' if adjustment_amount > 0 else '➖'
        adjustment_abs = abs(adjustment_amount)
        
        # Escape special characters
        escaped_telegram_id = escape_markdown_v1(str(telegram_id))
        escaped_reason = escape_markdown_v1(str(reason))
        
        markdown_message = (
            f"⚠️ *Confirm Balance Adjustment*\n\n"
            f"User ID: `{escaped_telegram_id}`\n"
            f"Current Balance: *{current_balance:.4f} SOL*\n"
            f"Adjustment: {plus_minus} *{adjustment_abs:.4f} SOL*\n"
            f"New Balance: *{new_balance:.4f} SOL*\n"
            f"Reason: _{escaped_reason}_\n\n"
            f"Are you sure you want to proceed?"
        )
        
        return markdown_message, "Markdown"
        
    except Exception as e:
        logging.warning(f"Failed to create Markdown confirmation: {e}. Using plain text.")
        
        # Fallback to plain text
        new_balance = current_balance + adjustment_amount
        plus_minus = '+' if adjustment_amount > 0 else '-'
        adjustment_abs = abs(adjustment_amount)
        
        plain_message = (
            f"CONFIRM BALANCE ADJUSTMENT\n\n"
            f"User ID: {telegram_id}\n"
            f"Current Balance: {current_balance:.4f} SOL\n"
            f"Adjustment: {plus_minus}{adjustment_abs:.4f} SOL\n"
            f"New Balance: {new_balance:.4f} SOL\n"
            f"Reason: {reason}\n\n"
            f"Are you sure you want to proceed?"
        )
        
        return plain_message, None


def format_balance_adjustment_result(success: bool, amount: float, message: str) -> tuple:
    """
    Format result message for balance adjustment.
    
    Args:
        success (bool): Whether the adjustment was successful
        amount (float): Adjustment amount
        message (str): Result message from balance manager
        
    Returns:
        tuple: (message_text, parse_mode)
    """
    try:
        if success:
            action = "added" if amount > 0 else "deducted"
            escaped_message = escape_markdown_v1(str(message))
            
            markdown_message = (
                f"✅ *Balance adjustment completed!*\n\n"
                f"Amount: *{abs(amount):.4f} SOL {action}*\n\n"
                f"{escaped_message}"
            )
            
            return markdown_message, "Markdown"
        else:
            escaped_message = escape_markdown_v1(str(message))
            
            markdown_message = (
                f"❌ *Balance adjustment failed*\n\n"
                f"{escaped_message}"
            )
            
            return markdown_message, "Markdown"
            
    except Exception as e:
        logging.warning(f"Failed to create Markdown result: {e}. Using plain text.")
        
        # Fallback to plain text
        if success:
            action = "added" if amount > 0 else "deducted"
            plain_message = (
                f"Balance adjustment completed!\n\n"
                f"{abs(amount):.4f} SOL {action}\n\n"
                f"{message}"
            )
        else:
            plain_message = f"Balance adjustment failed: {message}"
        
        return plain_message, None


def safe_send_message(bot, chat_id: str, message_text: str, parse_mode: Optional[str] = None, 
                     reply_markup: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> Dict[str, Any]:
    """
    Safely send a message with automatic fallback to plain text on Markdown errors.
    
    Args:
        bot: Telegram bot instance
        chat_id (str): Chat ID to send message to
        message_text (str): Message text to send
        parse_mode (str, optional): Parse mode ("Markdown", "MarkdownV2", or None)
        reply_markup (dict, optional): Reply markup for inline keyboards
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        dict: Response from Telegram API
    """
    logging.info(f"Attempting to send message to chat {chat_id}")
    logging.info(f"Message length: {len(message_text)} characters")
    logging.info(f"Parse mode: {parse_mode}")
    logging.info(f"Message preview: {repr(message_text[:200])}")
    
    # First attempt with requested parse mode
    try:
        response = bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        
        if response.get("ok", False):
            logging.info("Message sent successfully")
            return response
        else:
            logging.warning(f"Message failed with response: {response}")
            
    except Exception as e:
        logging.error(f"Error sending message with {parse_mode} mode: {e}")
        logging.error(f"Full message content: {repr(message_text)}")
    
    # Retry with plain text if Markdown failed
    if parse_mode and max_retries > 0:
        logging.info("Retrying with plain text format")
        
        try:
            # Remove markdown formatting for plain text
            plain_text = remove_markdown_formatting(message_text)
            
            response = bot.send_message(
                chat_id=chat_id,
                text=plain_text,
                parse_mode=None,
                reply_markup=reply_markup
            )
            
            if response.get("ok", False):
                logging.info("Message sent successfully in plain text")
                return response
            else:
                logging.error(f"Plain text message also failed: {response}")
                
        except Exception as e:
            logging.error(f"Error sending plain text message: {e}")
    
    # Final fallback - minimal message
    try:
        minimal_message = "Balance adjustment in progress. Please check again in a moment."
        response = bot.send_message(
            chat_id=chat_id,
            text=minimal_message,
            parse_mode=None,
            reply_markup=reply_markup
        )
        logging.info("Sent minimal fallback message")
        return response
        
    except Exception as e:
        logging.error(f"Even minimal message failed: {e}")
        return {"ok": False, "error": str(e)}


def remove_markdown_formatting(text: str) -> str:
    """
    Remove Markdown formatting characters from text.
    
    Args:
        text (str): Text with Markdown formatting
        
    Returns:
        str: Plain text without formatting
    """
    if not text:
        return ""
    
    # Remove markdown formatting
    plain_text = text
    
    # Remove bold
    plain_text = re.sub(r'\*([^*]+)\*', r'\1', plain_text)
    
    # Remove italic
    plain_text = re.sub(r'_([^_]+)_', r'\1', plain_text)
    
    # Remove code
    plain_text = re.sub(r'`([^`]+)`', r'\1', plain_text)
    
    # Remove escaped characters
    plain_text = re.sub(r'\\(.)', r'\1', plain_text)
    
    return plain_text


def test_formatter():
    """Test the formatter with problematic characters."""
    test_cases = [
        ("user_name", "123456789", 1.2345),
        ("user@test", "987654321", 0.0),
        ("user_with_underscores", "555555555", 10.5),
        ("user*special*chars", "111111111", 5.0),
        ("user[brackets]", "222222222", 3.33),
    ]
    
    print("Testing message formatter:")
    for username, telegram_id, balance in test_cases:
        message, parse_mode = format_balance_adjustment_user_found(username, telegram_id, balance)
        print(f"\nUsername: {username}")
        print(f"Parse mode: {parse_mode}")
        print(f"Message: {message[:100]}...")


if __name__ == "__main__":
    test_formatter()