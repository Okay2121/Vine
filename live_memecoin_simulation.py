#!/usr/bin/env python
"""
Script to simulate live trading using real-time memecoin data from pump.fun
"""
import logging
import sys
import random
import requests
import json
from datetime import datetime, timedelta
from app import app, db
from models import User, Transaction, Profit

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for the operation
USERNAME = "@briensmart"
MAX_TRADES = 3  # Number of trades to simulate

# API endpoints for fetching memecoin data
PUMP_FUN_API = "https://client-api.pump.fun/tokens/recent"
BIRDEYE_API = "https://api.birdeye.so/defi/hot_tokens/v1?chain=solana&count=20"  # Fallback API

def find_user_by_username(username):
    """Find a user by their Telegram username"""
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Try to find the user with case-insensitive search
    user = User.query.filter(User.username.ilike(username)).first()
    return user

def fetch_recent_memecoins():
    """Fetch recent memecoin data from pump.fun or fallback to birdeye"""
    try:
        # Try pump.fun first
        logger.info("Attempting to fetch data from pump.fun...")
        response = requests.get(PUMP_FUN_API, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                logger.info(f"Successfully fetched {len(data['data'])} tokens from pump.fun")
                
                # Format the data to a standard structure
                formatted_tokens = []
                for token in data['data']:
                    formatted_tokens.append({
                        'name': token.get('name', 'Unknown Token'),
                        'symbol': token.get('symbol', 'UNKNOWN'),
                        'price': token.get('price', 0.000001),
                        'market_cap': token.get('marketCap', 1000000),
                        'volume_24h': token.get('volume24h', 100000),
                        'address': token.get('address', ''),
                        'source': 'pump_fun',
                        'launch_date': token.get('launchDate', datetime.utcnow().isoformat()),
                    })
                return formatted_tokens
        
        logger.warning("Failed to get data from pump.fun, trying birdeye...")
        
        # Try birdeye as fallback
        response = requests.get(BIRDEYE_API, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                logger.info(f"Successfully fetched {len(data['data'])} tokens from birdeye")
                
                # Format the data to a standard structure
                formatted_tokens = []
                for token in data['data']:
                    formatted_tokens.append({
                        'name': token.get('symbol', 'Unknown Token'),  # Birdeye often has symbol as main identifier
                        'symbol': token.get('symbol', 'UNKNOWN'),
                        'price': token.get('price', 0.000001),
                        'market_cap': token.get('mc', 1000000),
                        'volume_24h': token.get('volume', 100000),
                        'address': token.get('address', ''),
                        'source': 'birdeye',
                        'launch_date': datetime.utcnow().isoformat(),  # Birdeye doesn't provide launch date
                    })
                return formatted_tokens
                
        logger.error("Failed to fetch data from both sources")
        return generate_fallback_tokens()
        
    except Exception as e:
        logger.error(f"Error fetching tokens: {e}")
        return generate_fallback_tokens()

def generate_fallback_tokens():
    """Generate fallback token data if API calls fail"""
    logger.warning("Using fallback generated token data")
    
    # List of popular memecoin names and symbols for fallback
    memecoin_options = [
        {"name": "Dogecoin", "symbol": "DOGE"},
        {"name": "Shiba Inu", "symbol": "SHIB"},
        {"name": "Pepe", "symbol": "PEPE"},
        {"name": "Floki Inu", "symbol": "FLOKI"},
        {"name": "Bonk", "symbol": "BONK"},
        {"name": "Mog Coin", "symbol": "MOG"},
        {"name": "Popcat", "symbol": "POPCAT"},
        {"name": "Meme Kombat", "symbol": "MK"},
        {"name": "Brett", "symbol": "BRETT"},
        {"name": "Turbo", "symbol": "TURBO"},
        {"name": "Cat in a Dogs World", "symbol": "MEW"},
        {"name": "WIF", "symbol": "WIF"},
        {"name": "Dogs", "symbol": "DOGS"},
        {"name": "Kitty", "symbol": "KIT"},
        {"name": "Goated", "symbol": "GOAT"}
    ]
    
    # Generate random tokens based on the list
    tokens = []
    for i in range(10):
        coin = random.choice(memecoin_options)
        price = random.uniform(0.0000001, 0.01)
        market_cap = random.uniform(500000, 50000000)
        volume = random.uniform(50000, 5000000)
        
        tokens.append({
            'name': coin["name"],
            'symbol': coin["symbol"],
            'price': price,
            'market_cap': market_cap,
            'volume_24h': volume,
            'address': f"FakeSolanaAddress{i}",
            'source': 'fallback',
            'launch_date': datetime.utcnow().isoformat(),
        })
    
    return tokens

def create_realistic_trade(user_id, user_balance, token):
    """Create a realistic trade based on token data and user balance"""
    # Determine if this will be a profitable trade (70% chance)
    is_profitable = random.random() < 0.7
    
    # Calculate trade parameters
    current_time = datetime.utcnow()
    
    # Use between 10-30% of user balance for a trade
    trade_percent = random.uniform(0.1, 0.3)
    trade_amount = user_balance * trade_percent
    
    # Calculate holding time in minutes (5-120 minutes)
    holding_time = random.randint(5, 120)
    entry_time = current_time - timedelta(minutes=holding_time)
    exit_time = current_time
    
    # Get token details
    token_name = token['name']
    token_symbol = token['symbol']
    entry_price = token['price']
    
    # Calculate profit/loss percentage
    if is_profitable:
        profit_percent = random.uniform(2.5, 35.0)  # 2.5% to 35% profit
        exit_price = entry_price * (1 + (profit_percent / 100))
    else:
        profit_percent = -random.uniform(1.0, 15.0)  # 1% to 15% loss
        exit_price = entry_price * (1 + (profit_percent / 100))
    
    # Calculate profit amount
    profit_amount = trade_amount * (profit_percent / 100)
    
    # Format token link based on source
    token_address = token.get('address', '')
    token_source = token.get('source', 'birdeye')
    
    if token_source == 'pump_fun':
        token_link = f"https://pump.fun/{token_address}"
    else:
        token_link = f"https://birdeye.so/token/{token_address}?chain=solana"
    
    # Create a trade record
    trade = {
        'user_id': user_id,
        'token_name': token_name,
        'token_symbol': token_symbol,
        'token_link': token_link,
        'trade_amount': trade_amount,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'entry_time': entry_time.isoformat(),
        'exit_time': exit_time.isoformat(),
        'profit_amount': profit_amount,
        'profit_percent': profit_percent,
        'market_cap': token.get('market_cap', 0),
        'volume': token.get('volume_24h', 0)
    }
    
    return trade, user_balance + profit_amount

def record_trade_in_database(user_id, trade):
    """Record a trade in the database with appropriate transaction and profit records"""
    # Validate trade input
    if trade is None:
        logger.error(f"Cannot record trade for user {user_id}: trade data is None")
        return False
    
    with app.app_context():
        try:
            # Get the user
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found when recording trade")
                return False
            
            # Create a transaction record for buy
            buy_transaction = Transaction(
                user_id=user_id,
                transaction_type="buy",
                amount=trade['trade_amount'],
                token_name=f"{trade['token_name']} ({trade['token_symbol']})",
                timestamp=datetime.fromisoformat(trade['entry_time']),
                status="completed",
                notes=f"Auto trade entry at {trade['entry_price']:.8f} USD"
            )
            
            # Create a transaction record for sell
            sell_amount = trade['trade_amount']
            if trade['profit_amount'] > 0:
                sell_amount += trade['profit_amount']
                
            sell_transaction = Transaction(
                user_id=user_id,
                transaction_type="sell",
                amount=sell_amount,
                token_name=f"{trade['token_name']} ({trade['token_symbol']})",
                timestamp=datetime.fromisoformat(trade['exit_time']),
                status="completed",
                notes=f"Auto trade exit at {trade['exit_price']:.8f} USD"
            )
            
            # Record the profit/loss
            profit_record = Profit(
                user_id=user_id,
                amount=trade['profit_amount'],
                percentage=trade['profit_percent'],
                date=datetime.fromisoformat(trade['exit_time']).date()
            )
            
            # Add records to database
            db.session.add(buy_transaction)
            db.session.add(sell_transaction)
            db.session.add(profit_record)
            
            # Update user balance with the profit
            user.balance += trade['profit_amount']
            
            # Commit the changes
            db.session.commit()
            
            logger.info(f"Trade record created for {trade['token_name']} ({trade['token_symbol']})")
            logger.info(f"Profit: {trade['profit_amount']:.4f} SOL ({trade['profit_percent']:.2f}%)")
            
            return True
            
        except Exception as e:
            # Handle database errors
            db.session.rollback()
            logger.error(f"Database error during trade recording: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def simulate_live_trading():
    """Main function to simulate live trading with real token data"""
    with app.app_context():
        # Find the user
        user = find_user_by_username(USERNAME)
        
        if not user:
            logger.error(f"User {USERNAME} not found")
            return False
        
        logger.info(f"Simulating live trading for user: {user.username} (ID: {user.id})")
        logger.info(f"Starting balance: {user.balance:.4f} SOL")
        
        # Fetch real token data
        tokens = fetch_recent_memecoins()
        
        if not tokens:
            logger.error("No tokens available for trading simulation")
            return False
        
        logger.info(f"Retrieved {len(tokens)} tokens for trade simulation")
        
        # Shuffle tokens to get random selection
        random.shuffle(tokens)
        
        # Select tokens for trading
        selected_tokens = tokens[:MAX_TRADES]
        
        # Track balance changes
        current_balance = user.balance
        
        # Create trade records
        successful_trades = 0
        
        for token in selected_tokens:
            # Generate a trade
            trade_result = create_realistic_trade(user.id, current_balance, token)
            
            if trade_result:
                trade, new_balance = trade_result
                
                # Record the trade
                if record_trade_in_database(user.id, trade):
                    current_balance = new_balance
                    successful_trades += 1
                    
                    # Log the trade
                    profit_emoji = "✅" if trade['profit_amount'] > 0 else "❌"
                    logger.info(f"{profit_emoji} Trade: {trade['token_name']} ({trade['token_symbol']})")
                    logger.info(f"   Amount: {trade['trade_amount']:.4f} SOL")
                    logger.info(f"   Profit: {trade['profit_amount']:.4f} SOL ({trade['profit_percent']:.2f}%)")
                    logger.info(f"   Current Balance: {current_balance:.4f} SOL")
        
        logger.info(f"Successfully completed {successful_trades} trades")
        logger.info(f"Final balance: {current_balance:.4f} SOL")
        
        return successful_trades > 0

if __name__ == "__main__":
    # Run the live trading simulation
    success = simulate_live_trading()
    sys.exit(0 if success else 1)