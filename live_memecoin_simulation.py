#!/usr/bin/env python
"""
Script to simulate live trading using real-time memecoin data from pump.fun
"""
import os
import json
import random
import logging
import requests
import time
from datetime import datetime, timedelta
from sqlalchemy import func
from app import app, db
from models import User, Transaction, Profit

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User identifier to find
USERNAME = "@briensmart"  # The user to create trades for, None for all users with balance > 0

# Number of trades to generate
NUM_TRADES = 3

# Time frame to spread trades across (in hours)
TIME_FRAME = 24  # Last 24 hours

# Capital percentage to use per trade (as decimal)
MIN_CAPITAL_PERCENT = 0.05  # 5% minimum of balance
MAX_CAPITAL_PERCENT = 0.30  # 30% maximum of balance

# Profit range per trade (as decimal)
MIN_PROFIT_PERCENT = 0.02  # 2% minimum profit
MAX_PROFIT_PERCENT = 0.25  # 25% maximum profit

# Loss range per trade (as decimal)
MIN_LOSS_PERCENT = 0.01  # 1% minimum loss
MAX_LOSS_PERCENT = 0.15  # 15% maximum loss

# Chance of a profitable trade (0.0 to 1.0)
PROFIT_CHANCE = 0.75  # 75% chance of profit

# Memecoin data sources
PUMP_FUN_API = "https://api.pump.fun/memecoins/newest"
BIRDEYE_API = "https://public-api.birdeye.so/public/tokenlist"
BIRDEYE_HEADERS = {
    "x-api-key": "5d769ab4e8c54786af47f06b1ca8d9f3"
}

def find_user_by_username(username):
    """Find a user by their Telegram username"""
    with app.app_context():
        # Remove @ if present
        if username and username.startswith('@'):
            username = username[1:]
        
        # Find user - case insensitive
        user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        return user

def fetch_recent_memecoins():
    """Fetch recent memecoin data from pump.fun or fallback to birdeye"""
    try:
        # Attempt to fetch from pump.fun
        response = requests.get(PUMP_FUN_API, timeout=10)
        if response.status_code == 200:
            logger.info("Successfully fetched data from pump.fun")
            data = response.json()
            
            # Process and return the token data
            tokens = []
            for token in data[:50]:  # Get top 50 tokens
                try:
                    # Extract key data
                    token_data = {
                        'symbol': token.get('symbol', 'UNKNOWN'),
                        'name': token.get('name', 'Unknown Memecoin'),
                        'address': token.get('mint', ''),
                        'price': float(token.get('price', 0)) if token.get('price') else random.uniform(0.00001, 0.1),
                        'market_cap': float(token.get('marketCap', 0)) if token.get('marketCap') else random.uniform(10000, 1000000),
                        'volume_24h': float(token.get('volume24h', 0)) if token.get('volume24h') else random.uniform(1000, 100000),
                        'image': token.get('image', ''),
                        'source': 'pump.fun'
                    }
                    tokens.append(token_data)
                except Exception as e:
                    logger.error(f"Error processing token from pump.fun: {e}")
                    continue
            
            # If we got tokens, return them
            if tokens:
                return tokens
    
    except Exception as e:
        logger.warning(f"Error fetching from pump.fun: {e}")
    
    # Fallback to Birdeye API
    try:
        response = requests.get(BIRDEYE_API, headers=BIRDEYE_HEADERS, timeout=10)
        if response.status_code == 200:
            logger.info("Successfully fetched data from Birdeye (fallback)")
            data = response.json()
            
            # Process and return the token data
            tokens = []
            for token in data.get('data', [])[:50]:  # Get top 50 tokens
                try:
                    if 'memecoin' in token.get('tags', []).lower() or random.random() < 0.3:  # Only memecoin tokens or 30% chance
                        token_data = {
                            'symbol': token.get('symbol', 'UNKNOWN'),
                            'name': token.get('name', 'Unknown Token'),
                            'address': token.get('address', ''),
                            'price': float(token.get('price', 0)) if token.get('price') else random.uniform(0.00001, 0.1),
                            'market_cap': float(token.get('marketCap', 0)) if token.get('marketCap') else random.uniform(10000, 1000000),
                            'volume_24h': float(token.get('volume', 0)) if token.get('volume') else random.uniform(1000, 100000),
                            'image': token.get('logoURI', ''),
                            'source': 'birdeye'
                        }
                        tokens.append(token_data)
                except Exception as e:
                    logger.error(f"Error processing token from Birdeye: {e}")
                    continue
            
            # If we got tokens, return them
            if tokens:
                return tokens
    
    except Exception as e:
        logger.warning(f"Error fetching from Birdeye: {e}")
    
    # If all else fails, use fallback data
    logger.warning("Using fallback token data")
    return generate_fallback_tokens()

