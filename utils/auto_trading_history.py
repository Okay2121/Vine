"""
Auto Trading History Module for Solana Memecoin Trading Bot

This module automatically generates realistic trading history for users
with newly launched Solana memecoins. It creates trades with appropriate timing
and realistic profit margins, triggered by deposits or admin balance adjustments.

Each trade includes:
- Token name & symbol (newly launched memecoins)
- Entry & exit timestamps
- Profit amount
- Balance updates
- Links to pump.fun or birdeye.so for token verification
"""

import logging
import random
import time
import json
import os
import threading
import requests
import schedule
from datetime import datetime, timedelta
from app import app, db
from models import User, Transaction, Profit, TradingPosition
from threading import Lock

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
STORAGE_FILE = 'auto_trading_data.json'
TRADES_PER_DAY = random.randint(3, 5)  # 3-5 trades per day per requirements
MIN_TRADE_INTERVAL = 120  # minimum minutes between trades (2-4 hours, in minutes)
MAX_TRADE_INTERVAL = 240  # maximum minutes between trades (2-4 hours, in minutes)
MIN_PROFIT_PERCENT = 4.0  # minimum profit percentage (4-10% per trade)
MAX_PROFIT_PERCENT = 10.0  # maximum profit percentage (4-10% per trade)
STANDOUT_PROFIT_MIN = 12.0  # standout profit min (12-15%)
STANDOUT_PROFIT_MAX = 15.0  # standout profit max (12-15%)
STANDOUT_PROBABILITY = 0.15  # chance of a standout win (once or twice per week)
LOSS_PROBABILITY = 0.2  # 20% chance of a loss on a trade (mostly profitable)
MIN_LOSS_PERCENT = 0.5  # minimum loss percentage (-0.5% to -1.8%)
MAX_LOSS_PERCENT = 1.8  # maximum loss percentage (-0.5% to -1.8%)
DEFAULT_ENTRY_HOLDING_MINUTES = 10  # time between entry and exit in minutes
DAILY_ROI_TARGET = 14.3  # Target daily ROI percentage for 2x in 7 days (100%/7)

# API endpoints
PUMP_FUN_API = "https://client-api.pump.fun/tokens/recent"
BIRDEYE_API = "https://public-api.birdeye.so/public/tokenlist?sort_by=v24hUSD"

# API cache settings
API_CACHE_DURATION = 15 * 60  # Cache API responses for 15 minutes
API_MAX_RETRIES = 3  # Maximum number of retry attempts
API_RETRY_DELAY = 2  # Seconds between retries

# Global cache for API responses
api_cache = {
    "pump_fun": {"data": None, "timestamp": 0},
    "birdeye": {"data": None, "timestamp": 0}
}

# Backoff/retry logging
def log_retry_attempt(func_name, attempt, max_tries, wait_time, error=None):
    """Log information about retry attempts"""
    error_msg = f": {error}" if error else ""
    logger.warning(
        f"Retrying {func_name} in {wait_time}s (attempt {attempt}/{max_tries}){error_msg}"
    )

# Implemented manually since we might not have backoff library installed
def with_retry(max_tries=3, delay=2):
    """
    Decorator that retries a function with exponential backoff
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_tries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    wait = delay * (2 ** (attempts - 1))  # Exponential backoff
                    
                    if attempts < max_tries:
                        logger.warning(
                            f"Error in {func.__name__}: {e}. "
                            f"Retrying in {wait}s (attempt {attempts}/{max_tries})"
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            f"Failed after {max_tries} attempts: {e}"
                        )
                        raise
        return wrapper
    return decorator

# Lock for file operations
file_lock = Lock()

# Global storage for user trading state
auto_trading_data = {}

# Global tracking for active trading threads
active_trading_threads = {}
stop_trading_flags = {}

# API status tracking
api_health = {
    'pump_fun': {'status': 'unknown', 'last_check': 0, 'failures': 0},
    'birdeye': {'status': 'unknown', 'last_check': 0, 'failures': 0}
}

def load_data():
    """Load auto trading data from file"""
    global auto_trading_data
    with file_lock:
        try:
            if os.path.exists(STORAGE_FILE):
                with open(STORAGE_FILE, 'r') as f:
                    auto_trading_data = json.load(f)
            else:
                auto_trading_data = {}
                save_data()
        except Exception as e:
            logger.error(f"Error loading auto trading data: {e}")
            auto_trading_data = {}

def save_data():
    """Save auto trading data to file"""
    with file_lock:
        try:
            with open(STORAGE_FILE, 'w') as f:
                json.dump(auto_trading_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving auto trading data: {e}")

def get_user_data(user_id):
    """Get auto trading data for a user, initialize if it doesn't exist"""
    str_user_id = str(user_id)
    if str_user_id not in auto_trading_data:
        auto_trading_data[str_user_id] = {
            "is_trading_active": False,
            "last_trade_time": None,
            "trades_today": 0,
            "last_daily_reset": datetime.utcnow().strftime("%Y-%m-%d"),
            "daily_profit": 0.0,
            "daily_profit_percentage": 0.0,  # Track ROI as percentage of starting balance
            "daily_starting_balance": None,  # Starting balance for ROI calculation
            "profit_streak": 0,
            "total_trades": 0,
            "positive_trades": 0,
            "next_trade_time": None,
            "weekly_roi_progress": 0.0,
            "roi_target_reached": False,     # Flag for when daily target is hit
            "last_trade_was_loss": False,    # Track if the last trade was a loss
            "consecutive_losses": 0          # Track number of consecutive losses
        }
        save_data()
    return auto_trading_data[str_user_id]

