#!/usr/bin/env python3
"""
Duplicate Response Fix - Strengthens the duplicate protection system
"""

import logging
import time
import hashlib
from threading import Lock
from collections import defaultdict

logger = logging.getLogger(__name__)

class EnhancedDuplicateManager:
    """Enhanced duplicate protection with stronger message tracking"""
    
    def __init__(self):
        self.processed_updates = set()
        self.processed_callbacks = set()
        self.message_hashes = set()
        self.user_last_message = {}  # Track last message per user
        self.user_rate_limits = defaultdict(float)
        self.lock = Lock()
        
    def is_duplicate_update(self, update_id):
        """Check if update was already processed"""
        with self.lock:
            if update_id in self.processed_updates:
                logger.debug(f"Duplicate update blocked: {update_id}")
                return True
            
            self.processed_updates.add(update_id)
            
            # Keep only recent 2000 updates
            if len(self.processed_updates) > 2000:
                sorted_updates = sorted(self.processed_updates)
                self.processed_updates = set(sorted_updates[-1000:])
            
            return False
    
    def is_duplicate_message(self, message):
        """Enhanced message duplicate detection"""
        with self.lock:
            user_id = message.get('from', {}).get('id')
            text = message.get('text', '')
            timestamp = message.get('date', time.time())
            
            # Create message signature
            signature = f"{user_id}:{text}:{int(timestamp)}"
            message_hash = hashlib.md5(signature.encode()).hexdigest()
            
            # Check for exact duplicate
            if message_hash in self.message_hashes:
                logger.debug(f"Duplicate message blocked for user {user_id}")
                return True
            
            # Check for rapid successive messages
            last_message_key = f"{user_id}:last_message"
            if last_message_key in self.user_last_message:
                last_text, last_time = self.user_last_message[last_message_key]
                if text == last_text and (timestamp - last_time) < 2:
                    logger.debug(f"Rapid duplicate message blocked for user {user_id}")
                    return True
            
            # Store message info
            self.message_hashes.add(message_hash)
            self.user_last_message[last_message_key] = (text, timestamp)
            
            # Cleanup old hashes
            if len(self.message_hashes) > 1000:
                # Remove random half to prevent memory growth
                hash_list = list(self.message_hashes)
                self.message_hashes = set(hash_list[-500:])
            
            return False
    
    def is_rate_limited(self, user_id, action_type="message", cooldown=2.0):
        """Rate limiting with stronger cooldowns"""
        with self.lock:
            key = f"{user_id}:{action_type}"
            current_time = time.time()
            
            if key in self.user_rate_limits:
                last_action = self.user_rate_limits[key]
                if current_time - last_action < cooldown:
                    logger.debug(f"Rate limit applied to user {user_id} for {action_type}")
                    return True
            
            self.user_rate_limits[key] = current_time
            return False

# Create enhanced global instance
enhanced_duplicate_manager = EnhancedDuplicateManager()

def apply_duplicate_fix():
    """Apply the enhanced duplicate protection to bot runner"""
    try:
        # Import and replace the duplicate manager
        import bot_v20_runner
        bot_v20_runner.duplicate_manager = enhanced_duplicate_manager
        logger.info("Enhanced duplicate protection applied")
        return True
    except Exception as e:
        logger.error(f"Failed to apply duplicate fix: {e}")
        return False

if __name__ == "__main__":
    apply_duplicate_fix()
    print("Enhanced duplicate protection system ready")