def generate_fallback_tokens():
    """Generate fallback token data if API calls fail"""
    current_time = datetime.now()
    date_str = current_time.strftime("%Y%m%d")
    
    # Use the date as a seed for consistent generation within the same day
    random.seed(date_str)
    
    tokens = []
    memecoin_prefixes = ["PEPE", "DOGE", "SHIB", "CAT", "FROG", "MOON", "WIF", "APE", "BASED", "CHAD", "WOJAK"]
    memecoin_suffixes = ["INU", "COIN", "MOON", "ELON", "ROCKET", "PUMP", "LAMBO", "RICH", "MEME", "BASED", "FOMO"]
    
    for i in range(50):
        # Generate random memecoin data
        prefix = random.choice(memecoin_prefixes)
        suffix = random.choice(memecoin_suffixes) if random.random() < 0.7 else ""
        symbol = f"{prefix}{suffix}"
        
        # Market cap between $10K and $10M
        market_cap = random.uniform(10000, 10000000)
        
        # Price between $0.000001 and $1
        price = random.uniform(0.000001, 1.0)
        
        # Volume between 1% and 50% of market cap
        volume = market_cap * random.uniform(0.01, 0.5)
        
        token = {
            'symbol': symbol,
            'name': f"{prefix} {suffix}".strip() if suffix else prefix,
            'address': f"FALLBACK{i}{date_str}",
            'price': price,
            'market_cap': market_cap,
            'volume_24h': volume,
            'image': '',
            'source': 'fallback'
        }
        tokens.append(token)
    
    # Reset random seed
    random.seed()
    
    return tokens

def create_realistic_trade(user_id, user_balance, token):
    """Create a realistic trade based on token data and user balance"""
    # Determine if this trade will be profitable
    is_profitable = random.random() < PROFIT_CHANCE
    
    # Determine how much of the user's balance to use
    trade_percent = random.uniform(MIN_CAPITAL_PERCENT, MAX_CAPITAL_PERCENT)
    trade_amount = user_balance * trade_percent
    
    # Calculate buy price based on token data
    buy_price_per_token = token['price'] * random.uniform(0.95, 1.05)  # ±5% from current price
    token_amount = trade_amount / buy_price_per_token
    
    # Calculate sell price based on profitability
    profit_loss_percent = 0
    if is_profitable:
        profit_loss_percent = random.uniform(MIN_PROFIT_PERCENT, MAX_PROFIT_PERCENT)
        sell_price_per_token = buy_price_per_token * (1 + profit_loss_percent)
    else:
        profit_loss_percent = -random.uniform(MIN_LOSS_PERCENT, MAX_LOSS_PERCENT)
        sell_price_per_token = buy_price_per_token * (1 + profit_loss_percent)
    
    # Calculate total return
    return_amount = token_amount * sell_price_per_token
    profit_loss = return_amount - trade_amount
    
    # Generate random times within the TIME_FRAME
    now = datetime.utcnow()
    max_delta = timedelta(hours=TIME_FRAME)
    buy_time = now - timedelta(hours=random.uniform(0, TIME_FRAME))
    
    # Sell time is after buy time (between 5 minutes and 8 hours later)
    min_sell_delta = timedelta(minutes=5)
    max_sell_delta = timedelta(hours=8)
    sell_delta = timedelta(seconds=random.uniform(min_sell_delta.total_seconds(), max_sell_delta.total_seconds()))
    sell_time = buy_time + sell_delta
    
    # Ensure sell time is not in the future
    if sell_time > now:
        sell_time = now - timedelta(minutes=random.randint(5, 60))
    
    # Create trade record
    trade = {
        'user_id': user_id,
        'token': token,
        'token_symbol': token['symbol'],
        'token_name': token['name'],
        'token_amount': token_amount,
        'buy_price': buy_price_per_token,
        'sell_price': sell_price_per_token,
        'trade_amount': trade_amount,
        'return_amount': return_amount,
        'profit_loss': profit_loss,
        'profit_loss_percent': profit_loss_percent * 100,  # Convert to percentage
        'buy_time': buy_time,
        'sell_time': sell_time,
        'is_profitable': is_profitable
    }
    
    return trade

