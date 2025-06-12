#!/usr/bin/env python3
"""
Production Telegram Bot - Optimized for 500+ Users
=================================================
High-performance bot with minimal database usage and efficient polling.
"""

import os
import sys
import json
import time
import logging
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from dataclasses import dataclass
from sqlalchemy import create_engine, text, NullPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class BotConfig:
    """Bot configuration with validation"""
    bot_token: str
    database_url: str
    admin_user_id: str = ""
    polling_timeout: int = 30
    max_concurrent_users: int = 500
    cache_ttl: int = 300
    rate_limit_messages: int = 10
    rate_limit_window: int = 60
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Create config from environment variables"""
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            # Use provided Neon database
            database_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        
        return cls(
            bot_token=bot_token,
            database_url=database_url,
            admin_user_id=os.getenv('ADMIN_USER_ID', ''),
        )

class MemoryCache:
    """Thread-safe in-memory cache"""
    
    def __init__(self, max_size: int = 5000, ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry['timestamp'] < self.ttl:
                    return entry['value']
                else:
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cached value with timestamp"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Remove oldest 10% of entries
                oldest_keys = sorted(
                    self._cache.keys(),
                    key=lambda k: self._cache[k]['timestamp']
                )[:max(1, len(self._cache) // 10)]
                
                for old_key in oldest_keys:
                    del self._cache[old_key]
            
            self._cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
    
    def delete(self, key: str) -> None:
        """Delete cached value"""
        with self._lock:
            self._cache.pop(key, None)

class DatabaseManager:
    """Optimized database manager with NullPool"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            poolclass=NullPool,  # No idle connections
            pool_pre_ping=True,
            connect_args={
                "sslmode": "require",
                "connect_timeout": 30,
                "application_name": "production_telegram_bot"
            },
            echo=False
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("Database initialized with NullPool")
    
    def execute_query(self, query: str, params: Dict = None, fetch_one: bool = False) -> Any:
        """Execute SQL query with automatic retry"""
        max_retries = 3
        for attempt in range(max_retries):
            session = None
            try:
                session = self.SessionLocal()
                result = session.execute(text(query), params or {})
                
                if fetch_one:
                    data = result.fetchone()
                    session.commit()
                    return data
                else:
                    data = result.fetchall()
                    session.commit()
                    return data
                    
            except SQLAlchemyError as e:
                if session:
                    session.rollback()
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"DB query failed (attempt {attempt + 1}): {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"DB query failed after {max_retries} attempts: {e}")
                    raise
            finally:
                if session:
                    session.close()
    
    def batch_insert(self, table: str, records: List[Dict]) -> None:
        """Batch insert records"""
        if not records:
            return
        
        # Build query
        columns = list(records[0].keys())
        placeholders = ', '.join([f':{col}' for col in columns])
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        session = None
        try:
            session = self.SessionLocal()
            session.execute(text(query), records)
            session.commit()
            logger.debug(f"Batch inserted {len(records)} records into {table}")
        except SQLAlchemyError as e:
            if session:
                session.rollback()
            logger.error(f"Batch insert failed: {e}")
            raise
        finally:
            if session:
                session.close()

