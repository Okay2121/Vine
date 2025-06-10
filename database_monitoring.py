"""
Database Monitoring and Resilience Module
=========================================
Implements proactive monitoring, connection resilience, and automated cleanup
to prevent database quota exhaustion and bot failures.
"""
import os
import logging
import time
import psycopg2
from psycopg2 import OperationalError
from datetime import datetime, timedelta
from app import app, db
from models import User, Transaction, TradingPosition, Profit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """Database monitoring and resilience handler"""
    
    def __init__(self):
        self.connection_retries = 3
        self.retry_delay = 5
        
    def get_robust_connection(self):
        """Get database connection with retry logic"""
        for attempt in range(self.connection_retries):
            try:
                # Use the existing DATABASE_URL from environment
                database_url = os.environ.get('DATABASE_URL')
                if not database_url:
                    raise Exception("DATABASE_URL not found in environment")
                
                conn = psycopg2.connect(database_url)
                logger.info(f"Database connection successful on attempt {attempt + 1}")
                return conn
                
            except OperationalError as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.connection_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error("All database connection attempts failed")
                    raise Exception(f"Database connection failed after {self.connection_retries} retries: {e}")
    
    def check_database_health(self):
        """Check database size, connections, and overall health"""
        try:
            with self.get_robust_connection() as conn:
                with conn.cursor() as cur:
                    # Check database size
                    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
                    db_size = cur.fetchone()[0]
                    
                    # Check active connections
                    cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                    active_connections = cur.fetchone()[0]
                    
                    # Check total connections
                    cur.execute("SELECT count(*) FROM pg_stat_activity;")
                    total_connections = cur.fetchone()[0]
                    
                    # Get table sizes
                    cur.execute("""
                        SELECT schemaname,tablename,
                               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
                    """)
                    table_sizes = cur.fetchall()
                    
                    health_report = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'database_size': db_size,
                        'active_connections': active_connections,
                        'total_connections': total_connections,
                        'table_sizes': table_sizes
                    }
                    
                    logger.info(f"Database Health Report:")
                    logger.info(f"  Size: {db_size}")
                    logger.info(f"  Active Connections: {active_connections}")
                    logger.info(f"  Total Connections: {total_connections}")
                    
                    return health_report
                    
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return None
    
    def cleanup_old_data(self, days_to_keep=30):
        """Clean up old data to prevent database bloat"""
        try:
            with app.app_context():
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
                
                # Count records before cleanup
                old_transactions = Transaction.query.filter(
                    Transaction.timestamp < cutoff_date
                ).count()
                
                old_profits = Profit.query.filter(
                    Profit.date < cutoff_date.date()
                ).count()
                
                old_positions = TradingPosition.query.filter(
                    TradingPosition.timestamp < cutoff_date
                ).count()
                
                logger.info(f"Found {old_transactions} old transactions, {old_profits} old profits, {old_positions} old positions")
                
                # Delete old records (keeping last 30 days)
                if old_transactions > 0:
                    Transaction.query.filter(
                        Transaction.timestamp < cutoff_date
                    ).delete()
                    
                if old_profits > 0:
                    Profit.query.filter(
                        Profit.date < cutoff_date.date()
                    ).delete()
                    
                if old_positions > 0:
                    TradingPosition.query.filter(
                        TradingPosition.timestamp < cutoff_date
                    ).delete()
                
                db.session.commit()
                
                cleanup_report = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'deleted_transactions': old_transactions,
                    'deleted_profits': old_profits,
                    'deleted_positions': old_positions,
                    'cutoff_date': cutoff_date.isoformat()
                }
                
                logger.info(f"Cleanup completed: {old_transactions + old_profits + old_positions} records removed")
                return cleanup_report
                
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            db.session.rollback()
            return None
    
    def vacuum_database(self):
        """Run VACUUM to reclaim space and optimize performance"""
        try:
            with self.get_robust_connection() as conn:
                conn.autocommit = True  # VACUUM requires autocommit
                with conn.cursor() as cur:
                    logger.info("Starting database VACUUM operation")
                    cur.execute("VACUUM ANALYZE;")
                    logger.info("Database VACUUM completed successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Database VACUUM failed: {e}")
            return False
    
    def get_usage_alerts(self):
        """Check for usage that might indicate approaching limits"""
        alerts = []
        
        try:
            health = self.check_database_health()
            if not health:
                alerts.append("Failed to get database health metrics")
                return alerts
            
            # Parse database size (assuming format like "123 MB" or "1.5 GB")
            size_str = health['database_size']
            if 'GB' in size_str:
                size_gb = float(size_str.split()[0])
                if size_gb > 8:  # Alert if over 8GB (close to 10GB limit)
                    alerts.append(f"Database size approaching limit: {size_str}")
            
            # Check connection count
            if health['total_connections'] > 50:  # Arbitrary threshold
                alerts.append(f"High connection count: {health['total_connections']}")
            
            # Check if any table is unusually large
            for schema, table, size in health['table_sizes']:
                if 'GB' in size and float(size.split()[0]) > 2:  # Tables over 2GB
                    alerts.append(f"Large table detected: {table} ({size})")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Usage alert check failed: {e}")
            return [f"Failed to check usage alerts: {e}"]

def run_daily_maintenance():
    """Run daily maintenance tasks"""
    logger.info("Starting daily database maintenance")
    
    monitor = DatabaseMonitor()
    
    # Health check
    health = monitor.check_database_health()
    
    # Cleanup old data
    cleanup = monitor.cleanup_old_data(days_to_keep=30)
    
    # VACUUM database
    vacuum_success = monitor.vacuum_database()
    
    # Check for alerts
    alerts = monitor.get_usage_alerts()
    
    # Log summary
    logger.info("Daily maintenance completed:")
    logger.info(f"  Health check: {'✓' if health else '✗'}")
    logger.info(f"  Cleanup: {'✓' if cleanup else '✗'}")
    logger.info(f"  VACUUM: {'✓' if vacuum_success else '✗'}")
    
    if alerts:
        logger.warning(f"Alerts detected: {len(alerts)}")
        for alert in alerts:
            logger.warning(f"  - {alert}")
    
    return {
        'health': health,
        'cleanup': cleanup,
        'vacuum_success': vacuum_success,
        'alerts': alerts
    }

if __name__ == '__main__':
    # Run maintenance when called directly
    run_daily_maintenance()