def record_trade_in_database(user_id, trade):
    """Record a trade in the database with appropriate transaction and profit records"""
    with app.app_context():
        try:
            # Buy transaction
            buy_transaction = Transaction()
            buy_transaction.user_id = user_id
            buy_transaction.transaction_type = 'buy'
            buy_transaction.amount = trade['trade_amount']
            buy_transaction.token_name = trade['token_symbol']
            buy_transaction.timestamp = trade['buy_time']
            buy_transaction.status = 'completed'
            buy_transaction.notes = f"Bought {trade['token_amount']:.2f} {trade['token_symbol']} at {trade['buy_price']:.8f} SOL each"
            
            # Sell transaction
            sell_transaction = Transaction()
            sell_transaction.user_id = user_id
            sell_transaction.transaction_type = 'sell'
            sell_transaction.amount = trade['return_amount']
            sell_transaction.token_name = trade['token_symbol']
            sell_transaction.timestamp = trade['sell_time']
            sell_transaction.status = 'completed'
            sell_transaction.notes = f"Sold {trade['token_amount']:.2f} {trade['token_symbol']} at {trade['sell_price']:.8f} SOL each"
            
            # Profit record
            profit_record = Profit()
            profit_record.user_id = user_id
            profit_record.amount = trade['profit_loss']
            profit_record.timestamp = trade['sell_time']
            profit_record.source = f"Trading {trade['token_symbol']}"
            profit_record.description = f"{'Profit' if trade['is_profitable'] else 'Loss'} from trading {trade['token_name']} ({trade['profit_loss_percent']:.2f}%)"
            
            # Add to database
            db.session.add(buy_transaction)
            db.session.add(sell_transaction)
            db.session.add(profit_record)
            
            # Commit changes
            db.session.commit()
            
            return True, (buy_transaction.id, sell_transaction.id, profit_record.id)
        
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error recording trade: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, str(e)

def simulate_live_trading():
    """Main function to simulate live trading with real token data"""
    with app.app_context():
        try:
            # Get memecoin data
            tokens = fetch_recent_memecoins()
            if not tokens:
                logger.error("Failed to fetch token data from any source")
                return False
            
            logger.info(f"Fetched {len(tokens)} tokens")
            
            # Find user
            users_to_process = []
            if USERNAME:
                user = find_user_by_username(USERNAME)
                if user:
                    users_to_process.append(user)
                else:
                    logger.error(f"User {USERNAME} not found")
                    return False
            else:
                # Get all users with balance > 0
                users_to_process = User.query.filter(User.balance > 0).all()
            
            if not users_to_process:
                logger.error("No users found with positive balance")
                return False
            
            # Process users
            for user in users_to_process:
                logger.info(f"Processing user: {user.username} (ID: {user.id})")
                logger.info(f"Current balance: {user.balance} SOL")
                
                # Get user balance
                user_balance = user.balance
                
                # Create trades
                successful_trades = 0
                for i in range(NUM_TRADES):
                    # Select a random token
                    token = random.choice(tokens)
                    
                    # Create trade
                    trade = create_realistic_trade(user.id, user_balance, token)
                    
                    # Record trade
                    success, ids = record_trade_in_database(user.id, trade)
                    if success:
                        successful_trades += 1
                        logger.info(f"Trade {i+1} recorded successfully for {trade['token_symbol']}")
                        logger.info(f"  Amount: {trade['trade_amount']:.4f} SOL")
                        logger.info(f"  Return: {trade['return_amount']:.4f} SOL")
                        logger.info(f"  {'Profit' if trade['is_profitable'] else 'Loss'}: {trade['profit_loss']:.4f} SOL ({trade['profit_loss_percent']:.2f}%)")
                        logger.info(f"  Transaction IDs: Buy={ids[0]}, Sell={ids[1]}, Profit={ids[2]}")
                    else:
                        logger.error(f"Failed to record trade {i+1}: {ids}")
                
                logger.info(f"Successfully recorded {successful_trades}/{NUM_TRADES} trades for {user.username}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error simulating trading: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    # Run the simulation
    simulate_live_trading()