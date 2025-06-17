"""
Performance Cache System for Bot Operations
==========================================
In-memory caching for frequently accessed data to reduce database load.
"""

import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import logging

logger = logging.getLogger(__name__)

class PerformanceCache:
    """Thread-safe in-memory cache with TTL and LRU eviction"""
    
    def __init__(self, max_size=1000, default_ttl=300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.access_times = {}
        self.lock = threading.RLock()
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0
        }
    
    def _is_expired(self, key):
        """Check if cache entry is expired"""
        if key not in self.access_times:
            return True
        
        created_at, ttl = self.access_times[key]
        return time.time() - created_at > ttl
    
    def _evict_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, (created_at, ttl) in self.access_times.items():
            if current_time - created_at > ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            self.stats['evictions'] += 1
    
    def _evict_lru(self):
        """Remove least recently used entries if cache is full"""
        while len(self.cache) >= self.max_size:
            lru_key = next(iter(self.cache))
            del self.cache[lru_key]
            if lru_key in self.access_times:
                del self.access_times[lru_key]
            self.stats['evictions'] += 1
    
    def get(self, key):
        """Get value from cache"""
        with self.lock:
            self._evict_expired()
            
            if key in self.cache and not self._is_expired(key):
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.stats['hits'] += 1
                return value
            
            self.stats['misses'] += 1
            return None
    
    def set(self, key, value, ttl=None):
        """Set value in cache"""
        with self.lock:
            self._evict_expired()
            self._evict_lru()
            
            ttl = ttl or self.default_ttl
            self.cache[key] = value
            self.access_times[key] = (time.time(), ttl)
            self.stats['sets'] += 1
    
    def delete(self, key):
        """Remove key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': round(hit_rate, 2),
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions'],
                'sets': self.stats['sets']
            }


class BotDataCache:
    """Specialized cache for bot operations"""
    
    def __init__(self):
        # Different TTLs for different data types
        self.user_cache = PerformanceCache(max_size=500, default_ttl=300)      # 5 min
        self.dashboard_cache = PerformanceCache(max_size=200, default_ttl=60)   # 1 min
        self.stats_cache = PerformanceCache(max_size=50, default_ttl=120)       # 2 min
        self.transaction_cache = PerformanceCache(max_size=1000, default_ttl=180) # 3 min
        
        # Batch operation tracking
        self.pending_updates = defaultdict(list)
        self.batch_lock = threading.Lock()
        
        logger.info("Bot data cache system initialized")
    
    def get_user(self, telegram_id):
        """Get cached user data"""
        key = f"user:{telegram_id}"
        return self.user_cache.get(key)
    
    def set_user(self, telegram_id, user_data):
        """Cache user data"""
        key = f"user:{telegram_id}"
        self.user_cache.set(key, user_data)
    
    def get_dashboard_data(self, user_id):
        """Get cached dashboard data"""
        key = f"dashboard:{user_id}"
        return self.dashboard_cache.get(key)
    
    def set_dashboard_data(self, user_id, dashboard_data):
        """Cache dashboard data with short TTL"""
        key = f"dashboard:{user_id}"
        self.dashboard_cache.set(key, dashboard_data, ttl=60)  # 1 minute for fresh data
    
    def get_user_transactions(self, user_id, limit=10):
        """Get cached transaction history"""
        key = f"transactions:{user_id}:{limit}"
        return self.transaction_cache.get(key)
    
    def set_user_transactions(self, user_id, transactions, limit=10):
        """Cache transaction history"""
        key = f"transactions:{user_id}:{limit}"
        self.transaction_cache.set(key, transactions)
    
    def get_admin_stats(self):
        """Get cached admin statistics"""
        return self.stats_cache.get("admin_stats")
    
    def set_admin_stats(self, stats_data):
        """Cache admin statistics"""
        self.stats_cache.set("admin_stats", stats_data)
    
    def invalidate_user_data(self, telegram_id=None, user_id=None):
        """Invalidate cached user data when updated"""
        if telegram_id:
            self.user_cache.delete(f"user:{telegram_id}")
        if user_id:
            self.dashboard_cache.delete(f"dashboard:{user_id}")
            # Clear transaction cache for this user
            keys_to_delete = [key for key in self.transaction_cache.cache.keys() 
                            if key.startswith(f"transactions:{user_id}:")]
            for key in keys_to_delete:
                self.transaction_cache.delete(key)
    
    def invalidate_admin_data(self):
        """Invalidate admin statistics"""
        self.stats_cache.delete("admin_stats")
    
    def add_pending_balance_update(self, user_id, new_balance):
        """Add balance update to pending batch"""
        with self.batch_lock:
            self.pending_updates['balances'].append((user_id, new_balance))
    
    def get_pending_balance_updates(self):
        """Get and clear pending balance updates"""
        with self.batch_lock:
            updates = list(self.pending_updates['balances'])
            self.pending_updates['balances'].clear()
            return updates
    
    def get_cache_statistics(self):
        """Get comprehensive cache statistics"""
        return {
            'user_cache': self.user_cache.get_stats(),
            'dashboard_cache': self.dashboard_cache.get_stats(),
            'stats_cache': self.stats_cache.get_stats(),
            'transaction_cache': self.transaction_cache.get_stats(),
            'pending_updates': {
                'balances': len(self.pending_updates['balances'])
            }
        }


# Global cache instance
bot_cache = BotDataCache()

def get_bot_cache():
    """Get the global bot cache instance"""
    return bot_cache