class ProductionBot:
    """High-performance Telegram bot for 500+ users"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.api_url = f"https://api.telegram.org/bot{config.bot_token}"
        self.running = False
        self.offset = 0
        
        # Initialize components
        self.db = DatabaseManager(config.database_url)
        self.cache = MemoryCache(max_size=5000, ttl=config.cache_ttl)
        
        # Handler registry
        self.command_handlers: Dict[str, Callable] = {}
        self.callback_handlers: Dict[str, Callable] = {}
        
        # Rate limiting
        self.user_message_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=config.rate_limit_messages))
        self.processed_updates: deque = deque(maxlen=1000)
        
        # Background task queues
        self.pending_db_operations: List[Dict] = []
        self.pending_messages: List[Dict] = []
        
        logger.info("Production bot initialized")
    
    def add_command_handler(self, command: str, handler: Callable) -> None:
        """Register command handler"""
        self.command_handlers[command] = handler
        logger.debug(f"Added command handler: /{command}")
    
    def add_callback_handler(self, pattern: str, handler: Callable) -> None:
        """Register callback handler"""
        self.callback_handlers[pattern] = handler
        logger.debug(f"Added callback handler: {pattern}")
    
    def is_rate_limited(self, user_id: str) -> bool:
        """Check if user is rate limited"""
        now = time.time()
        user_times = self.user_message_times[user_id]
        
        # Remove old timestamps
        while user_times and user_times[0] < now - self.config.rate_limit_window:
            user_times.popleft()
        
        if len(user_times) >= self.config.rate_limit_messages:
            return True
        
        user_times.append(now)
        return False
    
    def send_message(self, chat_id: str, text: str, reply_markup: Dict = None) -> bool:
        """Send message with error handling"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text[:4096],  # Telegram limit
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=data,
                timeout=30
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False
    
    def get_user_cached(self, telegram_id: str) -> Optional[Dict]:
        """Get user data with caching"""
        cache_key = f"user:{telegram_id}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        # Fetch from database
        try:
            result = self.db.execute_query(
                """
                SELECT id, telegram_id, username, first_name, balance, 
                       initial_deposit, status, joined_at
                FROM "user" 
                WHERE telegram_id = :telegram_id
                """,
                {"telegram_id": telegram_id},
                fetch_one=True
            )
            
            if result:
                user_data = {
                    'id': result[0],
                    'telegram_id': result[1],
                    'username': result[2],
                    'first_name': result[3],
                    'balance': float(result[4]) if result[4] else 0.0,
                    'initial_deposit': float(result[5]) if result[5] else 0.0,
                    'status': result[6],
                    'joined_at': result[7]
                }
                
                self.cache.set(cache_key, user_data)
                return user_data
                
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}")
        
        return None
    
    def create_user(self, telegram_id: str, username: str = None, first_name: str = None) -> Optional[Dict]:
        """Create new user"""
        try:
            result = self.db.execute_query(
                """
                INSERT INTO "user" (telegram_id, username, first_name, status, 
                                  balance, initial_deposit, joined_at, last_activity)
                VALUES (:telegram_id, :username, :first_name, 'onboarding', 
                        0.0, 0.0, :now, :now)
                RETURNING id
                """,
                {
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "now": datetime.utcnow()
                },
                fetch_one=True
            )
            
            if result:
                user_data = {
                    'id': result[0],
                    'telegram_id': telegram_id,
                    'username': username,
                    'first_name': first_name,
                    'balance': 0.0,
                    'initial_deposit': 0.0,
                    'status': 'onboarding',
                    'joined_at': datetime.utcnow()
                }
                
                # Cache the new user
                self.cache.set(f"user:{telegram_id}", user_data)
                return user_data
                
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
        
        return None
    
    def get_updates(self) -> List[Dict]:
        """Get updates from Telegram with long polling"""
        try:
            params = {
                'offset': self.offset,
                'timeout': self.config.polling_timeout,
                'limit': 100,
                'allowed_updates': ['message', 'callback_query']
            }
            
            response = requests.get(
                f"{self.api_url}/getUpdates",
                params=params,
                timeout=self.config.polling_timeout + 10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    updates = data['result']
                    if updates:
                        self.offset = updates[-1]['update_id'] + 1
                    return updates
                    
        except requests.exceptions.Timeout:
            # Expected with long polling
            pass
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            time.sleep(5)
        
        return []
    
    def process_update(self, update: Dict) -> None:
        """Process single update"""
        try:
            update_id = update.get('update_id', 0)
            
            # Skip duplicates
            if update_id in self.processed_updates:
                return
            
            self.processed_updates.append(update_id)
            
            if 'message' in update:
                self.process_message(update['message'])
            elif 'callback_query' in update:
                self.process_callback_query(update['callback_query'])
                
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    def process_message(self, message: Dict) -> None:
        """Process incoming message"""
        try:
            chat_id = str(message['chat']['id'])
            user_id = str(message['from']['id'])
            text = message.get('text', '')
            
            # Rate limiting
            if self.is_rate_limited(user_id):
                return
            
            # Handle commands
            if text.startswith('/'):
                command = text.split()[0][1:].split('@')[0]
                
                if command in self.command_handlers:
                    # Run handler in background thread
                    threading.Thread(
                        target=self._safe_execute,
                        args=(self.command_handlers[command], message),
                        daemon=True
                    ).start()
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def process_callback_query(self, callback_query: Dict) -> None:
        """Process callback query"""
        try:
            user_id = str(callback_query['from']['id'])
            data = callback_query.get('data', '')
            
            if self.is_rate_limited(user_id):
                return
            
            # Answer callback query
            requests.post(
                f"{self.api_url}/answerCallbackQuery",
                json={'callback_query_id': callback_query['id']},
                timeout=10
            )
            
            # Find matching handler
            for pattern, handler in self.callback_handlers.items():
                if data == pattern or data.startswith(pattern):
                    threading.Thread(
                        target=self._safe_execute,
                        args=(handler, callback_query),
                        daemon=True
                    ).start()
                    break
                    
        except Exception as e:
            logger.error(f"Error processing callback query: {e}")
    
    def _safe_execute(self, handler: Callable, data: Dict) -> None:
        """Execute handler with error handling"""
        try:
            handler(data, self)
        except Exception as e:
            logger.error(f"Error in handler: {e}")
    
    def start_background_tasks(self) -> None:
        """Start background processing tasks"""
        # Database batch processor
        db_thread = threading.Thread(target=self._process_db_queue, daemon=True)
        db_thread.start()
        
        # Message batch processor
        msg_thread = threading.Thread(target=self._process_message_queue, daemon=True)
        msg_thread.start()
        
        logger.info("Background tasks started")
    
    def _process_db_queue(self) -> None:
        """Process database operations in batches"""
        while self.running:
            try:
                if self.pending_db_operations:
                    # Process up to 50 operations at once
                    batch = self.pending_db_operations[:50]
                    self.pending_db_operations = self.pending_db_operations[50:]
                    
                    for operation in batch:
                        try:
                            self.db.execute_query(
                                operation['query'],
                                operation.get('params', {})
                            )
                        except Exception as e:
                            logger.error(f"DB operation failed: {e}")
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in DB queue processor: {e}")
                time.sleep(5)
    
    def _process_message_queue(self) -> None:
        """Process message queue in batches"""
        while self.running:
            try:
                if self.pending_messages:
                    # Process up to 20 messages at once
                    batch = self.pending_messages[:20]
                    self.pending_messages = self.pending_messages[20:]
                    
                    for msg in batch:
                        self.send_message(**msg)
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in message queue processor: {e}")
                time.sleep(5)
    
    def queue_db_operation(self, query: str, params: Dict = None) -> None:
        """Queue database operation for batch processing"""
        self.pending_db_operations.append({
            'query': query,
            'params': params or {}
        })
    
    def queue_message(self, chat_id: str, text: str, reply_markup: Dict = None) -> None:
        """Queue message for batch processing"""
        self.pending_messages.append({
            'chat_id': chat_id,
            'text': text,
            'reply_markup': reply_markup
        })
    
    def run(self) -> None:
        """Main bot loop"""
        logger.info("Starting production bot...")
        self.running = True
        
        # Start background tasks
        self.start_background_tasks()
        
        consecutive_errors = 0
        
        while self.running:
            try:
                updates = self.get_updates()
                
                if updates:
                    logger.debug(f"Processing {len(updates)} updates")
                    
                    # Process updates concurrently
                    threads = []
                    for update in updates:
                        thread = threading.Thread(
                            target=self.process_update,
                            args=(update,),
                            daemon=True
                        )
                        thread.start()
                        threads.append(thread)
                    
                    # Wait for completion
                    for thread in threads:
                        thread.join(timeout=30)
                
                consecutive_errors = 0
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in main loop: {e}")
                
                if consecutive_errors >= 5:
                    logger.error("Too many errors, pausing...")
                    time.sleep(60)
                    consecutive_errors = 0
                else:
                    time.sleep(5)
        
        self.running = False
        logger.info("Bot stopped")

# Command Handlers
def start_handler(message: Dict, bot: ProductionBot) -> None:
    """Handle /start command"""
    chat_id = str(message['chat']['id'])
    telegram_id = str(message['from']['id'])
    username = message['from'].get('username', '')
    first_name = message['from'].get('first_name', '')
    
    # Get or create user
    user = bot.get_user_cached(telegram_id)
    if not user:
        user = bot.create_user(telegram_id, username, first_name)
    
    if not user:
        bot.send_message(chat_id, "⚠️ Error creating account. Please try again.")
        return
    
    # Update activity (queued)
    bot.queue_db_operation(
        "UPDATE \"user\" SET last_activity = :now WHERE telegram_id = :telegram_id",
        {"telegram_id": telegram_id, "now": datetime.utcnow()}
    )
    
    # Send welcome message
    welcome_text = """
🚀 <b>Welcome to Solana Memecoin Trading Bot!</b>

Automated trading for profitable memecoin opportunities on Solana.

<b>Quick Start:</b>
💰 /deposit - Add SOL to start trading
📊 /dashboard - View your portfolio
⚙️ /settings - Configure preferences
❓ /help - Get help

Ready to start earning?
"""
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '💰 Make Deposit', 'callback_data': 'deposit'}],
            [{'text': '📊 Dashboard', 'callback_data': 'dashboard'}],
            [{'text': '❓ How It Works', 'callback_data': 'how_it_works'}]
        ]
    }
    
    bot.send_message(chat_id, welcome_text, keyboard)

