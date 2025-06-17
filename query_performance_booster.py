"""
Query Performance Booster - Direct SQL Optimization
==================================================
Creates essential indexes and optimized query functions for AWS database performance.
"""

import os
import logging
from app import db
from sqlalchemy import text
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class QueryPerformanceBooster:
    """Direct SQL-based performance optimization"""
    
    def __init__(self):
        self.indexes_created = []
        self.query_cache = {}
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        connection = db.engine.connect()
        try:
            yield connection
        finally:
            connection.close()
    
    def create_essential_indexes(self):
        """Create the most critical indexes for bot performance"""
        
        essential_indexes = [
            # User table - most critical
            'CREATE INDEX IF NOT EXISTS idx_user_telegram_id_fast ON "user" (telegram_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_status_active ON "user" (status) WHERE status = \'active\'',
            'CREATE INDEX IF NOT EXISTS idx_user_balance_nonzero ON "user" (balance) WHERE balance > 0',
            
            # Transaction table - extremely critical for performance
            'CREATE INDEX IF NOT EXISTS idx_transaction_user_time ON transaction (user_id, timestamp DESC)',
            'CREATE INDEX IF NOT EXISTS idx_transaction_type_status ON transaction (transaction_type, status)',
            'CREATE INDEX IF NOT EXISTS idx_transaction_hash_unique ON transaction (tx_hash) WHERE tx_hash IS NOT NULL',
            
            # Trading positions - critical for dashboard
            'CREATE INDEX IF NOT EXISTS idx_trading_user_status ON trading_position (user_id, status)',
            'CREATE INDEX IF NOT EXISTS idx_trading_timestamp ON trading_position (timestamp DESC)',
            
            # Profit table - dashboard performance
            'CREATE INDEX IF NOT EXISTS idx_profit_user_date ON profit (user_id, date DESC)',
            'CREATE INDEX IF NOT EXISTS idx_profit_date_recent ON profit (date) WHERE date >= CURRENT_DATE - INTERVAL \'30 days\'',
            
            # User metrics - real-time dashboard
            'CREATE INDEX IF NOT EXISTS idx_user_metrics_user ON user_metrics (user_id)',
            
            # Daily snapshots - performance tracking
            'CREATE INDEX IF NOT EXISTS idx_daily_snapshot_user_date ON daily_snapshot (user_id, date DESC)',
        ]
        
        created = 0
        with self.get_connection() as conn:
            for index_sql in essential_indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    created += 1
                    index_name = index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'
                    logger.info(f"Created index: idx_{index_name}")
                    self.indexes_created.append(index_name)
                except Exception as e:
                    logger.warning(f"Index creation skipped (may exist): {str(e)[:100]}")
        
        logger.info(f"Essential indexes setup complete. Created {created} indexes.")
        return created
    
    def optimize_user_lookup(self, telegram_id):
        """Ultra-fast user lookup by telegram_id"""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT id, telegram_id, username, balance, initial_deposit, status, last_activity
                FROM "user" 
                WHERE telegram_id = :telegram_id
                LIMIT 1
            """), {'telegram_id': str(telegram_id)})
            return result.fetchone()
    
    def optimize_user_dashboard_data(self, user_id):
        """Single query for complete dashboard data"""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT 
                    -- User basics
                    u.id, u.balance, u.initial_deposit, u.status,
                    -- Calculated totals
                    (u.balance - u.initial_deposit) as total_profit,
                    CASE 
                        WHEN u.initial_deposit > 0 THEN ((u.balance - u.initial_deposit) / u.initial_deposit * 100)
                        ELSE 0 
                    END as total_profit_percentage,
                    -- Today's data
                    COALESCE(ds.profit_amount, 0) as today_profit,
                    COALESCE(ds.profit_percentage, 0) as today_profit_percentage,
                    -- Metrics
                    COALESCE(um.current_streak, 0) as current_streak,
                    COALESCE(um.best_streak, 0) as best_streak,
                    COALESCE(um.next_milestone, 10.0) as next_milestone,
                    COALESCE(um.milestone_progress, 0) as milestone_progress,
                    COALESCE(um.current_goal, 100.0) as current_goal,
                    COALESCE(um.goal_progress, 0) as goal_progress,
                    COALESCE(um.trading_mode, 'autopilot') as trading_mode
                FROM "user" u
                LEFT JOIN user_metrics um ON u.id = um.user_id
                LEFT JOIN daily_snapshot ds ON u.id = ds.user_id AND ds.date = CURRENT_DATE
                WHERE u.id = :user_id
            """), {'user_id': user_id})
            return result.fetchone()
    
    def optimize_recent_transactions(self, user_id, limit=10):
        """Fast recent transactions lookup"""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT transaction_type, amount, timestamp, status, notes, tx_hash
                FROM transaction 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT :limit
            """), {'user_id': user_id, 'limit': limit})
            return result.fetchall()
    
    def optimize_active_users_count(self):
        """Fast active users count for admin dashboard"""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'active') as active_users,
                    COUNT(*) as total_users,
                    COALESCE(SUM(balance), 0) as total_balance,
                    COALESCE(AVG(balance), 0) as avg_balance
                FROM "user"
            """))
            return result.fetchone()
    
    def optimize_user_search(self, search_term):
        """Fast user search by username or telegram_id"""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT id, telegram_id, username, balance, status, last_activity
                FROM "user" 
                WHERE 
                    username ILIKE :search_term OR 
                    telegram_id = :exact_term
                ORDER BY 
                    CASE WHEN telegram_id = :exact_term THEN 1 ELSE 2 END,
                    last_activity DESC
                LIMIT 20
            """), {
                'search_term': f'%{search_term}%',
                'exact_term': search_term
            })
            return result.fetchall()
    
    def batch_balance_update(self, user_balance_pairs):
        """Optimized batch balance updates"""
        if not user_balance_pairs:
            return 0
        
        with self.get_connection() as conn:
            # Build batch update using VALUES clause
            values_list = []
            for user_id, balance in user_balance_pairs:
                values_list.append(f"({user_id}, {balance})")
            
            values_clause = ', '.join(values_list)
            
            result = conn.execute(text(f"""
                UPDATE "user" 
                SET balance = v.balance, last_activity = NOW()
                FROM (VALUES {values_clause}) AS v(user_id, balance)
                WHERE "user".id = v.user_id
            """))
            conn.commit()
            return result.rowcount
    
    def create_profit_snapshot(self, user_id, profit_amount, profit_percentage):
        """Fast profit recording"""
        with self.get_connection() as conn:
            conn.execute(text("""
                INSERT INTO profit (user_id, amount, percentage, date)
                VALUES (:user_id, :amount, :percentage, CURRENT_DATE)
                ON CONFLICT (user_id, date) DO UPDATE SET
                    amount = EXCLUDED.amount,
                    percentage = EXCLUDED.percentage
            """), {
                'user_id': user_id,
                'amount': profit_amount,
                'percentage': profit_percentage
            })
            conn.commit()
    
    def update_table_statistics(self):
        """Update PostgreSQL statistics for better query planning"""
        tables = ['user', 'transaction', 'trading_position', 'profit', 'user_metrics', 'daily_snapshot']
        
        with self.get_connection() as conn:
            for table in tables:
                try:
                    conn.execute(text(f"ANALYZE {table}"))
                    logger.info(f"Updated statistics for {table}")
                except Exception as e:
                    logger.warning(f"Could not analyze {table}: {e}")
            conn.commit()
        
        logger.info("Database statistics updated for optimal query planning")
    
    def get_performance_report(self):
        """Get database performance metrics"""
        with self.get_connection() as conn:
            # Check index usage
            result = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes 
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                LIMIT 10
            """))
            
            index_stats = result.fetchall()
            
            # Check table sizes
            result = conn.execute(text("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """))
            
            table_sizes = result.fetchall()
            
            return {
                'indexes_created': len(self.indexes_created),
                'top_indexes': [dict(row) for row in index_stats],
                'table_sizes': [dict(row) for row in table_sizes],
                'optimization_status': 'active'
            }


# Global instance
query_booster = None

def get_query_booster():
    """Get the global query booster instance"""
    global query_booster
    if query_booster is None:
        query_booster = QueryPerformanceBooster()
        query_booster.create_essential_indexes()
        query_booster.update_table_statistics()
    return query_booster

# Optimized functions for direct use in bot code
def fast_user_lookup(telegram_id):
    """Get user data optimized for speed"""
    booster = get_query_booster()
    return booster.optimize_user_lookup(telegram_id)

def fast_dashboard_data(user_id):
    """Get complete dashboard data in one query"""
    booster = get_query_booster()
    return booster.optimize_user_dashboard_data(user_id)

def fast_user_transactions(user_id, limit=10):
    """Get recent transactions optimized"""
    booster = get_query_booster()
    return booster.optimize_recent_transactions(user_id, limit)

def fast_admin_stats():
    """Get admin dashboard stats quickly"""
    booster = get_query_booster()
    return booster.optimize_active_users_count()

def fast_user_search(search_term):
    """Search users quickly"""
    booster = get_query_booster()
    return booster.optimize_user_search(search_term)