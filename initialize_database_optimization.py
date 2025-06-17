"""
Initialize Database Optimization
===============================
Sets up database indexes and performance monitoring within Flask application context.
"""

import logging
from app import app, db
from sqlalchemy import text

logger = logging.getLogger(__name__)

def create_performance_indexes():
    """Create essential indexes for query performance"""
    
    essential_indexes = [
        # User table - most critical for lookups
        'CREATE INDEX IF NOT EXISTS idx_user_telegram_id_fast ON "user" (telegram_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_status_enum ON "user" (status)',
        'CREATE INDEX IF NOT EXISTS idx_user_balance_nonzero ON "user" (balance) WHERE balance > 0',
        'CREATE INDEX IF NOT EXISTS idx_user_last_activity ON "user" (last_activity)',
        
        # Transaction table - extremely critical for performance
        'CREATE INDEX IF NOT EXISTS idx_transaction_user_time ON transaction (user_id, timestamp DESC)',
        'CREATE INDEX IF NOT EXISTS idx_transaction_type_status ON transaction (transaction_type, status)',
        'CREATE INDEX IF NOT EXISTS idx_transaction_hash_unique ON transaction (tx_hash) WHERE tx_hash IS NOT NULL',
        'CREATE INDEX IF NOT EXISTS idx_transaction_processed_at ON transaction (processed_at) WHERE processed_at IS NOT NULL',
        
        # Trading positions - critical for dashboard
        'CREATE INDEX IF NOT EXISTS idx_trading_user_status ON trading_position (user_id, status)',
        'CREATE INDEX IF NOT EXISTS idx_trading_timestamp ON trading_position (timestamp DESC)',
        'CREATE INDEX IF NOT EXISTS idx_trading_token_name ON trading_position (token_name)',
        
        # Profit table - dashboard performance
        'CREATE INDEX IF NOT EXISTS idx_profit_user_date ON profit (user_id, date DESC)',
        'CREATE INDEX IF NOT EXISTS idx_profit_date_recent ON profit (date) WHERE date >= CURRENT_DATE - INTERVAL \'30 days\'',
        
        # User metrics - real-time dashboard
        'CREATE INDEX IF NOT EXISTS idx_user_metrics_user ON user_metrics (user_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_metrics_updated ON user_metrics (last_updated)',
        
        # Daily snapshots - performance tracking
        'CREATE INDEX IF NOT EXISTS idx_daily_snapshot_user_date ON daily_snapshot (user_id, date DESC)',
        'CREATE INDEX IF NOT EXISTS idx_daily_snapshot_date ON daily_snapshot (date)',
        
        # Support system indexes
        'CREATE INDEX IF NOT EXISTS idx_support_ticket_user ON support_ticket (user_id, status)',
        'CREATE INDEX IF NOT EXISTS idx_support_ticket_status ON support_ticket (status, created_at)',
        
        # Referral system indexes
        'CREATE INDEX IF NOT EXISTS idx_referral_code_active ON referral_code (code) WHERE is_active = true',
        'CREATE INDEX IF NOT EXISTS idx_referral_reward_referrer ON referral_reward (referrer_id, timestamp)',
        
        # Trading cycle indexes
        'CREATE INDEX IF NOT EXISTS idx_trading_cycle_user_status ON trading_cycle (user_id, status)',
        'CREATE INDEX IF NOT EXISTS idx_trading_cycle_status ON trading_cycle (status, start_date)',
    ]
    
    created_count = 0
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                for index_sql in essential_indexes:
                    try:
                        conn.execute(text(index_sql))
                        conn.commit()
                        created_count += 1
                        
                        # Extract index name for logging
                        index_name = 'unknown'
                        if 'idx_' in index_sql:
                            index_name = index_sql.split('idx_')[1].split(' ')[0]
                        
                        logger.info(f"Created/verified index: idx_{index_name}")
                        
                    except Exception as e:
                        logger.warning(f"Index creation skipped (may already exist): {str(e)[:100]}")
                        
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return 0
    
    logger.info(f"Database indexing complete. Created/verified {created_count} indexes.")
    return created_count

def optimize_database_statistics():
    """Update database statistics for better query planning"""
    tables = ['user', 'transaction', 'trading_position', 'profit', 'user_metrics', 'daily_snapshot']
    
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                for table in tables:
                    try:
                        conn.execute(text(f"ANALYZE {table}"))
                        logger.info(f"Updated statistics for {table}")
                    except Exception as e:
                        logger.warning(f"Could not analyze {table}: {e}")
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    logger.info("Database statistics optimization complete")

def check_database_performance():
    """Check current database performance metrics"""
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Check index usage
                result = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan as scans,
                        idx_tup_read as tuples_read
                    FROM pg_stat_user_indexes 
                    WHERE schemaname = 'public' AND idx_scan > 0
                    ORDER BY idx_scan DESC
                    LIMIT 10
                """))
                
                index_stats = result.fetchall()
                logger.info(f"Found {len(index_stats)} active indexes")
                
                # Check table sizes
                result = conn.execute(text("""
                    SELECT 
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 5
                """))
                
                table_sizes = result.fetchall()
                logger.info("Top 5 table sizes:")
                for table in table_sizes:
                    logger.info(f"  {table.tablename}: {table.size}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error checking database performance: {e}")
            return False

def run_optimization():
    """Run complete database optimization"""
    logger.info("Starting database performance optimization...")
    
    # Create indexes
    indexes_created = create_performance_indexes()
    
    # Update statistics
    optimize_database_statistics()
    
    # Check performance
    performance_ok = check_database_performance()
    
    logger.info(f"Database optimization complete. Indexes: {indexes_created}, Performance check: {'OK' if performance_ok else 'Failed'}")
    
    return {
        'indexes_created': indexes_created,
        'statistics_updated': True,
        'performance_check': performance_ok
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_optimization()
    print(f"Optimization result: {result}")