def dashboard_handler(message: Dict, bot: ProductionBot) -> None:
    """Handle /dashboard command"""
    chat_id = str(message['chat']['id'])
    telegram_id = str(message['from']['id'])
    
    user = bot.get_user_cached(telegram_id)
    if not user:
        bot.send_message(chat_id, "Please use /start first.")
        return
    
    # Calculate ROI
    roi = 0.0
    if user['initial_deposit'] > 0:
        roi = ((user['balance'] - user['initial_deposit']) / user['initial_deposit']) * 100
    
    dashboard_text = f"""
📊 <b>Your Trading Dashboard</b>

💰 <b>Balance:</b> {user['balance']:.4f} SOL
💵 <b>Initial Deposit:</b> {user['initial_deposit']:.4f} SOL
📈 <b>ROI:</b> {roi:+.2f}%
📅 <b>Joined:</b> {user['joined_at'].strftime('%Y-%m-%d') if user['joined_at'] else 'Unknown'}

<b>Status:</b> {user['status'].title()}

Use the buttons below to manage your account.
"""
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '💰 Deposit', 'callback_data': 'deposit'}, 
             {'text': '💸 Withdraw', 'callback_data': 'withdraw'}],
            [{'text': '📈 Positions', 'callback_data': 'positions'}, 
             {'text': '📜 History', 'callback_data': 'history'}],
            [{'text': '🔄 Refresh', 'callback_data': 'dashboard'}]
        ]
    }
    
    bot.send_message(chat_id, dashboard_text, keyboard)

