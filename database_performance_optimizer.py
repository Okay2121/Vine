"""
Database Performance Optimizer for AWS Migration
===============================================
Optimizes query performance to match Neon speed after AWS migration.
Includes connection pooling, indexing, query optimization, and monitoring.
"""

import os
import time
import logging
import asyncio
from datetime import datetime, timedelta
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event, Index
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class DatabasePerformanceOptimizer:
    """Comprehensive database performance optimization"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        self.engine = None
        self.session_factory = None
        self.scoped_session = None
        
        # Performance monitoring
        self.query_stats = defaultdict(list)
        self.slow_queries = deque(maxlen=100)
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'avg_query_time': 0
        }
        
        self._setup_optimized_engine()
        self._setup_query_monitoring()
    
    def _setup_optimized_engine(self):
        """Setup optimized database engine with proper connection pooling"""
        if not self.database_url:
            raise ValueError("Database URL not provided")
        
        # Production-optimized engine configuration
        engine_options = {
            'poolclass': QueuePool,
            'pool_size': 10,           # Base connection pool size
            'max_overflow': 20,        # Additional connections if needed
            'pool_pre_ping': True,     # Verify connections before use
            'pool_recycle': 3600,      # Recycle connections every hour
            'pool_timeout': 30,        # Wait 30s for connection from pool
            'echo': False,             # Disable SQL logging in production
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 10,
                'application_name': 'telegram_bot_optimized',
                # TCP keepalive settings for AWS
                'keepalives_idle': 600,
                'keepalives_interval': 60,
                'keepalives_count': 3,
                # Connection optimization
                'target_session_attrs': 'read-write'
            }
        }
        
        self.engine = create_engine(self.database_url, **engine_options)
        self.session_factory = sessionmaker(bind=self.engine)
        self.scoped_session = scoped_session(self.session_factory)
        
        logger.info("Optimized database engine configured with connection pooling")
    
    def _setup_query_monitoring(self):
        """Setup query performance monitoring"""
        
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            
            # Track query statistics
            query_type = statement.strip().split()[0].upper()
            self.query_stats[query_type].append(total_time)
            
            # Track slow queries (>100ms)
            if total_time > 0.1:
                self.slow_queries.append({
                    'query': statement[:200] + '...' if len(statement) > 200 else statement,
                    'duration': total_time,
                    'timestamp': datetime.now()
                })
                logger.warning(f"Slow query detected: {total_time:.3f}s - {statement[:100]}...")
        
        logger.info("Query performance monitoring enabled")
    
    @contextmanager
    def get_db_session(self):
        """Get optimized database session with automatic cleanup"""
        session = self.scoped_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_performance_indexes(self):
        """Create indexes for frequently queried columns"""
        indexes_to_create = [
            # User table optimizations
            Index('idx_user_telegram_id_status', 'user.telegram_id', 'user.status'),
            Index('idx_user_status_active', 'user.status'),
            Index('idx_user_last_activity', 'user.last_activity'),
            
            # Transaction table optimizations (most critical)
            Index('idx_transaction_user_timestamp', 'transaction.user_id', 'transaction.timestamp'),
            Index('idx_transaction_type_status', 'transaction.transaction_type', 'transaction.status'),
            Index('idx_transaction_processed_at', 'transaction.processed_at'),
            
            # Trading position optimizations
            Index('idx_trading_position_user_status', 'trading_position.user_id', 'trading_position.status'),
            Index('idx_trading_position_timestamp', 'trading_position.timestamp'),
            Index('idx_trading_position_token', 'trading_position.token_name'),
            
            # Profit table optimizations
            Index('idx_profit_user_date', 'profit.user_id', 'profit.date'),
            Index('idx_profit_date', 'profit.date'),
            
            # Daily snapshot optimizations
            Index('idx_daily_snapshot_user_date', 'daily_snapshot.user_id', 'daily_snapshot.date'),
            
            # User metrics optimizations
            Index('idx_user_metrics_user_updated', 'user_metrics.user_id', 'user_metrics.last_updated'),
            
            # Trading cycle optimizations
            Index('idx_trading_cycle_user_status', 'trading_cycle.user_id', 'trading_cycle.status'),
        ]
        
        created_count = 0
        with self.get_db_session() as session:
            for index in indexes_to_create:
                try:
                    # Check if index already exists
                    result = session.execute(text(f"""
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = '{index.name}'
                    """))
                    
                    if not result.fetchone():
                        # Create index without CONCURRENTLY for compatibility
                        column_names = ', '.join([str(col) for col in index.columns])
                        session.execute(text(f"CREATE INDEX IF NOT EXISTS {index.name} ON {index.table.name} ({column_names})"))
                        created_count += 1
                        logger.info(f"Created index: {index.name}")
                    
                except Exception as e:
                    logger.warning(f"Could not create index {index.name}: {e}")
        
        logger.info(f"Database indexing complete. Created {created_count} new indexes.")
        return created_count
    
    def get_optimized_user_query(self, telegram_id):
        """Optimized user lookup by telegram_id"""
        with self.get_db_session() as session:
            # Use the indexed telegram_id column
            result = session.execute(text("""
                SELECT id, telegram_id, username, balance, initial_deposit, status, last_activity
                FROM "user" 
                WHERE telegram_id = :telegram_id
            """), {'telegram_id': str(telegram_id)})
            return result.fetchone()
    
    def get_optimized_user_transactions(self, user_id, limit=10):
        """Optimized transaction history lookup"""
        with self.get_db_session() as session:
            # Use indexed user_id and timestamp columns
            result = session.execute(text("""
                SELECT transaction_type, amount, timestamp, status, notes, tx_hash
                FROM transaction 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT :limit
            """), {'user_id': user_id, 'limit': limit})
            return result.fetchall()
    
    def get_optimized_user_performance(self, user_id):
        """Optimized performance data retrieval"""
        with self.get_db_session() as session:
            # Single query to get all performance data
            result = session.execute(text("""
                SELECT 
                    u.balance,
                    u.initial_deposit,
                    um.current_streak,
                    um.best_streak,
                    um.next_milestone,
                    um.milestone_progress,
                    um.current_goal,
                    um.goal_progress,
                    um.trading_mode,
                    -- Today's profit from daily snapshot
                    COALESCE(ds.profit_amount, 0) as today_profit,
                    COALESCE(ds.profit_percentage, 0) as today_percentage
                FROM "user" u
                LEFT JOIN user_metrics um ON u.id = um.user_id
                LEFT JOIN daily_snapshot ds ON u.id = ds.user_id AND ds.date = CURRENT_DATE
                WHERE u.id = :user_id
            """), {'user_id': user_id})
            return result.fetchone()
    
    def get_optimized_all_users_summary(self):
        """Optimized query for admin dashboard - all users summary"""
        with self.get_db_session() as session:
            result = session.execute(text("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_users,
                    SUM(balance) as total_balance,
                    AVG(balance) as avg_balance,
                    SUM(CASE WHEN balance > initial_deposit THEN balance - initial_deposit ELSE 0 END) as total_profit
                FROM "user"
            """))
            return result.fetchone()
    
    def batch_update_balances(self, balance_updates):
        """Optimized batch balance updates"""
        if not balance_updates:
            return 0
        
        with self.get_db_session() as session:
            # Use batch update for efficiency
            update_cases = []
            user_ids = []
            
            for user_id, new_balance in balance_updates:
                update_cases.append(f"WHEN {user_id} THEN {new_balance}")
                user_ids.append(str(user_id))
            
            query = f"""
                UPDATE "user" 
                SET balance = CASE id {' '.join(update_cases)} END,
                    last_activity = NOW()
                WHERE id IN ({','.join(user_ids)})
            """
            
            result = session.execute(text(query))
            return result.rowcount
    
    def analyze_query_performance(self):
        """Analyze current query performance"""
        analysis = {
            'total_queries': sum(len(queries) for queries in self.query_stats.values()),
            'query_types': {},
            'slow_queries_count': len(self.slow_queries),
            'recent_slow_queries': list(self.slow_queries)[-10:] if self.slow_queries else []
        }
        
        # Calculate average times per query type
        for query_type, times in self.query_stats.items():
            if times:
                analysis['query_types'][query_type] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times)
                }
        
        return analysis
    
    def get_connection_pool_status(self):
        """Get connection pool health status"""
        if not self.engine:
            return {'status': 'not_initialized'}
        
        pool = self.engine.pool
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'invalid': pool.invalid()
        }
    
    def optimize_table_statistics(self):
        """Update table statistics for better query planning"""
        tables = ['user', 'transaction', 'trading_position', 'profit', 'daily_snapshot', 'user_metrics']
        
        with self.get_db_session() as session:
            for table in tables:
                try:
                    session.execute(text(f"ANALYZE {table}"))
                    logger.info(f"Updated statistics for table: {table}")
                except Exception as e:
                    logger.warning(f"Could not analyze table {table}: {e}")
        
        logger.info("Table statistics optimization complete")


