"""
Graceful Duplicate Response Handler
This module provides comprehensive protection against duplicate responses and HTTP 409 errors
"""
import logging
import time
import json
import hashlib
from threading import Lock
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DuplicateProtectionManager:
    """Manages duplicate protection across the entire bot system"""
    
    def __init__(self):
        self.processed_updates = set()
        self.processed_callbacks = set()
        self.processed_messages = set()
        self.request_timestamps = {}
        self.lock = Lock()
        self.last_cleanup = time.time()
        
    def is_duplicate_update(self, update_id):
        """Check if an update has already been processed"""
        with self.lock:
            if update_id in self.processed_updates:
                return True
            self.processed_updates.add(update_id)
            self._cleanup_if_needed()
            return False
    
    def is_duplicate_callback(self, callback_id):
        """Check if a callback has already been processed"""
        with self.lock:
            if callback_id in self.processed_callbacks:
                return True
            self.processed_callbacks.add(callback_id)
            self._cleanup_if_needed()
            return False
    
    def is_duplicate_message(self, message_data):
        """Check if a message has already been processed using content hash"""
        message_hash = self._generate_message_hash(message_data)
        with self.lock:
            if message_hash in self.processed_messages:
                return True
            self.processed_messages.add(message_hash)
            self._cleanup_if_needed()
            return False
    
    def is_rate_limited(self, user_id, action_type="message", cooldown_seconds=1.0):
        """Check if a user is rate limited for a specific action"""
        key = f"{user_id}_{action_type}"
        current_time = time.time()
        
        with self.lock:
            if key in self.request_timestamps:
                last_request = self.request_timestamps[key]
                if current_time - last_request < cooldown_seconds:
                    return True
            
            self.request_timestamps[key] = current_time
            return False
    
    def _generate_message_hash(self, message_data):
        """Generate a unique hash for message content"""
        # Create a hash based on user_id, chat_id, text, and timestamp (rounded to seconds)
        content = {
            'user_id': message_data.get('from', {}).get('id'),
            'chat_id': message_data.get('chat', {}).get('id'),
            'text': message_data.get('text', ''),
            'timestamp': int(message_data.get('date', time.time()))
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def _cleanup_if_needed(self):
        """Clean up old entries to prevent memory leaks"""
        current_time = time.time()
        if current_time - self.last_cleanup > 300:  # Clean up every 5 minutes
            # Keep only the last 1000 entries for each set
            if len(self.processed_updates) > 1000:
                self.processed_updates = set(list(self.processed_updates)[-500:])
            if len(self.processed_callbacks) > 1000:
                self.processed_callbacks = set(list(self.processed_callbacks)[-500:])
            if len(self.processed_messages) > 1000:
                self.processed_messages = set(list(self.processed_messages)[-500:])
            
            # Clean up old timestamps (older than 1 hour)
            cutoff_time = current_time - 3600
            self.request_timestamps = {
                k: v for k, v in self.request_timestamps.items() 
                if v > cutoff_time
            }
            
            self.last_cleanup = current_time
            logger.debug("Cleaned up duplicate protection caches")

# Global instance
duplicate_manager = DuplicateProtectionManager()

def handle_telegram_api_error(response, operation_name="API call"):
    """Handle Telegram API errors gracefully"""
    if response.status_code == 409:
        logger.warning(f"HTTP 409 (Conflict) during {operation_name} - likely duplicate request, ignoring")
        return {"ok": True, "result": {"message": "Duplicate request handled gracefully"}}
    elif response.status_code == 429:
        logger.warning(f"HTTP 429 (Rate Limited) during {operation_name} - backing off")
        time.sleep(1)
        return {"ok": False, "error": "Rate limited"}
    elif response.status_code != 200:
        logger.error(f"HTTP {response.status_code} during {operation_name}: {response.text}")
        return {"ok": False, "error": f"HTTP {response.status_code}"}
    
    return response.json()

def safe_telegram_request(func, *args, max_retries=3, **kwargs):
    """Safely execute a Telegram API request with retry logic"""
    for attempt in range(max_retries):
        try:
            response = func(*args, **kwargs)
            
            # Handle specific HTTP error codes
            if hasattr(response, 'status_code'):
                if response.status_code == 409:
                    logger.debug(f"HTTP 409 on attempt {attempt + 1}, treating as success")
                    return {"ok": True, "handled_duplicate": True}
                elif response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                elif response.status_code != 200:
                    logger.error(f"HTTP {response.status_code} on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return {"ok": False, "error": f"HTTP {response.status_code}"}
                    time.sleep(1)
                    continue
                
                return response.json()
            
            return response
            
        except Exception as e:
            logger.error(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return {"ok": False, "error": str(e)}
            time.sleep(1)
    
    return {"ok": False, "error": "Max retries exceeded"}

def create_safe_bot_methods():
    """Create safe wrapper methods for bot operations"""
    
    def safe_send_message(bot, chat_id, text, **kwargs):
        """Safely send a message with duplicate protection"""
        # Check rate limiting
        if duplicate_manager.is_rate_limited(chat_id, "send_message", 0.5):
            logger.debug(f"Rate limited message to {chat_id}")
            return {"ok": True, "rate_limited": True}
        
        # Create message signature for duplicate detection
        message_data = {
            'chat_id': chat_id,
            'text': text,
            'timestamp': int(time.time())
        }
        
        if duplicate_manager.is_duplicate_message(message_data):
            logger.debug(f"Duplicate message detected for chat {chat_id}")
            return {"ok": True, "duplicate_handled": True}
        
        # Send the message
        return safe_telegram_request(bot.send_message, chat_id, text, **kwargs)
    
    def safe_edit_message(bot, message_id, chat_id, text, **kwargs):
        """Safely edit a message with duplicate protection"""
        if duplicate_manager.is_rate_limited(f"{chat_id}_{message_id}", "edit_message", 0.5):
            logger.debug(f"Rate limited edit for message {message_id} in chat {chat_id}")
            return {"ok": True, "rate_limited": True}
        
        return safe_telegram_request(bot.edit_message, message_id, chat_id, text, **kwargs)
    
    def safe_process_update(bot, update):
        """Safely process an update with comprehensive duplicate protection"""
        update_id = update.get('update_id')
        
        # Check for duplicate update
        if duplicate_manager.is_duplicate_update(update_id):
            logger.debug(f"Skipping duplicate update {update_id}")
            return True
        
        # Handle callback queries
        if 'callback_query' in update:
            callback_id = update['callback_query']['id']
            if duplicate_manager.is_duplicate_callback(callback_id):
                logger.debug(f"Skipping duplicate callback {callback_id}")
                return True
        
        # Handle messages
        if 'message' in update:
            message = update['message']
            user_id = message.get('from', {}).get('id')
            
            if user_id and duplicate_manager.is_rate_limited(user_id, "process_message", 1.0):
                logger.debug(f"Rate limited processing for user {user_id}")
                return True
            
            if duplicate_manager.is_duplicate_message(message):
                logger.debug(f"Skipping duplicate message from user {user_id}")
                return True
        
        return False  # Not a duplicate, should be processed
    
    return {
        'safe_send_message': safe_send_message,
        'safe_edit_message': safe_edit_message,
        'safe_process_update': safe_process_update
    }

# Create the safe methods
safe_methods = create_safe_bot_methods()