#!/usr/bin/env python
"""
Yield Tracker & Trade History Module for Telegram Bot
This module adds realistic trade simulations, yield tracking, and token history
to the existing Telegram bot while preserving the original UI and commands.
"""
import logging
import os
import json
import requests
import random
from datetime import datetime, timedelta
from threading import Lock
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Storage file path
DATA_FILE = 'yield_data.json'

# API endpoint for recent tokens
PUMP_FUN_API = "https://client-api.pump.fun/tokens/recent"

# Lock for file operations
file_lock = Lock()

# Initialize module data
yield_data = {}


def get_recent_tokens():
    """
    Fetch recent tokens from the Pump.fun API.
    Returns a list of token data or an empty list if the request fails.
    """
    try:
        # Add a User-Agent header to avoid potential blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
        }
        
        response = requests.get(PUMP_FUN_API, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        else:
            logger.error(f"Failed to fetch tokens: {response.status_code}")
            
            # If API returns non-200 error, we'll still return empty list
            # but log the response body for debugging
            try:
                error_body = response.text[:200]  # Limit length for log
                logger.error(f"API response body: {error_body}")
            except:
                pass
                
            return []
    except Exception as e:
        logger.error(f"Error fetching tokens: {e}")
        return []


def get_random_token():
    """
    Get a random token from the Pump.fun API.
    Returns token data or None if no tokens are available.
    """
    tokens = get_recent_tokens()
    if tokens:
        # Pick a random token from the list
        token = random.choice(tokens)
        return {
            'name': token.get('name', 'Unknown Token'),
            'symbol': token.get('symbol', 'UNKNOWN'),
            'mint': token.get('address', '')
        }
    return None


def save_data():
    """Save yield data to file."""
    with file_lock:
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(yield_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")


def load_data():
    """Load yield data from file."""
    global yield_data
    with file_lock:
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    yield_data = json.load(f)
            else:
                yield_data = {}
                save_data()
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            yield_data = {}


def get_user_data(user_id):
    """Get user data from storage, initialize if not exists."""
    str_user_id = str(user_id)
    if str_user_id not in yield_data:
        yield_data[str_user_id] = {
            "balance": 0.5,  # Starting balance of 0.5 SOL
            "trades": [],
            "page": 0
        }
        save_data()
    return yield_data[str_user_id]


def generate_trade(user_id):
    """
    Generate a simulated trade for a user.
    Returns the trade data.
    """
    token = get_random_token()
    if not token:
        # Fallback if API fails
        token = {
            'name': f"Token{random.randint(1000, 9999)}",
            'symbol': f"TKN{random.randint(10, 99)}",
            'mint': ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))
        }
    
    # Random entry between $2M and $4M
    entry_cap = random.uniform(2000000, 4000000)
    
    # Calculate yield to follow 7-day 2x ROI curve (approximately 10.4% daily)
    # Using a slightly randomized value for realism
    daily_yield = random.uniform(9.5, 11.5)
    
    # Calculate exit price
    exit_cap = entry_cap * (1 + (daily_yield / 100))
    
    # Create the trade record
    trade = {
        'name': token['name'],
        'symbol': token['symbol'],
        'mint': token['mint'],
        'entry': entry_cap,
        'exit': exit_cap,
        'yield': daily_yield,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Update user data with the new trade
    user_data = get_user_data(user_id)
    
    # Apply yield to balance using compounding formula
    user_data['balance'] *= (1 + (daily_yield / 100))
    
    # Add trade to history
    user_data['trades'].insert(0, trade)  # Add to beginning (latest first)
    
    # Save updated data
    save_data()
    
    return trade


def format_trade_message(trade):
    """Format a trade record into a Telegram message with HTML formatting."""
    return (
        f"🧬 BOT SNIPED ANOTHER ONE! 🧬\n"
        f"🧠 Token Protocol: <a href=\"https://pump.fun/{trade['mint']}\">{trade['name']} ({trade['symbol']})</a>\n"
        f"📉 Entry Floor: ${trade['entry']:,.2f}\n"
        f"📈 Exit Ceiling: ${trade['exit']:,.2f}\n"
        f"💎 Yield Potential: {trade['yield']:.2f}%\n"
        f"📅 Time: {datetime.fromisoformat(trade['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )


def format_balance_message(user_id):
    """Format a balance message for the user."""
    user_data = get_user_data(user_id)
    balance = user_data['balance']
    
    # Calculate stats
    total_trades = len(user_data['trades'])
    total_yield = sum(trade['yield'] for trade in user_data['trades']) if total_trades > 0 else 0
    avg_yield = total_yield / total_trades if total_trades > 0 else 0
    
    return (
        f"💰 <b>Your Current SOL Balance</b>\n\n"
        f"Balance: <b>{balance:.4f} SOL</b>\n"
        f"Total Trades: {total_trades}\n"
        f"Average Yield: {avg_yield:.2f}%\n\n"
        f"Use /simulate to run a new trade simulation!"
    )


def get_trade_history_message(user_id, page=0):
    """
    Get the trade history message for a user with pagination.
    Shows 3 trades per page.
    """
    user_data = get_user_data(user_id)
    trades = user_data['trades']
    
    if not trades:
        return "No trade history found. Use /simulate to create some trades!"
    
    # Calculate total pages
    items_per_page = 3
    total_pages = (len(trades) + items_per_page - 1) // items_per_page
    
    # Validate page number
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1
    
    # Get trades for the current page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(trades))
    page_trades = trades[start_idx:end_idx]
    
    # Format the message
    header = f"📊 <b>Trading History</b> - Page {page + 1}/{total_pages}\n\n"
    trade_messages = []
    
    for i, trade in enumerate(page_trades):
        trade_msg = (
            f"<b>Trade #{start_idx + i + 1}</b>\n"
            f"Token: <a href=\"https://pump.fun/{trade['mint']}\">{trade['name']} ({trade['symbol']})</a>\n"
            f"Entry: ${trade['entry']:,.2f}\n"
            f"Exit: ${trade['exit']:,.2f}\n"
            f"Yield: {trade['yield']:.2f}%\n"
            f"Date: {datetime.fromisoformat(trade['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        trade_messages.append(trade_msg)
    
    return header + "\n".join(trade_messages)


def create_pagination_keyboard(user_id, current_page):
    """Create pagination keyboard for trade history."""
    user_data = get_user_data(user_id)
    trades = user_data['trades']
    
    items_per_page = 3
    total_pages = (len(trades) + items_per_page - 1) // items_per_page
    
    buttons = []
    
    # Only add prev button if not on first page
    if current_page > 0:
        buttons.append({"text": "⬅️ Prev", "callback_data": f"history_prev_{current_page}"})
    
    # Add page indicator
    buttons.append({"text": f"Page {current_page + 1}/{total_pages}", "callback_data": "no_action"})
    
    # Only add next button if not on last page
    if current_page < total_pages - 1:
        buttons.append({"text": "Next ➡️", "callback_data": f"history_next_{current_page}"})
    
    return [[button] for button in buttons]


# Command handlers for the python-telegram-bot v20 compatibility
async def simulate_command(update, context):
    """Simulate a random trade and update yield + balance."""
    # Extract user information
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Generate trade and update user data
    trade = generate_trade(user_id)
    
    # Send the trade message
    await context.bot.send_message(
        chat_id=chat_id,
        text=format_trade_message(trade),
        parse_mode="HTML"
    )
    
    # Update the user's page in case they were viewing history
    user_data = get_user_data(user_id)
    user_data['page'] = 0
    save_data()


async def history_command(update, context):
    """Show paginated trading history."""
    # Extract user information
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Get user data and current page
    user_data = get_user_data(user_id)
    page = user_data.get('page', 0)
    
    # Get history message and create pagination keyboard
    message = get_trade_history_message(user_id, page)
    keyboard = create_pagination_keyboard(user_id, page)
    
    # Send the message with pagination buttons
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML",
        reply_markup={"inline_keyboard": keyboard} if user_data['trades'] else None
    )


async def balance_command(update, context):
    """Display current SOL balance."""
    # Extract user information
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Get balance message
    message = format_balance_message(user_id)
    
    # Send the message
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML"
    )


async def callback_handler(update, context):
    """Handle callback queries from pagination buttons."""
    # Extract callback data
    query = update.callback_query
    user_id = query.from_user.id
    
    # Get current user data
    user_data = get_user_data(user_id)
    
    # Parse the callback data
    data = query.data
    
    # Handle pagination actions
    if data.startswith("history_prev_"):
        current_page = int(data.split("_")[-1])
        user_data['page'] = current_page - 1
        save_data()
        
        # Update the message with new page
        message = get_trade_history_message(user_id, user_data['page'])
        keyboard = create_pagination_keyboard(user_id, user_data['page'])
        
        await query.edit_message_text(
            text=message,
            parse_mode="HTML",
            reply_markup={"inline_keyboard": keyboard}
        )
    elif data.startswith("history_next_"):
        current_page = int(data.split("_")[-1])
        user_data['page'] = current_page + 1
        save_data()
        
        # Update the message with new page
        message = get_trade_history_message(user_id, user_data['page'])
        keyboard = create_pagination_keyboard(user_id, user_data['page'])
        
        await query.edit_message_text(
            text=message,
            parse_mode="HTML",
            reply_markup={"inline_keyboard": keyboard}
        )
    elif data == "no_action":
        # Do nothing for the page indicator button
        await query.answer("Current page")
    else:
        # Unknown callback
        await query.answer("Unknown action")


def setup_yield_module(application):
    """
    Set up the yield module for the Telegram bot.
    This function should be called from the main bot file.
    """
    try:
        # Import telegram module here to avoid circular imports
        from telegram.ext import CommandHandler, CallbackQueryHandler
        
        # Load existing data
        load_data()
        
        # Add command handlers
        application.add_handler(
            CommandHandler("simulate", simulate_command)
        )
        application.add_handler(
            CommandHandler("history", history_command)
        )
        application.add_handler(
            CommandHandler("balance", balance_command)
        )
        
        # Add callback query handler for pagination
        application.add_handler(
            CallbackQueryHandler(
                callback_handler,
                pattern=r"^(history_prev_|history_next_|no_action)"
            )
        )
        
        logger.info("Yield module initialized successfully.")
    except ImportError as e:
        logger.error(f"Failed to initialize yield module: {e}")
        logger.error("Make sure python-telegram-bot v20+ is installed")


# Main function for standalone testing
if __name__ == "__main__":
    print("This module is intended to be imported and used with a Telegram bot.")
    print("To use this module, add the following to your main bot file:")
    print("\nfrom yield_module import setup_yield_module")
    print("setup_yield_module(application)\n")