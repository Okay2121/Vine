#!/usr/bin/env python3
"""
Production-Ready Telegram Bot for 500+ Users
=============================================
Optimized for minimal resource usage with Neon PostgreSQL and AWS deployment.

Features:
- Efficient polling with timeout=30 and read_latency=5
- NullPool for zero idle connections
- In-memory caching to reduce DB hits
- Batch processing and connection reuse
- Async support for non-blocking operations
- Webhook-ready architecture
- Production error handling and logging
"""

import asyncio
import logging
import os
import sys
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from functools import wraps
import hashlib

import requests
from sqlalchemy import create_engine, text, NullPool
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class ProductionCache:
    """High-performance in-memory cache to reduce database hits"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict] = {}
        self.access_times: Dict[str, float] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self.cache:
                # Check TTL
                if time.time() - self.access_times[key] < self.ttl_seconds:
                    self.access_times[key] = time.time()  # Update access time
                    return self.cache[key]
                else:
                    # Expired, remove
                    del self.cache[key]
                    del self.access_times[key]
            return None
    
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            # Evict old entries if cache is full
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def delete(self, key: str) -> None:
        with self._lock:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def _evict_oldest(self) -> None:
        # Remove 10% of oldest entries
        entries_to_remove = max(1, len(self.cache) // 10)
        oldest_keys = sorted(self.access_times.keys(), 
                           key=lambda k: self.access_times[k])[:entries_to_remove]
        
        for key in oldest_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def clear(self) -> None:
        with self._lock:
            self.cache.clear()
            self.access_times.clear()

class DatabaseManager:
    """Optimized database manager for Neon PostgreSQL with connection pooling"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.Session = None
        self._initialize_engine()
        
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with NullPool for serverless"""
        try:
            # Use NullPool to avoid idle connections
            self.engine = create_engine(
                self.database_url,
                poolclass=NullPool,  # No connection pooling - creates new connections as needed
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    "sslmode": "require",
                    "connect_timeout": 30,
                    "application_name": "telegram_bot_production",
                    "keepalives_idle": 600,
                    "keepalives_interval": 60,
                    "keepalives_count": 3
                },
                echo=False,  # Disable SQL logging in production
                future=True
            )
            
            # Create session factory
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            logger.info("Database engine initialized with NullPool")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def get_session(self):
        """Get a database session - always creates new connection with NullPool"""
        return self.Session()
    
    def execute_with_retry(self, operation, max_retries: int = 3, delay: float = 1.0):
        """Execute database operation with retry logic"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                session = self.get_session()
                try:
                    result = operation(session)
                    session.commit()
                    return result
                finally:
                    session.close()
                    
            except (SQLAlchemyError, DisconnectionError, OperationalError) as e:
                last_exception = e
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} database attempts failed")
                    
        if last_exception:
            raise last_exception
        else:
            raise Exception("Database operation failed with unknown error")
    
    def batch_execute(self, operations: List[callable]) -> List[Any]:
        """Execute multiple operations in a single transaction"""
        def batch_operation(session):
            results = []
            for op in operations:
                result = op(session)
                results.append(result)
            return results
        
        return self.execute_with_retry(batch_operation)