# Global optimizer instance
performance_optimizer = None

def initialize_performance_optimizer(database_url=None):
    """Initialize the global performance optimizer"""
    global performance_optimizer
    if performance_optimizer is None:
        performance_optimizer = DatabasePerformanceOptimizer(database_url)
        
        # Create indexes on startup
        performance_optimizer.create_performance_indexes()
        
        # Optimize table statistics
        performance_optimizer.optimize_table_statistics()
        
        logger.info("Database performance optimizer initialized")
    
    return performance_optimizer

def get_performance_optimizer():
    """Get the global performance optimizer instance"""
    global performance_optimizer
    if performance_optimizer is None:
        initialize_performance_optimizer()
    return performance_optimizer


# Optimized query functions for bot usage
def get_user_by_telegram_id(telegram_id):
    """Optimized user lookup"""
    optimizer = get_performance_optimizer()
    return optimizer.get_optimized_user_query(telegram_id)

def get_user_transactions(user_id, limit=10):
    """Optimized transaction history"""
    optimizer = get_performance_optimizer()
    return optimizer.get_optimized_user_transactions(user_id, limit)

def get_user_performance_data(user_id):
    """Optimized performance data"""
    optimizer = get_performance_optimizer()
    return optimizer.get_optimized_user_performance(user_id)

def get_all_users_summary():
    """Optimized admin dashboard summary"""
    optimizer = get_performance_optimizer()
    return optimizer.get_optimized_all_users_summary()

def batch_update_user_balances(balance_updates):
    """Optimized batch balance updates"""
    optimizer = get_performance_optimizer()
    return optimizer.batch_update_balances(balance_updates)