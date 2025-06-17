"""
Optimized Database Integration Layer
===================================
High-performance database operations that replace slow queries in bot code.
Uses caching, optimized queries, and batch operations for maximum speed.
"""

import logging
from datetime import datetime, date
from query_performance_booster import get_query_booster, fast_user_lookup, fast_dashboard_data, fast_user_transactions, fast_admin_stats
from performance_cache_system import get_bot_cache
from app import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class OptimizedDatabaseService:
    """High-performance database service for bot operations"""
    
    def __init__(self):
        self.query_booster = get_query_booster()
        self.cache = get_bot_cache()
        logger.info("Optimized database service initialized")
    
    def get_user_by_telegram_id(self, telegram_id):
        """Ultra-fast user lookup with caching"""
        # Check cache first
        cached_user = self.cache.get_user(telegram_id)
        if cached_user:
            return cached_user
        
        # Query database with optimized query
        user_data = fast_user_lookup(telegram_id)
        
        if user_data:
            # Convert to dict for easier handling
            user_dict = {
                'id': user_data.id,
                'telegram_id': user_data.telegram_id,
                'username': user_data.username,
                'balance': user_data.balance,
                'initial_deposit': user_data.initial_deposit,
                'status': user_data.status,
                'last_activity': user_data.last_activity
            }
            
            # Cache for future requests
            self.cache.set_user(telegram_id, user_dict)
            return user_dict
        
        return None
    
    def get_user_dashboard_data(self, user_id):
        """Complete dashboard data in single optimized query"""
        # Check cache first
        cached_data = self.cache.get_dashboard_data(user_id)
        if cached_data:
            return cached_data
        
        # Get comprehensive dashboard data
        dashboard_data = fast_dashboard_data(user_id)
        
        if dashboard_data:
            # Convert to structured format
            formatted_data = {
                'user_id': dashboard_data.id,
                'current_balance': dashboard_data.balance,
                'initial_deposit': dashboard_data.initial_deposit,
                'total_profit': dashboard_data.total_profit,
                'total_percentage': dashboard_data.total_profit_percentage,
                'today_profit': dashboard_data.today_profit,
                'today_percentage': dashboard_data.today_profit_percentage,
                'streak_days': dashboard_data.current_streak,
                'best_streak': dashboard_data.best_streak,
                'next_milestone': dashboard_data.next_milestone,
                'milestone_progress': dashboard_data.milestone_progress,
                'current_goal': dashboard_data.current_goal,
                'goal_progress': dashboard_data.goal_progress,
                'trading_mode': dashboard_data.trading_mode
            }
            
            # Cache with short TTL for fresh data
            self.cache.set_dashboard_data(user_id, formatted_data)
            return formatted_data
        
        return None
    
    def get_user_transaction_history(self, user_id, limit=10):
        """Fast transaction history with caching"""
        # Check cache first
        cached_transactions = self.cache.get_user_transactions(user_id, limit)
        if cached_transactions:
            return cached_transactions
        
        # Query optimized transactions
        transactions = fast_user_transactions(user_id, limit)
        
        if transactions:
            # Convert to list of dicts
            transaction_list = []
            for tx in transactions:
                transaction_list.append({
                    'transaction_type': tx.transaction_type,
                    'amount': tx.amount,
                    'timestamp': tx.timestamp,
                    'status': tx.status,
                    'notes': tx.notes,
                    'tx_hash': tx.tx_hash
                })
            
            # Cache the results
            self.cache.set_user_transactions(user_id, transaction_list, limit)
            return transaction_list
        
        return []
    
    def get_admin_statistics(self):
        """Fast admin dashboard statistics"""
        # Check cache first
        cached_stats = self.cache.get_admin_stats()
        if cached_stats:
            return cached_stats
        
        # Get optimized admin stats
        stats = fast_admin_stats()
        
        if stats:
            stats_dict = {
                'active_users': stats.active_users,
                'total_users': stats.total_users,
                'total_balance': float(stats.total_balance),
                'avg_balance': float(stats.avg_balance),
                'last_updated': datetime.now()
            }
            
            # Cache admin stats
            self.cache.set_admin_stats(stats_dict)
            return stats_dict
        
        return {
            'active_users': 0,
            'total_users': 0,
            'total_balance': 0.0,
            'avg_balance': 0.0,
            'last_updated': datetime.now()
        }
    
    def update_user_balance(self, user_id, new_balance, reason="Balance adjustment"):
        """Optimized balance update with cache invalidation"""
        try:
            with self.query_booster.get_connection() as conn:
                # Update balance
                result = conn.execute(text("""
                    UPDATE "user" 
                    SET balance = :balance, last_activity = NOW()
                    WHERE id = :user_id
                    RETURNING telegram_id
                """), {'balance': new_balance, 'user_id': user_id})
                
                telegram_id_result = result.fetchone()
                if telegram_id_result:
                    telegram_id = telegram_id_result.telegram_id
                    
                    # Create transaction record
                    conn.execute(text("""
                        INSERT INTO transaction (user_id, transaction_type, amount, notes, timestamp, status)
                        VALUES (:user_id, 'admin_adjustment', :amount, :reason, NOW(), 'completed')
                    """), {
                        'user_id': user_id,
                        'amount': new_balance,
                        'reason': reason
                    })
                    
                    conn.commit()
                    
                    # Invalidate cache
                    self.cache.invalidate_user_data(telegram_id=telegram_id, user_id=user_id)
                    self.cache.invalidate_admin_data()
                    
                    return True
                
        except Exception as e:
            logger.error(f"Error updating user balance: {e}")
        
        return False
    
    def batch_update_balances(self, user_balance_pairs):
        """High-performance batch balance updates"""
        if not user_balance_pairs:
            return 0
        
        try:
            updated_count = self.query_booster.batch_balance_update(user_balance_pairs)
            
            # Invalidate cache for updated users
            for user_id, _ in user_balance_pairs:
                self.cache.invalidate_user_data(user_id=user_id)
            
            self.cache.invalidate_admin_data()
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in batch balance update: {e}")
            return 0
    
    def create_trading_position(self, user_id, token_name, amount, entry_price, trade_type="live"):
        """Fast trading position creation"""
        try:
            with self.query_booster.get_connection() as conn:
                result = conn.execute(text("""
                    INSERT INTO trading_position 
                    (user_id, token_name, amount, entry_price, current_price, trade_type, timestamp, status)
                    VALUES (:user_id, :token_name, :amount, :entry_price, :current_price, :trade_type, NOW(), 'open')
                    RETURNING id
                """), {
                    'user_id': user_id,
                    'token_name': token_name,
                    'amount': amount,
                    'entry_price': entry_price,
                    'current_price': entry_price,
                    'trade_type': trade_type
                })
                
                position_id = result.fetchone()
                conn.commit()
                
                # Invalidate user's dashboard cache
                self.cache.invalidate_user_data(user_id=user_id)
                
                return position_id.id if position_id else None
                
        except Exception as e:
            logger.error(f"Error creating trading position: {e}")
            return None
    
    def record_daily_profit(self, user_id, profit_amount, profit_percentage):
        """Fast daily profit recording with upsert"""
        try:
            self.query_booster.create_profit_snapshot(user_id, profit_amount, profit_percentage)
            
            # Invalidate dashboard cache
            self.cache.invalidate_user_data(user_id=user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error recording daily profit: {e}")
            return False
    
    def get_active_users_for_broadcast(self):
        """Get active users for message broadcasting"""
        try:
            with self.query_booster.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT id, telegram_id, username 
                    FROM "user" 
                    WHERE status = 'active' 
                    ORDER BY last_activity DESC
                """))
                
                return [{'id': row.id, 'telegram_id': row.telegram_id, 'username': row.username} 
                       for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def search_users(self, search_term):
        """Fast user search with caching"""
        cache_key = f"search:{search_term.lower()}"
        
        try:
            from query_performance_booster import fast_user_search
            users = fast_user_search(search_term)
            
            return [{'id': user.id, 'telegram_id': user.telegram_id, 'username': user.username,
                    'balance': user.balance, 'status': user.status, 'last_activity': user.last_activity}
                   for user in users]
            
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    def get_performance_metrics(self):
        """Get database and cache performance metrics"""
        try:
            db_metrics = self.query_booster.get_performance_report()
            cache_metrics = self.cache.get_cache_statistics()
            
            return {
                'database': db_metrics,
                'cache': cache_metrics,
                'optimization_status': 'active',
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}


# Global service instance
optimized_db_service = None

def get_optimized_db():
    """Get the global optimized database service"""
    global optimized_db_service
    if optimized_db_service is None:
        optimized_db_service = OptimizedDatabaseService()
    return optimized_db_service

# High-level functions for bot integration
def fast_get_user(telegram_id):
    """Fast user lookup for bot handlers"""
    service = get_optimized_db()
    return service.get_user_by_telegram_id(telegram_id)

def fast_get_dashboard(user_id):
    """Fast dashboard data for bot handlers"""
    service = get_optimized_db()
    return service.get_user_dashboard_data(user_id)

def fast_get_transactions(user_id, limit=10):
    """Fast transaction history for bot handlers"""
    service = get_optimized_db()
    return service.get_user_transaction_history(user_id, limit)

def fast_update_balance(user_id, new_balance, reason="Balance adjustment"):
    """Fast balance update for bot handlers"""
    service = get_optimized_db()
    return service.update_user_balance(user_id, new_balance, reason)

def fast_get_admin_stats():
    """Fast admin statistics for bot handlers"""
    service = get_optimized_db()
    return service.get_admin_statistics()

def fast_batch_update_balances(user_balance_pairs):
    """Fast batch balance updates for bot handlers"""
    service = get_optimized_db()
    return service.batch_update_balances(user_balance_pairs)

def fast_create_position(user_id, token_name, amount, entry_price, trade_type="live"):
    """Fast trading position creation for bot handlers"""
    service = get_optimized_db()
    return service.create_trading_position(user_id, token_name, amount, entry_price, trade_type)

def fast_record_profit(user_id, profit_amount, profit_percentage):
    """Fast profit recording for bot handlers"""
    service = get_optimized_db()
    return service.record_daily_profit(user_id, profit_amount, profit_percentage)

def fast_search_users(search_term):
    """Fast user search for bot handlers"""
    service = get_optimized_db()
    return service.search_users(search_term)

def fast_get_active_users():
    """Fast active users list for broadcasting"""
    service = get_optimized_db()
    return service.get_active_users_for_broadcast()