class TelegramBotOptimized:
    """Production-ready Telegram bot optimized for 500+ users"""
    
    def __init__(self, token: str, database_url: str):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.running = False
        self.offset = 0
        
        # Initialize database manager
        self.db = DatabaseManager(database_url)
        
        # Initialize cache
        self.cache = ProductionCache(max_size=5000, ttl_seconds=300)  # 5 minute TTL
        
        # Handler registry
        self.command_handlers: Dict[str, callable] = {}
        self.callback_handlers: Dict[str, callable] = {}
        self.message_handlers: List[callable] = []
        
        # Rate limiting and deduplication
        self.processed_updates: deque = deque(maxlen=1000)  # Track recent updates
        self.user_message_times: defaultdict = defaultdict(deque)  # Rate limiting per user
        
        # Batch processing queues
        self.pending_notifications: List[Dict] = []
        self.pending_db_writes: List[Dict] = []
        
        # Background tasks
        self.background_tasks: List[threading.Thread] = []
        
        logger.info(f"Bot initialized for production use")
    
    def add_command_handler(self, command: str, handler: callable):
        """Register command handler"""
        self.command_handlers[command] = handler
        logger.debug(f"Registered command handler: /{command}")
    
    def add_callback_handler(self, pattern: str, handler: callable):
        """Register callback query handler"""
        self.callback_handlers[pattern] = handler
        logger.debug(f"Registered callback handler: {pattern}")
    
    def add_message_handler(self, handler: callable):
        """Register message handler"""
        self.message_handlers.append(handler)
        logger.debug("Registered message handler")
    
    def rate_limit_user(self, user_id: str, limit: int = 10, window: int = 60) -> bool:
        """Check if user is rate limited"""
        now = time.time()
        user_times = self.user_message_times[user_id]
        
        # Remove old entries
        while user_times and user_times[0] < now - window:
            user_times.popleft()
        
        # Check if under limit
        if len(user_times) >= limit:
            return True
        
        # Add current time
        user_times.append(now)
        return False
    
    def is_duplicate_update(self, update_id: int) -> bool:
        """Check if update was already processed"""
        if update_id in self.processed_updates:
            return True
        
        self.processed_updates.append(update_id)
        return False
    
    def cache_user_data(self, user_id: str, data: Dict) -> None:
        """Cache user data to reduce DB hits"""
        cache_key = f"user:{user_id}"
        self.cache.set(cache_key, data)
    
    def get_cached_user_data(self, user_id: str) -> Optional[Dict]:
        """Get cached user data"""
        cache_key = f"user:{user_id}"
        return self.cache.get(cache_key)
    
    def send_message_safe(self, chat_id: str, text: str, **kwargs) -> Optional[Dict]:
        """Send message with error handling and rate limiting"""
        try:
            # Prepare request data
            data = {
                'chat_id': chat_id,
                'text': text[:4096],  # Telegram message limit
                'parse_mode': kwargs.get('parse_mode', 'HTML'),
                'disable_web_page_preview': kwargs.get('disable_web_page_preview', True)
            }
            
            # Add reply markup if provided
            if 'reply_markup' in kwargs:
                data['reply_markup'] = json.dumps(kwargs['reply_markup'])
            
            # Send request
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to send message to {chat_id}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return None
    
    def get_updates_optimized(self, timeout: int = 30) -> List[Dict]:
        """Get updates with optimized polling settings"""
        try:
            params = {
                'offset': self.offset,
                'timeout': timeout,  # Long polling for efficiency
                'limit': 100,       # Process up to 100 updates per request
                'allowed_updates': ['message', 'callback_query']  # Only what we need
            }
            
            response = requests.get(
                f"{self.api_url}/getUpdates",
                params=params,
                timeout=timeout + 10  # Request timeout slightly higher than polling timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    updates = data['result']
                    if updates:
                        # Update offset to mark these as processed
                        self.offset = updates[-1]['update_id'] + 1
                    return updates
            else:
                logger.warning(f"Failed to get updates: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            # Timeout is expected with long polling
            pass
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            time.sleep(5)  # Brief pause on error
        
        return []
    
    def process_update(self, update: Dict) -> None:
        """Process a single update efficiently"""
        try:
            update_id = update.get('update_id')
            
            # Skip duplicate updates
            if self.is_duplicate_update(update_id):
                return
            
            # Process message
            if 'message' in update:
                self.process_message(update['message'])
            
            # Process callback query
            elif 'callback_query' in update:
                self.process_callback_query(update['callback_query'])
                
        except Exception as e:
            logger.error(f"Error processing update {update.get('update_id')}: {e}")
    
    def process_message(self, message: Dict) -> None:
        """Process incoming message"""
        try:
            chat_id = str(message['chat']['id'])
            user_id = str(message['from']['id'])
            text = message.get('text', '')
            
            # Rate limiting
            if self.rate_limit_user(user_id):
                logger.warning(f"Rate limiting user {user_id}")
                return
            
            # Handle commands
            if text.startswith('/'):
                command = text.split()[0][1:].split('@')[0]  # Remove bot mention
                
                if command in self.command_handlers:
                    handler = self.command_handlers[command]
                    # Run handler in thread to avoid blocking
                    threading.Thread(
                        target=self._safe_handler_execution,
                        args=(handler, message),
                        daemon=True
                    ).start()
                    return
            
            # Handle regular messages
            for handler in self.message_handlers:
                threading.Thread(
                    target=self._safe_handler_execution,
                    args=(handler, message),
                    daemon=True
                ).start()
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def process_callback_query(self, callback_query: Dict) -> None:
        """Process callback query"""
        try:
            user_id = str(callback_query['from']['id'])
            data = callback_query.get('data', '')
            
            # Rate limiting
            if self.rate_limit_user(user_id):
                return
            
            # Find matching handler
            for pattern, handler in self.callback_handlers.items():
                if data.startswith(pattern) or data == pattern:
                    threading.Thread(
                        target=self._safe_handler_execution,
                        args=(handler, callback_query),
                        daemon=True
                    ).start()
                    break
                    
        except Exception as e:
            logger.error(f"Error processing callback query: {e}")
    
    def _safe_handler_execution(self, handler: callable, update_data: Dict) -> None:
        """Execute handler with error handling"""
        try:
            handler(update_data, self)
        except Exception as e:
            logger.error(f"Error in handler {handler.__name__}: {e}")
    
    def start_background_tasks(self) -> None:
        """Start background processing tasks"""
        # Batch notification processor
        notification_thread = threading.Thread(
            target=self._process_notification_queue,
            daemon=True
        )
        notification_thread.start()
        self.background_tasks.append(notification_thread)
        
        # Batch database writer
        db_writer_thread = threading.Thread(
            target=self._process_database_queue,
            daemon=True
        )
        db_writer_thread.start()
        self.background_tasks.append(db_writer_thread)
    
    def _process_notification_queue(self) -> None:
        """Process pending notifications in batches"""
        while self.running:
            try:
                if self.pending_notifications:
                    # Process up to 10 notifications at once
                    batch = self.pending_notifications[:10]
                    self.pending_notifications = self.pending_notifications[10:]
                    
                    for notification in batch:
                        self.send_message_safe(**notification)
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error processing notification queue: {e}")
                time.sleep(5)
    
    def _process_database_queue(self) -> None:
        """Process pending database writes in batches"""
        while self.running:
            try:
                if self.pending_db_writes:
                    # Process up to 20 DB operations at once
                    batch = self.pending_db_writes[:20]
                    self.pending_db_writes = self.pending_db_writes[20:]
                    
                    # Execute batch
                    operations = [op['operation'] for op in batch]
                    self.db.batch_execute(operations)
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error processing database queue: {e}")
                time.sleep(10)
    
    def queue_notification(self, chat_id: str, text: str, **kwargs) -> None:
        """Queue notification for batch processing"""
        notification = {
            'chat_id': chat_id,
            'text': text,
            **kwargs
        }
        self.pending_notifications.append(notification)
    
    def queue_database_operation(self, operation: callable) -> None:
        """Queue database operation for batch processing"""
        self.pending_db_writes.append({'operation': operation})
    
    def run_polling(self) -> None:
        """Main polling loop optimized for production"""
        logger.info("Starting optimized polling...")
        self.running = True
        
        # Start background tasks
        self.start_background_tasks()
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                # Get updates with optimized settings
                updates = self.get_updates_optimized(timeout=30)
                
                if updates:
                    logger.debug(f"Processing {len(updates)} updates")
                    
                    # Process updates in parallel for better performance
                    threads = []
                    for update in updates:
                        thread = threading.Thread(
                            target=self.process_update,
                            args=(update,),
                            daemon=True
                        )
                        thread.start()
                        threads.append(thread)
                    
                    # Wait for all threads to complete (with timeout)
                    for thread in threads:
                        thread.join(timeout=30)
                
                # Reset error counter on success
                consecutive_errors = 0
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping bot...")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in polling loop: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), pausing...")
                    time.sleep(60)  # Longer pause after many errors
                    consecutive_errors = 0
                else:
                    time.sleep(5)  # Brief pause after single error
        
        self.running = False
        logger.info("Bot stopped")
    
    def stop(self) -> None:
        """Stop the bot gracefully"""
        self.running = False
        
        # Wait for background tasks to finish
        for task in self.background_tasks:
            task.join(timeout=5)

# Webhook support for future scaling
class WebhookHandler:
    """Webhook handler for scaling beyond polling"""
    
    def __init__(self, bot: TelegramBotOptimized):
        self.bot = bot
    
    def set_webhook(self, webhook_url: str, secret_token: str = None) -> bool:
        """Set webhook for receiving updates"""
        try:
            data = {'url': webhook_url}
            if secret_token:
                data['secret_token'] = secret_token
            
            response = requests.post(
                f"{self.bot.api_url}/setWebhook",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook set successfully: {webhook_url}")
                return True
            else:
                logger.error(f"Failed to set webhook: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False
    
    def delete_webhook(self) -> bool:
        """Delete webhook to switch back to polling"""
        try:
            response = requests.post(
                f"{self.bot.api_url}/deleteWebhook",
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Webhook deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete webhook: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False

# Production configuration
class ProductionConfig:
    """Production configuration settings"""
    
    # Database settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require')
    
    # Bot settings
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')
    
    # Performance settings
    POLLING_TIMEOUT = 30
    MAX_CONCURRENT_HANDLERS = 50
    CACHE_TTL_SECONDS = 300
    RATE_LIMIT_MESSAGES = 10
    RATE_LIMIT_WINDOW = 60
    
    # Webhook settings (for future use)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN is required")
            return False
        
        if not cls.DATABASE_URL:
            logger.error("DATABASE_URL is required")
            return False
        
        return True

def create_production_bot() -> TelegramBotOptimized:
    """Factory function to create production-ready bot"""
    if not ProductionConfig.validate():
        raise ValueError("Invalid configuration")
    
    bot = TelegramBotOptimized(
        token=ProductionConfig.BOT_TOKEN,
        database_url=ProductionConfig.DATABASE_URL
    )
    
    return bot

if __name__ == "__main__":
    # Run bot in production mode
    try:
        bot = create_production_bot()
        
        # Add basic handlers for testing
        def start_handler(message: Dict, bot_instance: TelegramBotOptimized):
            chat_id = str(message['chat']['id'])
            bot_instance.send_message_safe(
                chat_id=chat_id,
                text="🚀 Production bot is running efficiently!"
            )
        
        bot.add_command_handler('start', start_handler)
        
        # Start the bot
        bot.run_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)