def deposit_handler(message: Dict, bot: ProductionBot) -> None:
    """Handle /deposit command"""
    chat_id = str(message['chat']['id'])
    telegram_id = str(message['from']['id'])
    
    user = bot.get_user_cached(telegram_id)
    if not user:
        bot.send_message(chat_id, "Please use /start first.")
        return
    
    admin_wallet = "Soa8DkfSzZEmXLJ2AWEqm76fgrSWYxT5iPg6kDdZbKmx"
    
    deposit_text = f"""
💰 <b>Make a Deposit</b>

Send SOL to this wallet:
<code>{admin_wallet}</code>

<b>Important:</b>
• Minimum: 0.1 SOL
• Auto-detection within 5 minutes
• Trading starts immediately

<b>Current Balance:</b> {user['balance']:.4f} SOL
"""
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '📋 Copy Address', 'callback_data': f'copy:{admin_wallet}'}],
            [{'text': '🔍 Check Status', 'callback_data': 'check_deposit'}],
            [{'text': '🏠 Dashboard', 'callback_data': 'dashboard'}]
        ]
    }
    
    bot.send_message(chat_id, deposit_text, keyboard)

def help_handler(message: Dict, bot: ProductionBot) -> None:
    """Handle /help command"""
    chat_id = str(message['chat']['id'])
    
    help_text = """
🤖 <b>Solana Trading Bot Help</b>

<b>Commands:</b>
/start - Initialize account
/dashboard - View portfolio
/deposit - Add SOL funds  
/help - Show this help

<b>How It Works:</b>
1. Deposit SOL to start trading
2. AI monitors memecoin markets 24/7
3. Automatic trades on profitable opportunities
4. Daily profits added to your balance
5. Withdraw anytime

<b>Support:</b> Contact @support

Ready to start? Use /deposit!
"""
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '💰 Deposit', 'callback_data': 'deposit'}],
            [{'text': '📊 Dashboard', 'callback_data': 'dashboard'}]
        ]
    }
    
    bot.send_message(chat_id, help_text, keyboard)

