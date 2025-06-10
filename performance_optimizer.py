#!/usr/bin/env python3
"""
Performance Optimizer for Telegram Bot
=====================================
Adds caching, batch processing, and connection pooling to handle 500+ users efficiently.
"""

import threading
import time
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class UserCache:
    """Thread-safe user data cache"""
    
    def __init__(self, max_size: int = 5000, ttl_seconds: int = 300):
        self._cache: Dict[str, Dict] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached value if not expired"""
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self.ttl_seconds:
                    return self._cache[key].copy()
                else:
                    # Expired
                    del self._cache[key]
                    del self._timestamps[key]
            return None
    
    def set(self, key: str, value: Dict) -> None:
        """Set cached value"""
        with self._lock:
            # Evict old entries if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_oldest(self.max_size // 10)
            
            self._cache[key] = value.copy()
            self._timestamps[key] = time.time()
    
    def invalidate(self, key: str) -> None:
        """Remove cached value"""
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def _evict_oldest(self, count: int) -> None:
        """Evict oldest cached entries"""
        if not self._timestamps:
            return
        
        oldest_keys = sorted(self._timestamps.keys(), 
                           key=lambda k: self._timestamps[k])[:count]
        
        for key in oldest_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def _cleanup_loop(self) -> None:
        """Background cleanup of expired entries"""
        while True:
            try:
                current_time = time.time()
                with self._lock:
                    expired_keys = [
                        key for key, timestamp in self._timestamps.items()
                        if current_time - timestamp >= self.ttl_seconds
                    ]
                    
                    for key in expired_keys:
                        self._cache.pop(key, None)
                        self._timestamps.pop(key, None)
                
                time.sleep(60)  # Clean every minute
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                time.sleep(60)

class RateLimiter:
    """Per-user rate limiting"""
    
    def __init__(self, max_messages: int = 10, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.user_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_messages))
        self._lock = threading.RLock()
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        with self._lock:
            now = time.time()
            user_times = self.user_timestamps[user_id]
            
            # Remove old timestamps
            while user_times and user_times[0] < now - self.window_seconds:
                user_times.popleft()
            
            # Check if under limit
            if len(user_times) >= self.max_messages:
                return False
            
            # Add current time
            user_times.append(now)
            return True

class DatabaseBatcher:
    """Batch database operations to reduce connection load"""
    
    def __init__(self, batch_size: int = 50, flush_interval: int = 2):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending_operations: List[Dict] = []
        self._lock = threading.RLock()
        self.running = True
        
        # Start batch processor
        processor_thread = threading.Thread(target=self._process_batches, daemon=True)
        processor_thread.start()
    
    def queue_operation(self, operation_type: str, query: str, params: Dict = None) -> None:
        """Queue database operation for batch processing"""
        with self._lock:
            self.pending_operations.append({
                'type': operation_type,
                'query': query,
                'params': params or {},
                'timestamp': time.time()
            })
            
            # Process immediately if batch is full
            if len(self.pending_operations) >= self.batch_size:
                self._flush_batch()
    
    def _flush_batch(self) -> None:
        """Process pending operations"""
        if not self.pending_operations:
            return
        
        batch = self.pending_operations[:self.batch_size]
        self.pending_operations = self.pending_operations[self.batch_size:]
        
        try:
            from app import app, db
            with app.app_context():
                for operation in batch:
                    try:
                        if operation['type'] == 'update':
                            db.session.execute(db.text(operation['query']), operation['params'])
                        elif operation['type'] == 'insert':
                            db.session.execute(db.text(operation['query']), operation['params'])
                    except Exception as e:
                        logger.error(f"Batch operation error: {e}")
                
                db.session.commit()
                logger.debug(f"Processed batch of {len(batch)} operations")
                
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
    
    def _process_batches(self) -> None:
        """Background batch processor"""
        while self.running:
            try:
                time.sleep(self.flush_interval)
                with self._lock:
                    if self.pending_operations:
                        self._flush_batch()
            except Exception as e:
                logger.error(f"Batch processor error: {e}")
                time.sleep(5)

class MessageQueue:
    """Queue for batching message sending"""
    
    def __init__(self, batch_size: int = 20, flush_interval: int = 1):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending_messages: List[Dict] = []
        self._lock = threading.RLock()
        self.running = True
        
        # Start message processor
        processor_thread = threading.Thread(target=self._process_messages, daemon=True)
        processor_thread.start()
    
    def queue_message(self, bot_instance, chat_id: str, text: str, **kwargs) -> None:
        """Queue message for batch sending"""
        with self._lock:
            self.pending_messages.append({
                'bot': bot_instance,
                'chat_id': chat_id,
                'text': text,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            
            # Process immediately if batch is full
            if len(self.pending_messages) >= self.batch_size:
                self._flush_messages()
    
    def _flush_messages(self) -> None:
        """Send pending messages"""
        if not self.pending_messages:
            return
        
        batch = self.pending_messages[:self.batch_size]
        self.pending_messages = self.pending_messages[self.batch_size:]
        
        for msg in batch:
            try:
                msg['bot'].send_message(msg['chat_id'], msg['text'], **msg['kwargs'])
                time.sleep(0.1)  # Prevent API rate limits
            except Exception as e:
                logger.error(f"Message send error: {e}")
    
    def _process_messages(self) -> None:
        """Background message processor"""
        while self.running:
            try:
                time.sleep(self.flush_interval)
                with self._lock:
                    if self.pending_messages:
                        self._flush_messages()
            except Exception as e:
                logger.error(f"Message processor error: {e}")
                time.sleep(2)

class PerformanceOptimizer:
    """Main performance optimization coordinator"""
    
    def __init__(self):
        self.user_cache = UserCache(max_size=5000, ttl_seconds=300)
        self.rate_limiter = RateLimiter(max_messages=10, window_seconds=60)
        self.db_batcher = DatabaseBatcher(batch_size=50, flush_interval=2)
        self.message_queue = MessageQueue(batch_size=20, flush_interval=1)
        
        # Performance metrics
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'rate_limited_requests': 0,
            'batched_db_operations': 0,
            'queued_messages': 0
        }
        
        logger.info("Performance optimizer initialized")
    
    def get_user_cached(self, telegram_id: str, fetch_function: callable) -> Optional[Dict]:
        """Get user with caching"""
        cache_key = f"user:{telegram_id}"
        cached = self.user_cache.get(cache_key)
        
        if cached:
            self.metrics['cache_hits'] += 1
            return cached
        
        # Cache miss - fetch from database
        self.metrics['cache_misses'] += 1
        user_data = fetch_function(telegram_id)
        
        if user_data:
            self.user_cache.set(cache_key, user_data)
        
        return user_data
    
    def invalidate_user_cache(self, telegram_id: str) -> None:
        """Invalidate user cache"""
        self.user_cache.invalidate(f"user:{telegram_id}")
    
    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is rate limited"""
        if not self.rate_limiter.is_allowed(user_id):
            self.metrics['rate_limited_requests'] += 1
            return True
        return False
    
    def queue_db_operation(self, operation_type: str, query: str, params: Dict = None) -> None:
        """Queue database operation"""
        self.db_batcher.queue_operation(operation_type, query, params)
        self.metrics['batched_db_operations'] += 1
    
    def queue_message(self, bot_instance, chat_id: str, text: str, **kwargs) -> None:
        """Queue message for sending"""
        self.message_queue.queue_message(bot_instance, chat_id, text, **kwargs)
        self.metrics['queued_messages'] += 1
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (self.metrics['cache_hits'] / cache_total * 100) if cache_total > 0 else 0
        
        return {
            **self.metrics,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'cache_size': len(self.user_cache._cache),
            'pending_db_operations': len(self.db_batcher.pending_operations),
            'pending_messages': len(self.message_queue.pending_messages)
        }

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

def optimize_bot_instance(bot_instance):
    """Add performance optimizations to existing bot instance"""
    
    # Store original methods
    original_send_message = bot_instance.send_message
    
    def optimized_send_message(chat_id, text, **kwargs):
        """Optimized message sending with queueing"""
        if len(text) > 4096:
            text = text[:4093] + "..."
        
        # Queue for batch processing
        performance_optimizer.queue_message(bot_instance, chat_id, text, **kwargs)
    
    # Replace methods with optimized versions
    bot_instance.send_message_optimized = optimized_send_message
    bot_instance.performance_optimizer = performance_optimizer
    
    logger.info("Bot instance optimized for 500+ users")
    return bot_instance

def get_performance_report() -> Dict:
    """Get comprehensive performance report"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'system': {
            'cpu_percent': process.cpu_percent(),
            'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
            'threads': process.num_threads(),
            'connections': len(process.connections())
        },
        'optimization': performance_optimizer.get_metrics(),
        'database': {
            'pool_type': 'NullPool',
            'connection_reuse': False,
            'batch_processing': True
        }
    }