def fetch_api_data(url, source):
    """
    Centralized function for fetching data from APIs with retry logic
    
    Args:
        url (str): The API endpoint URL
        source (str): Source identifier for logging ("pump_fun" or "birdeye")
        
    Returns:
        dict or None: JSON response data or None if all retries failed
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }
    
    # Check if we have a valid cached response
    cache_entry = api_cache.get(source, {})
    cache_time = cache_entry.get("timestamp", 0)
    cache_data = cache_entry.get("data")
    
    # Use cache if it's still valid (not expired)
    if cache_data and (time.time() - cache_time) < API_CACHE_DURATION:
        logger.debug(f"Using cached {source} API data (age: {time.time() - cache_time:.1f}s)")
        return cache_data
    
    # If no valid cache, fetch from API with retries
    for attempt in range(1, API_MAX_RETRIES + 1):
        try:
            fetch_start_time = time.time()
            logger.debug(f"Fetching {source} API data (attempt {attempt}/{API_MAX_RETRIES})")
            response = requests.get(url, headers=headers, timeout=10)
            
            # Check for HTTP errors
            if response.status_code != 200:
                error_msg = f"API error: {response.status_code}"
                try:
                    # Try to extract error message from JSON response
                    error_body = response.json()
                    if "message" in error_body:
                        error_msg += f" - {error_body['message']}"
                except:
                    # If we can't parse JSON, use text content
                    error_msg += f" - {response.text[:100]}"
                
                logger.warning(f"{source} API request failed: {error_msg}")
                
                # For 429 (rate limit) or 5xx (server errors), retry after backoff
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < API_MAX_RETRIES:
                        wait_time = API_RETRY_DELAY * (2 ** (attempt - 1))
                        logger.warning(f"Retrying {source} API in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                
                # For other errors like 400, 401, 403, don't retry
                return None
            
            # Parse JSON response
            try:
                data = response.json()
                fetch_duration = time.time() - fetch_start_time
                
                # Validate the response format and content
                if source == "pump_fun":
                    tokens_list = data.get("data")
                    if not isinstance(tokens_list, list):
                        logger.warning(f"Invalid {source} API response format: 'data' field is not a list")
                        return None
                    
                    # Verify that we have at least some tokens
                    if len(tokens_list) == 0:
                        logger.warning(f"Empty token list received from {source} API")
                        return None
                    
                    # Log a sample token to verify data quality
                    if len(tokens_list) > 0:
                        sample_token = tokens_list[0]
                        # Validate required fields
                        if not all(k in sample_token for k in ['name', 'symbol', 'address']):
                            logger.warning(f"Missing required fields in {source} token data")
                            return None
                        
                        # Log sample data and fetch timestamp
                        sample_data = {
                            'name': sample_token.get('name'),
                            'symbol': sample_token.get('symbol'),
                            'address': sample_token.get('address')[:8] + '...',  # Truncate for logging
                            'price': sample_token.get('price'),
                            'marketCap': sample_token.get('marketCap'),
                            'volume': sample_token.get('volume')
                        }
                        fetch_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                        logger.info(f"Pump.fun data loaded successfully at {fetch_time} (took {fetch_duration:.2f}s)")
                        logger.info(f"Sample token: {sample_data}")
                
                elif source == "birdeye":
                    tokens_container = data.get("data", {})
                    tokens_list = tokens_container.get("tokens")
                    if not isinstance(tokens_list, list):
                        logger.warning(f"Invalid {source} API response format: 'data.tokens' field is not a list")
                        return None
                    
                    # Verify that we have at least some tokens
                    if len(tokens_list) == 0:
                        logger.warning(f"Empty token list received from {source} API")
                        return None
                    
                    # Log a sample token to verify data quality
                    if len(tokens_list) > 0:
                        sample_token = tokens_list[0]
                        # Validate required fields
                        if not all(k in sample_token for k in ['symbol', 'address']):
                            logger.warning(f"Missing required fields in {source} token data")
                            return None
                        
                        # Log sample data and fetch timestamp
                        sample_data = {
                            'name': sample_token.get('name', sample_token.get('symbol')),
                            'symbol': sample_token.get('symbol'),
                            'address': sample_token.get('address')[:8] + '...',  # Truncate for logging
                            'price': sample_token.get('price'),
                            'marketCap': sample_token.get('marketCap'),
                            'volume': sample_token.get('v24hUSD')
                        }
                        fetch_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                        logger.info(f"Birdeye data fetched successfully at {fetch_time} (took {fetch_duration:.2f}s)")
                        logger.info(f"Sample token: {sample_data}")
                
                # Additional data type validation for the current API source
                tokens_list = None
                if source == "pump_fun":
                    tokens_list = data.get("data", [])
                elif source == "birdeye":
                    tokens_list = data.get("data", {}).get("tokens", [])
                
                # Validate types if we have token data
                if tokens_list and len(tokens_list) > 0:
                    sample = tokens_list[0]
                    # Type checks
                    if sample.get('name') and not isinstance(sample.get('name'), str):
                        logger.warning(f"{source} API: Token name is not a string")
                    if sample.get('price') and not isinstance(sample.get('price'), (int, float)):
                        logger.warning(f"{source} API: Token price is not a number")
                
                # Update cache
                api_cache[source] = {
                    "data": data,
                    "timestamp": time.time()
                }
                
                return data
                
            except ValueError as e:
                logger.warning(f"Failed to parse {source} API response as JSON: {e}")
                if attempt < API_MAX_RETRIES:
                    wait_time = API_RETRY_DELAY * (2 ** (attempt - 1))
                    logger.warning(f"Retrying {source} API in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"{source} API request timed out")
            if attempt < API_MAX_RETRIES:
                wait_time = API_RETRY_DELAY * (2 ** (attempt - 1))
                logger.warning(f"Retrying {source} API in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"{source} API failed after {API_MAX_RETRIES} retries due to timeouts")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"{source} API connection error: {e}")
            if attempt < API_MAX_RETRIES:
                wait_time = API_RETRY_DELAY * (2 ** (attempt - 1))
                logger.warning(f"Retrying {source} API in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"{source} API failed after {API_MAX_RETRIES} retries due to connection errors")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error fetching {source} API data: {e}")
            if attempt < API_MAX_RETRIES:
                wait_time = API_RETRY_DELAY * (2 ** (attempt - 1))
                logger.warning(f"Retrying {source} API in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"{source} API failed after {API_MAX_RETRIES} retries")
                return None
    
    # If we've exhausted all retries
    return None


def get_recent_solana_memecoins(source="pump_fun"):
    """
    Fetch recently launched Solana memecoins from the API with caching and retries
    Returns a list of token data or falls back to previously cached data if the request fails
    """
    # Choose the appropriate API endpoint
    if source == "pump_fun":
        api_url = PUMP_FUN_API
    elif source == "birdeye":
        api_url = BIRDEYE_API
    else:
        logger.error(f"Unknown API source: {source}")
        return []
    
    # Fetch data from API (with caching and retries)
    data = fetch_api_data(api_url, source)
    
    # Process the response based on the source
    if data:
        try:
            recent_tokens = []
            
            if source == "pump_fun":
                tokens = data.get('data', [])
                
                # Filter for tokens with required fields
                for token in tokens:
                    if token.get('name') and token.get('address'):
                        recent_tokens.append({
                            'name': token.get('name'),
                            'symbol': token.get('symbol', 'UNKNOWN'),
                            'address': token.get('address'),
                            'price': token.get('price', 0.00001),
                            'marketCap': token.get('marketCap', 1000000),
                            'source': 'pump_fun'
                        })
                        
            elif source == "birdeye":
                tokens = data.get('data', {}).get('tokens', [])
                
                # Filter for recent tokens with low market cap (top 50)
                for token in tokens[:50]:
                    if token.get('symbol') and token.get('address'):
                        recent_tokens.append({
                            'name': token.get('name', token.get('symbol')),
                            'symbol': token.get('symbol'),
                            'address': token.get('address'),
                            'price': token.get('price', 0.00001),
                            'marketCap': token.get('marketCap', 1000000),
                            'source': 'birdeye'
                        })
            
            if recent_tokens:
                logger.info(f"Successfully fetched {len(recent_tokens)} tokens from {source}")
                return recent_tokens
            else:
                logger.warning(f"No valid tokens found in {source} API response")
                return []
                
        except Exception as e:
            logger.error(f"Error processing {source} API response: {e}")
            return []
    else:
        logger.warning(f"Failed to fetch data from {source} API")
        
        # Check if we have any cached data (even if expired)
        cache_entry = api_cache.get(source, {})
        cache_data = cache_entry.get("data")
        
        if cache_data:
            logger.info(f"Using expired cache data for {source} as fallback")
            # Process the cached data (reuse the same logic)
            try:
                recent_tokens = []
                
                if source == "pump_fun":
                    tokens = cache_data.get('data', [])
                    for token in tokens:
                        if token.get('name') and token.get('address'):
                            recent_tokens.append({
                                'name': token.get('name'),
                                'symbol': token.get('symbol', 'UNKNOWN'),
                                'address': token.get('address'),
                                'price': token.get('price', 0.00001),
                                'marketCap': token.get('marketCap', 1000000),
                                'source': 'pump_fun'
                            })
                            
                elif source == "birdeye":
                    tokens = cache_data.get('data', {}).get('tokens', [])
                    for token in tokens[:50]:
                        if token.get('symbol') and token.get('address'):
                            recent_tokens.append({
                                'name': token.get('name', token.get('symbol')),
                                'symbol': token.get('symbol'),
                                'address': token.get('address'),
                                'price': token.get('price', 0.00001),
                                'marketCap': token.get('marketCap', 1000000),
                                'source': 'birdeye'
                            })
                
                if recent_tokens:
                    logger.info(f"Using {len(recent_tokens)} cached tokens from {source}")
                    return recent_tokens
            except Exception as e:
                logger.error(f"Error processing cached {source} API data: {e}")
        
        # If we get here, we couldn't get data from API or cache
        return []

def get_random_memecoin():
    """
    Get a random newly launched memecoin from available sources
    with improved error handling and fallback mechanisms
    """
    # Try primary source first (pump.fun)
    logger.debug("Attempting to get memecoin from primary source (pump.fun)")
    tokens = get_recent_solana_memecoins("pump_fun")
    
    # If primary source fails, try secondary source (birdeye)
    if not tokens:
        logger.info("Primary source failed, trying secondary source (birdeye)")
        tokens = get_recent_solana_memecoins("birdeye")
    
    # If we have tokens from either source, choose a random one
    if tokens:
        logger.debug(f"Successfully obtained {len(tokens)} tokens for selection")
        # Pick a random token from the available ones
        token = random.choice(tokens)
        logger.info(f"Selected token: {token.get('name')} ({token.get('symbol')}) from {token.get('source')}")
        return token
    
    # If both APIs failed and no cached data is available
    logger.error("Failed to obtain token data from any source")
    return None

def generate_trade_for_user(user_id, user_balance):
    """
    Generate a realistic trade for a user based on their current balance
    Returns the trade data and updated balance, or None if no token data is available
    """
    # Get user trading data
    user_data = get_user_data(user_id)
    
    # Get a random new memecoin
    token = get_random_memecoin()
    
    # If we couldn't get any token data from any source, return None to indicate failure
    if token is None:
        logger.error(f"Cannot generate trade for user {user_id}: No token data available from any source")
        return None
    
    try:
        # Check if the last trade was a loss and prevent consecutive losses
        # Also enforce higher win rate (3-4 profitable trades out of 3-5)
        if user_data.get('last_trade_was_loss', False):
            # Force this trade to be profitable to avoid consecutive losses
            is_profitable = True
            logger.info(f"Enforcing profitable trade for user {user_id} to avoid consecutive losses")
            user_data['consecutive_losses'] = 0  # Reset consecutive loss counter
        else:
            # Determine if this trade will be profitable or not
            is_profitable = random.random() > LOSS_PROBABILITY
            # If this would be a loss, check if we already have too many losses today
            if not is_profitable:
                # Calculate today's ratio of profitable to total trades
                trades_today = user_data.get('trades_today', 0)
                if trades_today >= 3:  # Only apply this logic after we have some data
                    profitable_today = user_data.get('positive_trades', 0)
                    # If we have less than 3 profitable trades out of total trades, force profit
                    if profitable_today < 3 and trades_today - profitable_today >= 1:
                        is_profitable = True
                        logger.info(f"Enforcing profitable trade for user {user_id} to maintain high win rate")
        
        # Check if this is going to be a standout trade (12-15% gain)
        # Should happen once or twice a week (approximately 1-2 out of 21-35 trades)
        is_standout = is_profitable and random.random() < STANDOUT_PROBABILITY
        
        # Calculate profit/loss percentage
        if is_profitable:
            if is_standout:
                # Generate a standout trade with higher profit (12-15%)
                profit_percent = random.uniform(STANDOUT_PROFIT_MIN, STANDOUT_PROFIT_MAX)
                logger.info(f"Generated standout trade with {profit_percent:.2f}% profit for user {user_id}")
            else:
                # Regular profitable trade (4-10%)
                profit_percent = random.uniform(MIN_PROFIT_PERCENT, MAX_PROFIT_PERCENT)
        else:
            # Loss trade (-0.5% to -1.8%)
            profit_percent = -random.uniform(MIN_LOSS_PERCENT, MAX_LOSS_PERCENT)
            user_data['consecutive_losses'] = user_data.get('consecutive_losses', 0) + 1
        
        # Calculate profit amount based on a portion of user's balance
        # Use between 10-50% of balance for each trade
        trade_amount = user_balance * random.uniform(0.1, 0.5)
        profit_amount = trade_amount * (profit_percent / 100)
        
        # Calculate entry and exit timing
        current_time = datetime.utcnow()
        holding_time = random.randint(DEFAULT_ENTRY_HOLDING_MINUTES // 2, DEFAULT_ENTRY_HOLDING_MINUTES * 2)
        exit_time = current_time + timedelta(minutes=holding_time)
        
        # Safely access token data with error checking
        entry_price = token.get('price', 0.00001)
        exit_price = entry_price * (1 + (profit_percent / 100))
        
        # Format token link based on source with error checking
        token_address = token.get('address')
        token_source = token.get('source', 'birdeye')  # Default to birdeye if source not specified
        
        if not token_address:
            logger.error(f"Token data missing address: {token}")
            return None
            
        if token_source == 'pump_fun':
            token_link = f"https://pump.fun/{token_address}"
        else:
            token_link = f"https://birdeye.so/token/{token_address}?chain=solana"
        
        # Create the trade record with proper error checking
        # Safely access token data using get() to avoid KeyError
        trade = {
            'user_id': user_id,
            'token_name': token.get('name', 'Unknown'),
            'token_symbol': token.get('symbol', 'UNKNOWN'),
            'token_address': token_address,
            'token_link': token_link,
            'entry_time': current_time.isoformat(),
            'exit_time': exit_time.isoformat(),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'trade_amount': trade_amount,
            'profit_amount': profit_amount,
            'profit_percent': profit_percent,
            'is_profitable': is_profitable
        }
        
        # Update user balance
        new_balance = user_balance + profit_amount
        
        return trade, new_balance
        
    except Exception as e:
        # Log the error with detailed information
        logger.error(f"Error generating trade for user {user_id}: {e}")
        logger.error(f"Token data: {token}")
        return None

def record_trade_in_database(user_id, trade):
    """Record a trade in the database with appropriate transaction and profit records"""
    # Validate trade input
    if trade is None:
        logger.error(f"Cannot record trade for user {user_id}: trade data is None")
        return False
        
    # Ensure trade has all required fields
    required_fields = ['trade_amount', 'token_name', 'token_symbol', 'entry_time', 'exit_time',
                       'entry_price', 'exit_price', 'profit_amount', 'profit_percent']
    
    for field in required_fields:
        if field not in trade:
            logger.error(f"Cannot record trade for user {user_id}: missing required field '{field}'")
            return False
    
    with app.app_context():
        try:
            # Get the user
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found when recording trade")
                return False
            
            # Create a transaction record for buy
            buy_transaction = Transaction()
            buy_transaction.user_id = user_id
            buy_transaction.transaction_type = "buy"
            buy_transaction.amount = trade['trade_amount']
            buy_transaction.token_name = f"{trade['token_name']} ({trade['token_symbol']})"
            buy_transaction.timestamp = datetime.fromisoformat(trade['entry_time'])
            buy_transaction.status = "completed"
            buy_transaction.notes = f"Auto trade entry at {trade['entry_price']:.8f} USD"
            buy_transaction.tx_hash = None  # No actual blockchain transaction
            
            # Create a transaction record for sell
            sell_transaction = Transaction()
            sell_transaction.user_id = user_id
            sell_transaction.transaction_type = "sell"
            sell_transaction.amount = trade['trade_amount'] + trade['profit_amount']
            sell_transaction.token_name = f"{trade['token_name']} ({trade['token_symbol']})"
            sell_transaction.timestamp = datetime.fromisoformat(trade['exit_time'])
            sell_transaction.status = "completed"
            sell_transaction.notes = f"Auto trade exit at {trade['exit_price']:.8f} USD"
            sell_transaction.tx_hash = None  # No actual blockchain transaction
            
            # Record the profit/loss
            profit_record = Profit()
            profit_record.user_id = user_id
            profit_record.amount = trade['profit_amount']
            profit_record.percentage = trade['profit_percent']
            profit_record.date = datetime.fromisoformat(trade['exit_time']).date()
            
            # Add records to database
            db.session.add(buy_transaction)
            db.session.add(sell_transaction)
            db.session.add(profit_record)
            
            # Update user balance
            user.balance += trade['profit_amount']
            
            # Commit the changes
            db.session.commit()
            
            logger.info(f"Recorded trade for user {user_id}: {trade['profit_amount']:.4f} SOL ({trade['profit_percent']:.2f}%)")
            return True
            
        except Exception as e:
            logger.error(f"Error recording trade in database: {e}")
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()
            return False

def format_trade_message(trade, telegram_mode=False):
    """Format a trade record into a message for notifications"""
    entry_time = datetime.fromisoformat(trade['entry_time'])
    exit_time = datetime.fromisoformat(trade['exit_time'])
    
    # Calculate holding duration in minutes
    holding_duration = (exit_time - entry_time).total_seconds() / 60
    
    # Create emoji indicators based on performance
    if trade['is_profitable']:
        if trade['profit_percent'] > 10:
            profit_emoji = "🚀"  # Rocket for big gains
        else:
            profit_emoji = "🟢"  # Green circle for standard gains
    else:
        if trade['profit_percent'] < -5:
            profit_emoji = "📉"  # Chart down for significant losses
        else:
            profit_emoji = "🔴"  # Red circle for minor losses
    
    # Determine the token link based on context
    token_link = trade['token_link']
    
    # Format time in a cleaner way
    entry_time_str = entry_time.strftime('%H:%M UTC')
    exit_time_str = exit_time.strftime('%H:%M UTC')
    
    # Format message differently for Telegram vs other contexts
    if telegram_mode:
        # Advanced formatting for 2x ROI strategy
        result_str = f"{'+' if trade['profit_percent'] >= 0 else ''}{trade['profit_percent']:.2f}%"
        balance_str = f"{trade['updated_balance']:.4f} SOL"
        
        message = (
            f"{profit_emoji} *Auto Trade Completed!*\n\n"
            f"*Token:* ${trade['token_symbol']}\n"
            f"*Entry Price:* {trade['entry_price']:.8f} SOL\n"
            f"*Exit Price:* {trade['exit_price']:.8f} SOL\n"
            f"*Time:* {exit_time_str}\n"
            f"*Result:* {result_str}\n"
            f"*Updated Balance:* {balance_str}\n"
        )
        
        # Add a motivational note based on result
        if trade['is_profitable']:
            if trade['profit_percent'] > 10:
                message += "\n🔥 *Exceptional performance!* The bot caught a significant price movement."
            elif trade['profit_percent'] > 5:
                message += "\n✨ *Strong trade!* Your bot is performing well."
        else:
            message += "\n📊 *Market volatility is normal.* The bot balances gains and losses for optimal results."
    else:
        # HTML format for web interfaces
        result_str = f"{'+' if trade['profit_amount'] >= 0 else ''}{trade['profit_amount']:.4f} SOL ({'+' if trade['profit_percent'] >= 0 else ''}{trade['profit_percent']:.2f}%)"
        
        message = (
            f"{profit_emoji} <b>Auto Trade Completed!</b>\n\n"
            f"<b>Token:</b> <a href='{token_link}'>{trade['token_name']} ({trade['token_symbol']})</a>\n"
            f"<b>Entry:</b> {entry_time_str} → <b>Exit:</b> {exit_time_str} ({holding_duration:.1f} min)\n"
            f"<b>Amount:</b> {trade['trade_amount']:.4f} SOL\n"
            f"<b>Result:</b> {result_str}\n"
        )
        
        # Add a motivational note based on result
        if trade['is_profitable']:
            if trade['profit_percent'] > 10:
                message += "\n🔥 <b>Exceptional performance!</b> The bot caught a significant price movement."
            elif trade['profit_percent'] > 5:
                message += "\n✨ <b>Strong trade!</b> Your bot is performing well."
        else:
            message += "\n📊 <b>Market volatility is normal.</b> The bot balances gains and losses for optimal results."
    
    return message

def send_telegram_notification(chat_id, message, message_type="trading_update", parse_mode="Markdown", reply_markup=None):
    """
    Send a notification to the user via Telegram with automatic message cleanup
    
    Args:
        chat_id (int): Telegram chat ID
        message (str): Message text to send
        message_type (str): Type of message for cleanup tracking 
        parse_mode (str): Telegram parse mode (Markdown or HTML)
        reply_markup: Optional keyboard markup
        
    Returns:
        bool: True if message was sent successfully
    """
    try:
        with app.app_context():
            # Try to use message cleanup module if available
            try:
                from utils.message_cleanup import send_message_with_cleanup, delete_old_message
                
                # Check if we have a bot_v20_runner reference
                try:
                    from bot_v20_runner import bot
                    if bot:
                        # Use the cleanup-enabled sender
                        return send_message_with_cleanup(
                            bot, 
                            chat_id, 
                            message, 
                            message_type, 
                            parse_mode=parse_mode, 
                            reply_markup=reply_markup
                        ) is not None
                except (ImportError, AttributeError):
                    # If we can't import the bot, try to delete any old messages directly
                    # Skip async function call since we're in a synchronous context
                    logger.warning("Could not import bot from bot_v20_runner")
            except (ImportError, AttributeError):
                # Message cleanup module not available, continue with regular sending
                logger.debug("Message cleanup module not available, using standard notification")
                pass
            
            # Fallback using direct API call
            import os
            import requests
            
            token = os.environ.get('TELEGRAM_BOT_TOKEN')
            if not token:
                logger.error("No Telegram bot token available for notification")
                return False
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            # Add reply_markup if provided
            if reply_markup:
                if isinstance(reply_markup, dict):
                    payload['reply_markup'] = reply_markup
                else:
                    # Try to convert the object to JSON
                    import json
                    try:
                        payload['reply_markup'] = json.dumps(reply_markup.to_dict())
                    except:
                        logger.warning("Could not convert reply_markup to JSON")
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

def get_motivational_message(streak):
    """Generate a motivational message based on performance streak"""
    if streak <= 0:
        return random.choice([
            "Time to bounce back! The 2x ROI path is still ahead of us.",
            "Minor setback, major comeback! Our high-performance strategy is adaptable.",
            "Even top performers have adjustment days. Tomorrow we accelerate again!",
            "Optimizing our strategy. The path to 2x ROI remains clear!",
            "Quick recovery mode activated! Every new trade brings us back on track."
        ])
    elif streak < 3:
        return random.choice([
            "We're building momentum! Our 2x ROI journey is progressing nicely.",
            "Consistent gains! You're witnessing the power of compounding returns.",
            "Smart trades paying off! This high-performance strategy is delivering.",
            "Upward trajectory established! Each profitable day accelerates your growth.",
            "Excellent progress! We're hitting our daily targets with precision."
        ])
    elif streak < 7:
        return random.choice([
            "Impressive 5-day win streak! Your strategy is outperforming the market!",
            "Remarkable consistency! Few traders achieve this level of performance.",
            "Outstanding streak! Your portfolio growth is ahead of schedule!",
            "Superior trading performance! You're on the fastest path to 2x returns!",
            "Exceptional streak continues! Your investment is growing at prime rate!"
        ])
    else:
        return random.choice([
            "Phenomenal 7+ day win streak! You've unlocked elite performance tier!",
            "Extraordinary streak! Your returns are outpacing 98% of traders!",
            "Masterful performance continues! Your 2x ROI is accelerating rapidly!",
            "Legendary streak achieved! Your investment strategy is unmatched!",
            "Peak performance activated! You're experiencing the ultimate growth pattern!"
        ])

def generate_progress_bar(percentage, length=10):
    """Generate a progress bar string based on percentage"""
    filled = int(percentage / 100 * length)
    empty = length - filled
    return "▓" * filled + "░" * empty

def send_daily_summary(user_id):
    """Send a daily summary of trading performance to the user"""
    with app.app_context():
        try:
            # Get user information
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found when sending daily summary")
                return False
            
            # Get user trading data
            user_data = get_user_data(user_id)
            
            # Calculate total profit for the day
            daily_profit = user_data.get('daily_profit', 0.0)
            trades_today = user_data.get('trades_today', 0)
            
            # Calculate total positive vs negative trades
            total_trades = user_data.get('total_trades', 0)
            positive_trades = user_data.get('positive_trades', 0)
            negative_trades = total_trades - positive_trades
            
            # Calculate win rate
            win_rate = (positive_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate daily ROI percentage using starting balance
            starting_balance = user_data.get('daily_starting_balance')
            if not starting_balance or starting_balance <= 0:
                starting_balance = user.balance - daily_profit  # Estimate starting balance if not tracked
            
            daily_roi_percent = (daily_profit / starting_balance * 100) if starting_balance > 0 else 0
            
            # Update streak based on daily profit
            profit_streak = user_data.get('profit_streak', 0)
            if daily_profit > 0:
                profit_streak += 1
            else:
                profit_streak = 0
            
            user_data['profit_streak'] = profit_streak
            
            # Update weekly ROI progress - aim for 2x in 7 days
            weekly_target = 100.0  # 100% increase = 2x
            daily_target = weekly_target / 7  # ~14.3% per day
            
            # Update weekly ROI progress
            current_progress = user_data.get('weekly_roi_progress', 0.0)
            new_progress = min(100.0, current_progress + (daily_roi_percent / daily_target) * (100.0 / 7))
            user_data['weekly_roi_progress'] = new_progress
            
            # Check for milestone achievements
            milestone_message = ""
            if 25 <= new_progress < 50 and current_progress < 25:
                milestone_message = "🎯 *25% MILESTONE REACHED!* You're a quarter way to doubling your investment! Keep going! 💪\n\n"
            elif 50 <= new_progress < 75 and current_progress < 50:
                milestone_message = "🎯 *50% MILESTONE REACHED!* Halfway to doubling your investment! Incredible progress! 🔥\n\n"
            elif 75 <= new_progress < 100 and current_progress < 75:
                milestone_message = "🎯 *75% MILESTONE REACHED!* Just a bit more to reach your 2x goal! Almost there! 🚀\n\n"
            elif new_progress >= 100 and current_progress < 100:
                milestone_message = "🏆 *100% MILESTONE REACHED!* CONGRATULATIONS! You've doubled your investment! Outstanding performance! 🎉🎊\n\n"
            
            # Generate motivational message based on win streak
            motivation = get_motivational_message(profit_streak)
            
            # Generate progress bar
            progress_bar = generate_progress_bar(new_progress)
            
            # Determine performance emoji
            if daily_profit > 0:
                if daily_roi_percent >= DAILY_ROI_TARGET:
                    performance_emoji = "🚀"  # Target reached
                elif daily_roi_percent >= 10.0:
                    performance_emoji = "💰"  # Exceptional profit (10%+)
                else:
                    performance_emoji = "📈"  # Positive
            else:
                performance_emoji = "📉"  # Negative
            
            # Format the date in a more readable way
            yesterday = datetime.utcnow() - timedelta(days=1)
            date_str = yesterday.strftime("%B %d, %Y")
            
            # Format message with more detail
            message = (
                f"{performance_emoji} *Daily Trading Summary* {performance_emoji}\n\n"
                f"*Date:* {date_str}\n"
                f"*Trades Executed:* {trades_today}\n"
                f"*Daily Profit:* {'+' if daily_profit >= 0 else ''}{daily_profit:.4f} SOL\n"
                f"*ROI:* {'+' if daily_roi_percent >= 0 else ''}{daily_roi_percent:.2f}%\n"
                f"*Current Balance:* {user.balance:.4f} SOL\n\n"
            )
            
            # Add performance statistics section
            message += (
                "*Performance Stats:*\n"
                f"• Win Rate: {win_rate:.1f}%\n"
                f"• Profitable Trades: {positive_trades}\n"
                f"• Loss Trades: {negative_trades}\n"
                f"• Profit Streak: {profit_streak} day{'s' if profit_streak != 1 else ''}\n\n"
            )
            
            # Add weekly progress with 2x goal emphasis
            message += (
                "*Weekly 2x ROI Progress:*\n"
                f"{progress_bar} {new_progress:.1f}%\n\n"
            )
            
            # Add milestone message if milestone reached
            if milestone_message:
                message += milestone_message
            
            # Add personalized motivation based on streak
            message += f"*{motivation}*\n\n"
            
            # Add daily performance indicator
            if daily_roi_percent >= 10:
                message += "🔥 *Exceptional day!* Your bot achieved outstanding returns today!\n\n"
            elif daily_roi_percent >= DAILY_ROI_TARGET:
                message += "✅ *Target reached!* Your bot hit the daily ROI target!\n\n"
            
            # Add call to action
            message += "🔄 *Trading has reset for the new day!*"
            if new_progress >= 100:
                message += "\n🎯 *Weekly 2x target reached! Congratulations!*"
            elif user.balance < 0.05:  # Low balance warning
                message += "\n⚠️ *Your balance is low.* Consider depositing more to maximize profits."
            
            # Send notification with appropriate cleanup
            if send_telegram_notification(user.telegram_id, message, message_type="daily_summary"):
                logger.info(f"Sent daily summary to user {user_id}")
                
                # Reset daily profit for the next day
                user_data['daily_profit'] = 0.0
                user_data['trades_today'] = 0
                user_data['last_daily_reset'] = datetime.utcnow().strftime("%Y-%m-%d")
                save_data()
                return True
            else:
                logger.error(f"Failed to send daily summary to user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def run_auto_trading_for_user(user_id):
    """
    Run automated trading for a specific user
    This function is meant to be run in a separate thread
    """
    logger.info(f"Starting auto trading thread for user {user_id}")
    
    # Get user trading data
    user_data = get_user_data(user_id)
    user_data['is_trading_active'] = True
    save_data()
    
    # Initialize
    global stop_trading_flags
    stop_trading_flags[user_id] = False
    
    # Calculate trades per day (randomized slightly per user)
    trades_per_day = random.randint(4, 8)  # More trades for higher activity
    
    # Calculate average time between trades
    seconds_per_day = 24 * 60 * 60
    avg_seconds_between_trades = seconds_per_day / trades_per_day
    
    while not stop_trading_flags.get(user_id, True):
        try:
            # Get user from database
            with app.app_context():
                user = User.query.get(user_id)
                if not user:
                    logger.error(f"User {user_id} not found during auto trading")
                    return
            
            # Check if we need to reset daily stats
            today = datetime.utcnow().strftime("%Y-%m-%d")
            if user_data.get('last_daily_reset') != today:
                # It's a new day - send summary from yesterday if there were trades
                if user_data.get('trades_today', 0) > 0:
                    send_daily_summary(user_id)
                
                # Reset for the new day
                user_data['last_daily_reset'] = today
                user_data['trades_today'] = 0
                user_data['daily_profit'] = 0.0
                user_data['daily_profit_percentage'] = 0.0
                user_data['daily_starting_balance'] = user.balance  # Store starting balance for ROI calculation
                user_data['roi_target_reached'] = False  # Reset ROI target flag
                save_data()
                
                logger.info(f"Daily stats reset for user {user_id}. New day starting balance: {user.balance:.6f} SOL")
            
            # Initialize daily starting balance if not set
            if user_data.get('daily_starting_balance') is None:
                user_data['daily_starting_balance'] = user.balance
                save_data()
            
            # Get current time
            current_time = datetime.utcnow()
            
            # Check if we've already scheduled the next trade
            next_trade_time_str = user_data.get('next_trade_time')
            if next_trade_time_str:
                next_trade_time = datetime.fromisoformat(next_trade_time_str)
            else:
                # Schedule first trade with a short delay
                delay_minutes = random.randint(5, 10)
                next_trade_time = current_time + timedelta(minutes=delay_minutes)
                user_data['next_trade_time'] = next_trade_time.isoformat()
                save_data()
                
                # Log the scheduled trade
                logger.info(f"First trade for user {user_id} scheduled at {next_trade_time}")
            
            # Check if it's time for the next trade
            if current_time >= next_trade_time:
                # Check if we've already hit the daily ROI target
                daily_roi_reached = False
                
                # Calculate current daily ROI percentage
                starting_balance = user_data.get('daily_starting_balance', user.balance)
                if starting_balance > 0:
                    current_roi_percentage = (user_data.get('daily_profit', 0.0) / starting_balance) * 100
                    user_data['daily_profit_percentage'] = current_roi_percentage
                    
                    # Check if daily ROI target is reached
                    if current_roi_percentage >= DAILY_ROI_TARGET:
                        daily_roi_reached = True
                        user_data['roi_target_reached'] = True
                        save_data()
                        
                        # Log ROI target reached
                        logger.info(f"Daily ROI target of {DAILY_ROI_TARGET:.2f}% reached for user {user_id}: {current_roi_percentage:.2f}%")
                        
                        # Send notification to user about reaching daily target
                        roi_message = (
                            f"🎯 *Daily ROI Target Reached!*\n\n"
                            f"Congratulations! Your bot has reached the daily ROI target of {DAILY_ROI_TARGET:.2f}%.\n\n"
                            f"Current ROI: {current_roi_percentage:.2f}%\n"
                            f"Total Profit Today: {user_data.get('daily_profit', 0.0):.4f} SOL\n\n"
                            f"Trading will resume tomorrow to protect your profits!"
                        )
                        send_telegram_notification(user.telegram_id, roi_message)
                
                # Check if we should stop trading for today (daily limit or ROI target)
                if daily_roi_reached or user_data.get('roi_target_reached', False) or user_data.get('trades_today', 0) >= trades_per_day:
                    # Wait until tomorrow
                    tomorrow = (datetime.utcnow() + timedelta(days=1)).replace(
                        hour=random.randint(8, 11),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                    user_data['next_trade_time'] = tomorrow.isoformat()
                    save_data()
                    
                    if not daily_roi_reached and not user_data.get('roi_target_reached', False) and user_data.get('trades_today', 0) >= trades_per_day:
                        logger.info(f"Daily trade limit reached for user {user_id}. Next trade scheduled for tomorrow.")
                    
                    # Sleep for a while before checking again
                    time.sleep(60)
                    continue
                
                # Time to execute a trade!
                with app.app_context():
                    # Get the user (refresh data)
                    user = User.query.get(user_id)
                    if not user:
                        logger.error(f"User {user_id} not found during auto trading")
                        return
                    
                    # Generate and record the trade
                    trade_result = generate_trade_for_user(user_id, user.balance)
                    
                    # If trade generation failed, retry later
                    if trade_result is None:
                        logger.warning(f"Failed to generate trade for user {user_id}. API sources unavailable. Will retry later.")
                        # Schedule retry in 30-60 minutes
                        retry_delay = random.randint(30, 60)
                        next_trade_time = datetime.utcnow() + timedelta(minutes=retry_delay)
                        user_data['next_trade_time'] = next_trade_time.isoformat()
                        save_data()
                        continue
                    
                    # Unpack the trade data and new balance
                    trade, new_balance = trade_result
                    success = record_trade_in_database(user_id, trade)
                    
                    if success:
                        # Update user data
                        user_data['trades_today'] = user_data.get('trades_today', 0) + 1
                        user_data['total_trades'] = user_data.get('total_trades', 0) + 1
                        user_data['last_trade_time'] = datetime.utcnow().isoformat()
                        
                        # Update daily profit tracking
                        user_data['daily_profit'] = user_data.get('daily_profit', 0.0) + trade['profit_amount']
                        
                        # Recalculate ROI percentage
                        starting_balance = user_data.get('daily_starting_balance', user.balance)
                        if starting_balance > 0:
                            current_roi_percentage = (user_data.get('daily_profit', 0.0) / starting_balance) * 100
                            user_data['daily_profit_percentage'] = current_roi_percentage
                            
                            # Check if we just hit ROI target with this trade
                            if current_roi_percentage >= DAILY_ROI_TARGET and not user_data.get('roi_target_reached', False):
                                user_data['roi_target_reached'] = True
                                
                                # Send notification about reaching ROI target
                                roi_message = (
                                    f"🎯 *Daily ROI Target Reached!*\n\n"
                                    f"Congratulations! Your bot has reached the daily ROI target of {DAILY_ROI_TARGET:.2f}%.\n\n"
                                    f"Current ROI: {current_roi_percentage:.2f}%\n"
                                    f"Total Profit Today: {user_data.get('daily_profit', 0.0):.4f} SOL\n\n"
                                    f"Trading will resume tomorrow to protect your profits!"
                                )
                                send_telegram_notification(user.telegram_id, roi_message)
                        
                        # Track positive trades and update loss tracking
                        if trade['profit_amount'] > 0:
                            user_data['positive_trades'] = user_data.get('positive_trades', 0) + 1
                            user_data['last_trade_was_loss'] = False
                        else:
                            user_data['last_trade_was_loss'] = True
                        
                        # Schedule next trade (if ROI target not reached)
                        next_interval_minutes = random.randint(MIN_TRADE_INTERVAL, MAX_TRADE_INTERVAL)
                        next_trade_time = datetime.utcnow() + timedelta(minutes=next_interval_minutes)
                        
                        # If ROI target reached, schedule for tomorrow instead
                        if user_data.get('roi_target_reached', False):
                            tomorrow = (datetime.utcnow() + timedelta(days=1)).replace(
                                hour=random.randint(8, 11),
                                minute=random.randint(0, 59),
                                second=random.randint(0, 59)
                            )
                            next_trade_time = tomorrow
                            logger.info(f"ROI target reached, scheduling next trade for tomorrow: {next_trade_time}")
                        
                        user_data['next_trade_time'] = next_trade_time.isoformat()
                        save_data()
                        
                        # Notify the user
                        trade_message = format_trade_message(trade, telegram_mode=True)
                        send_telegram_notification(user.telegram_id, trade_message)
                        
                        logger.info(f"Auto trade completed for user {user_id}, next trade in {next_interval_minutes} minutes")
                    else:
                        logger.error(f"Failed to record trade for user {user_id}")
            
            # Sleep for a bit before checking again
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in auto trading thread for user {user_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Sleep before retrying
            time.sleep(60)
    
    # Update trading status when thread ends
    user_data = get_user_data(user_id)
    user_data['is_trading_active'] = False
    save_data()
    
    logger.info(f"Auto trading thread for user {user_id} stopped")

def start_auto_trading_for_user(user_id):
    """Start automated trading for a user"""
    global active_trading_threads, stop_trading_flags
    
    # Check if trading is already active
    user_data = get_user_data(user_id)
    if user_data.get('is_trading_active', False):
        logger.info(f"Auto trading already active for user {user_id}")
        return False
    
    # Stop any existing thread
    stop_trading_flags[user_id] = True
    if user_id in active_trading_threads and active_trading_threads[user_id].is_alive():
        logger.info(f"Waiting for existing trading thread to stop for user {user_id}")
        active_trading_threads[user_id].join(timeout=3.0)
    
    # Create a new thread for this user
    stop_trading_flags[user_id] = False
    thread = threading.Thread(
        target=run_auto_trading_for_user,
        args=(user_id,),
        daemon=True
    )
    active_trading_threads[user_id] = thread
    thread.start()
    
    logger.info(f"Started auto trading for user {user_id}")
    return True

def stop_auto_trading_for_user(user_id):
    """Stop automated trading for a user"""
    global active_trading_threads, stop_trading_flags
    
    # Signal the thread to stop
    stop_trading_flags[user_id] = True
    
    # Wait for the thread to finish
    if user_id in active_trading_threads and active_trading_threads[user_id].is_alive():
        active_trading_threads[user_id].join(timeout=3.0)
    
    # Update user data
    user_data = get_user_data(user_id)
    user_data['is_trading_active'] = False
    save_data()
    
    logger.info(f"Stopped auto trading for user {user_id}")
    return True

def is_auto_trading_active_for_user(user_id):
    """Check if auto trading is active for a user"""
    user_data = get_user_data(user_id)
    return user_data.get('is_trading_active', False)

def handle_user_deposit(user_id, amount):
    """
    Handler for when a user makes a deposit
    This should be called by the deposit processing functions
    """
    logger.info(f"Handling deposit of {amount} SOL for user {user_id}")
    
    # Check if auto trading is already active
    if is_auto_trading_active_for_user(user_id):
        logger.info(f"Auto trading already active for user {user_id}")
        return
    
    # Start auto trading for this user
    start_auto_trading_for_user(user_id)

def handle_admin_balance_adjustment(user_id, amount):
    """
    Handler for when an admin adjusts a user's balance
    This should be called by the admin balance adjustment functions
    """
    if amount <= 0:
        # Only start trading on balance increases
        return
    
    logger.info(f"Handling admin balance adjustment of +{amount} SOL for user {user_id}")
    
    # Update ROI cycle to reflect the new balance
    try:
        from utils.roi_system import admin_update_cycle_after_balance_adjustment
        admin_update_cycle_after_balance_adjustment(user_id, amount)
        logger.info(f"Updated ROI cycle for user {user_id} after admin balance adjustment")
    except Exception as roi_error:
        logger.error(f"Failed to update ROI cycle for user {user_id}: {roi_error}")
    
    # Check if auto trading is already active
    if is_auto_trading_active_for_user(user_id):
        logger.info(f"Auto trading already active for user {user_id}")
        return
    
    # Start auto trading for this user
    start_auto_trading_for_user(user_id)

def check_api_health():
    """
    Check the health of all API endpoints and update the global health status
    This function should be called periodically to ensure we have up-to-date API status
    """
    global api_health
    
    current_time = time.time()
    check_interval = 15 * 60  # Check every 15 minutes
    
    # Check each API source
    for source in ['pump_fun', 'birdeye']:
        # Only check if we haven't checked recently
        if current_time - api_health[source]['last_check'] > check_interval:
            logger.debug(f"Checking health of {source} API...")
            
            # Set appropriate API URL
            if source == 'pump_fun':
                url = PUMP_FUN_API
            else:
                url = BIRDEYE_API
                
            # Try to fetch a small amount of data to test connection
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                
                # Update API status based on response
                if response.status_code == 200:
                    # Check response format validity
                    data = response.json()
                    if source == 'pump_fun' and isinstance(data.get('data'), list):
                        api_health[source]['status'] = 'healthy'
                        api_health[source]['failures'] = 0
                        logger.info(f"{source} API is healthy")
                    elif source == 'birdeye' and isinstance(data.get('data', {}).get('tokens'), list):
                        api_health[source]['status'] = 'healthy'
                        api_health[source]['failures'] = 0
                        logger.info(f"{source} API is healthy")
                    else:
                        api_health[source]['status'] = 'degraded'
                        api_health[source]['failures'] += 1
                        logger.warning(f"{source} API returned unexpected data format")
                else:
                    api_health[source]['status'] = 'degraded'
                    api_health[source]['failures'] += 1
                    logger.warning(f"{source} API returned status code {response.status_code}")
            except Exception as e:
                api_health[source]['status'] = 'down'
                api_health[source]['failures'] += 1
                logger.error(f"Error checking {source} API health: {e}")
            
            # Mark the check time
            api_health[source]['last_check'] = current_time
            
            # If we've seen multiple consecutive failures, log a critical error
            if api_health[source]['failures'] >= 3:
                logger.critical(f"{source} API appears to be down after {api_health[source]['failures']} consecutive failures")

def verify_api_data_quality():
    """
    Verify the quality of API data from both sources and log detailed information
    about the received data for monitoring and debugging
    
    This function forces a fresh fetch from both APIs (ignoring cache) and performs
    in-depth validation of the received data structure and content
    """
    logger.info("=====================================================")
    logger.info("STARTING API DATA QUALITY VERIFICATION")
    logger.info("=====================================================")
    
    verification_results = {}
    
    # Test each API source separately
    for source in ['pump_fun', 'birdeye']:
        if source == 'pump_fun':
            url = PUMP_FUN_API
        else:
            url = BIRDEYE_API
        
        logger.info(f"Verifying {source.upper()} API data quality...")
        
        # Force a fresh fetch by bypassing cache
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
        }
        
        try:
            # Fetch with timeout
            fetch_time_start = time.time()
            response = requests.get(url, headers=headers, timeout=15)
            fetch_time = time.time() - fetch_time_start
            
            verification_results[source] = {
                'fetch_success': False,
                'status_code': response.status_code,
                'fetch_time': f"{fetch_time:.2f}s",
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'data_structure': None,
                'sample_tokens': [],
                'issues': []
            }
            
            # Check status code
            if response.status_code != 200:
                verification_results[source]['issues'].append(
                    f"ERROR: API returned status code {response.status_code}"
                )
                continue
                
            # Parse and validate the JSON response
            try:
                data = response.json()
                verification_results[source]['fetch_success'] = True
                
                # Validate structure based on source
                if source == 'pump_fun':
                    # Check data structure
                    if not isinstance(data, dict):
                        verification_results[source]['issues'].append("ERROR: Response is not a dictionary")
                        continue
                        
                    if 'data' not in data:
                        verification_results[source]['issues'].append("ERROR: Missing 'data' key in response")
                        continue
                        
                    tokens = data['data']
                    if not isinstance(tokens, list):
                        verification_results[source]['issues'].append("ERROR: 'data' is not a list")
                        continue
                        
                    # Get token count
                    token_count = len(tokens)
                    verification_results[source]['token_count'] = token_count
                    
                    if token_count == 0:
                        verification_results[source]['issues'].append("WARNING: Empty token list")
                        continue
                        
                    # Check data structure
                    verification_results[source]['data_structure'] = {
                        'top_level_keys': list(data.keys()),
                        'token_keys': list(tokens[0].keys()) if token_count > 0 else []
                    }
                    
                    # Collect sample tokens (up to 3)
                    for i, token in enumerate(tokens[:3]):
                        sample = {
                            'name': token.get('name', 'N/A'),
                            'symbol': token.get('symbol', 'N/A'),
                            'address': token.get('address', 'N/A')[:10] + '...' if token.get('address') else 'N/A',
                            'price': token.get('price', 'N/A'),
                            'marketCap': token.get('marketCap', 'N/A'),
                            'volume': token.get('volume', 'N/A')
                        }
                        verification_results[source]['sample_tokens'].append(sample)
                        
                    # Type validation on first token if available
                    if token_count > 0:
                        sample_token = tokens[0]
                        type_issues = []
                        
                        if 'name' in sample_token and not isinstance(sample_token['name'], str):
                            type_issues.append(f"name (type: {type(sample_token['name']).__name__})")
                            
                        if 'symbol' in sample_token and not isinstance(sample_token['symbol'], str):
                            type_issues.append(f"symbol (type: {type(sample_token['symbol']).__name__})")
                            
                        if 'address' in sample_token and not isinstance(sample_token['address'], str):
                            type_issues.append(f"address (type: {type(sample_token['address']).__name__})")
                            
                        if 'price' in sample_token and not isinstance(sample_token['price'], (int, float, type(None))):
                            type_issues.append(f"price (type: {type(sample_token['price']).__name__})")
                            
                        if type_issues:
                            verification_results[source]['issues'].append(
                                f"WARNING: Type issues detected in fields: {', '.join(type_issues)}"
                            )
                            
                elif source == 'birdeye':
                    # Check data structure
                    if not isinstance(data, dict):
                        verification_results[source]['issues'].append("ERROR: Response is not a dictionary")
                        continue
                        
                    if 'data' not in data:
                        verification_results[source]['issues'].append("ERROR: Missing 'data' key in response")
                        continue
                        
                    tokens_container = data['data']
                    if not isinstance(tokens_container, dict):
                        verification_results[source]['issues'].append("ERROR: 'data' is not a dictionary")
                        continue
                        
                    if 'tokens' not in tokens_container:
                        verification_results[source]['issues'].append("ERROR: Missing 'tokens' key in data")
                        continue
                        
                    tokens = tokens_container['tokens']
                    if not isinstance(tokens, list):
                        verification_results[source]['issues'].append("ERROR: 'tokens' is not a list")
                        continue
                        
                    # Get token count
                    token_count = len(tokens)
                    verification_results[source]['token_count'] = token_count
                    
                    if token_count == 0:
                        verification_results[source]['issues'].append("WARNING: Empty token list")
                        continue
                        
                    # Check data structure
                    verification_results[source]['data_structure'] = {
                        'top_level_keys': list(data.keys()),
                        'data_keys': list(tokens_container.keys()),
                        'token_keys': list(tokens[0].keys()) if token_count > 0 else []
                    }
                    
                    # Collect sample tokens (up to 3)
                    for i, token in enumerate(tokens[:3]):
                        sample = {
                            'name': token.get('name', token.get('symbol', 'N/A')),
                            'symbol': token.get('symbol', 'N/A'),
                            'address': token.get('address', 'N/A')[:10] + '...' if token.get('address') else 'N/A',
                            'price': token.get('price', 'N/A'),
                            'marketCap': token.get('marketCap', 'N/A'),
                            'volume': token.get('v24hUSD', 'N/A')
                        }
                        verification_results[source]['sample_tokens'].append(sample)
                        
                    # Type validation on first token if available
                    if token_count > 0:
                        sample_token = tokens[0]
                        type_issues = []
                        
                        if 'symbol' in sample_token and not isinstance(sample_token['symbol'], str):
                            type_issues.append(f"symbol (type: {type(sample_token['symbol']).__name__})")
                            
                        if 'address' in sample_token and not isinstance(sample_token['address'], str):
                            type_issues.append(f"address (type: {type(sample_token['address']).__name__})")
                            
                        if 'price' in sample_token and not isinstance(sample_token['price'], (int, float, type(None))):
                            type_issues.append(f"price (type: {type(sample_token['price']).__name__})")
                            
                        if type_issues:
                            verification_results[source]['issues'].append(
                                f"WARNING: Type issues detected in fields: {', '.join(type_issues)}"
                            )
                
            except ValueError as e:
                verification_results[source]['issues'].append(f"ERROR: Failed to parse response as JSON: {e}")
                verification_results[source]['fetch_success'] = False
                
        except requests.exceptions.Timeout:
            verification_results[source]['issues'].append("ERROR: Request timed out")
            verification_results[source]['fetch_success'] = False
            
        except requests.exceptions.ConnectionError as e:
            verification_results[source]['issues'].append(f"ERROR: Connection error: {e}")
            verification_results[source]['fetch_success'] = False
            
        except Exception as e:
            verification_results[source]['issues'].append(f"ERROR: Unexpected error: {e}")
            verification_results[source]['fetch_success'] = False
    
    # Log results
    logger.info("=====================================================")
    logger.info("API DATA VERIFICATION RESULTS")
    logger.info("=====================================================")
    
    for source, results in verification_results.items():
        logger.info(f"SOURCE: {source.upper()} API ({results['timestamp']})")
        logger.info(f"Fetch success: {results['fetch_success']}")
        logger.info(f"Status code: {results.get('status_code', 'N/A')}")
        logger.info(f"Fetch time: {results.get('fetch_time', 'N/A')}")
        
        if 'token_count' in results:
            logger.info(f"Token count: {results['token_count']}")
            
        if results.get('data_structure'):
            structure = results['data_structure']
            logger.info(f"Data structure:")
            for key, value in structure.items():
                logger.info(f"  - {key}: {value}")
                
        # Log sample tokens
        if results.get('sample_tokens'):
            logger.info("Sample tokens:")
            for i, token in enumerate(results['sample_tokens']):
                logger.info(f"  Token {i+1}:")
                for key, value in token.items():
                    logger.info(f"    - {key}: {value}")
                    
        # Log issues
        if results.get('issues'):
            logger.info("Issues:")
            for issue in results['issues']:
                logger.info(f"  - {issue}")
                
        logger.info("-----------------------------------------------------")
    
    logger.info("API DATA VERIFICATION COMPLETE")
    logger.info("=====================================================")
    
    # Return overall success status
    overall_success = all(r.get('fetch_success', False) for r in verification_results.values())
    
    if overall_success:
        logger.info("VERIFICATION RESULT: All API sources are functioning correctly")
    else:
        logger.warning("VERIFICATION RESULT: Issues detected with one or more API sources")
        
    return overall_success

def initialize_module():
    """Initialize the auto trading history module"""
    # Load existing data
    load_data()
    
    # Check initial API health
    check_api_health()
    
    # Verify API data quality on startup
    try:
        logger.info("Verifying API data quality on startup...")
        api_data_verified = verify_api_data_quality()
        if api_data_verified:
            logger.info("API data verification successful - real-time data source confirmed working")
        else:
            logger.warning("API data verification encountered issues - check logs for details")
    except Exception as e:
        logger.error(f"Error during API data verification: {e}")
    
    # Schedule periodic API health checks
    schedule.every(15).minutes.do(check_api_health)
    # Schedule daily API data quality verification
    schedule.every().day.at("03:00").do(verify_api_data_quality)  # Run verification during low usage time
    
    logger.info("Auto trading history module initialized")

# Call initialize on module import
initialize_module()