# Callback Handlers
def callback_handler(callback_query: Dict, bot: ProductionBot) -> None:
    """Handle callback queries"""
    chat_id = str(callback_query['message']['chat']['id'])
    data = callback_query['data']
    
    if data == 'dashboard':
        fake_message = {
            'chat': {'id': chat_id},
            'from': {'id': callback_query['from']['id']}
        }
        dashboard_handler(fake_message, bot)
        
    elif data == 'deposit':
        fake_message = {
            'chat': {'id': chat_id},
            'from': {'id': callback_query['from']['id']}
        }
        deposit_handler(fake_message, bot)
        
    elif data == 'how_it_works':
        how_it_works_text = """
🎯 <b>How Our AI Trading Works</b>

<b>🔍 Market Analysis:</b>
• Monitor 1000+ Solana tokens
• Identify breakout patterns
• Track whale movements

<b>⚡ Automated Trading:</b>
• Execute trades in milliseconds
• Built-in risk management
• Portfolio diversification

<b>📈 Profit Strategies:</b>
• Scalping (2-5% gains)
• Early token launches
• Trend reversals

<b>💰 Returns:</b>
• 80% to your balance
• 20% reinvested

Start with 0.1 SOL minimum!
"""
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '💰 Start Trading', 'callback_data': 'deposit'}],
                [{'text': '🏠 Back', 'callback_data': 'dashboard'}]
            ]
        }
        
        bot.send_message(chat_id, how_it_works_text, keyboard)
        
    elif data.startswith('copy:'):
        address = data.split(':', 1)[1]
        bot.send_message(
            chat_id,
            f"📋 <b>Wallet Address:</b>\n<code>{address}</code>\n\nTap to copy, then send SOL to this address."
        )

def main():
    """Main entry point"""
    try:
        config = BotConfig.from_env()
        bot = ProductionBot(config)
        
        # Register handlers
        bot.add_command_handler('start', start_handler)
        bot.add_command_handler('dashboard', dashboard_handler)
        bot.add_command_handler('deposit', deposit_handler)
        bot.add_command_handler('help', help_handler)
        
# DISABLED:         bot.add_callback_handler('dashboard', callback_handler)  # Duplicate handler - use bot_v20_runner.py instead
# DISABLED:         bot.add_callback_handler('deposit', callback_handler)  # Duplicate handler - use bot_v20_runner.py instead
# DISABLED:         bot.add_callback_handler('how_it_works', callback_handler)  # Duplicate handler - use bot_v20_runner.py instead
        bot.add_callback_handler('copy:', callback_handler)
        
        # Start bot
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()