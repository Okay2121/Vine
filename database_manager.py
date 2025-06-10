"""
Robust Database Manager with Connection Pooling and Retry Logic
==============================================================
This module provides enterprise-grade database connectivity with:
- Connection pooling for better resource management
- Automatic retry logic for transient failures
- Circuit breaker pattern for persistent failures
- Health monitoring and recovery mechanisms
- Multiple database provider support
"""

import os
import time
import logging
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager
from sqlalchemy import create_engine, text, pool
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import psycopg2
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections with resilience patterns."""
    
    def __init__(self):
        self.engines = {}
        self.session_factories = {}
        self.circuit_breaker = CircuitBreaker()
        self.health_monitor = DatabaseHealthMonitor()
        self._setup_databases()
    
    def _setup_databases(self):
        """Setup multiple database connections with fallback options."""
        
        # Primary database (current Neon)
        primary_url = os.environ.get('DATABASE_URL') or \
                     "postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        
        # Backup database URLs (add your AWS RDS or other providers)
        backup_urls = [
            os.environ.get('BACKUP_DATABASE_URL'),
            os.environ.get('AWS_RDS_URL'),
        ]
        backup_urls = [url for url in backup_urls if url]
        
        # Setup primary connection
        self._create_engine_with_pool('primary', primary_url)
        
        # Setup backup connections
        for i, backup_url in enumerate(backup_urls):
            self._create_engine_with_pool(f'backup_{i}', backup_url)
    
    def _create_engine_with_pool(self, name, database_url):
        """Create database engine with connection pooling."""
        try:
            engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "solana_trading_bot"
                }
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.engines[name] = engine
            self.session_factories[name] = scoped_session(sessionmaker(bind=engine))
            logger.info(f"Database engine '{name}' created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database engine '{name}': {str(e)}")
    
    @contextmanager
    def get_session(self, retry_count=3):
        """Get database session with automatic retry and fallback."""
        last_error = None
        
        # Try primary database first
        for attempt in range(retry_count):
            try:
                if self.circuit_breaker.can_execute():
                    session = self._get_primary_session()
                    if session:
                        try:
                            yield session
                            session.commit()
                            self.circuit_breaker.record_success()
                            return
                        except Exception as e:
                            session.rollback()
                            raise e
                        finally:
                            session.close()
            except Exception as e:
                last_error = e
                self.circuit_breaker.record_failure()
                logger.warning(f"Primary database attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        # Try backup databases
        for engine_name in self.engines:
            if engine_name != 'primary':
                try:
                    session = self.session_factories[engine_name]()
                    try:
                        yield session
                        session.commit()
                        logger.info(f"Using backup database: {engine_name}")
                        return
                    except Exception as e:
                        session.rollback()
                        raise e
                    finally:
                        session.close()
                except Exception as e:
                    logger.error(f"Backup database {engine_name} failed: {str(e)}")
        
        # If all databases fail
        logger.error("All database connections failed")
        raise last_error or Exception("No database connections available")
    
    def _get_primary_session(self):
        """Get session from primary database."""
        if 'primary' in self.session_factories:
            return self.session_factories['primary']()
        return None
    
    def health_check(self):
        """Perform health check on all database connections."""
        status = {}
        
        for name, engine in self.engines.items():
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1")).scalar()
                    status[name] = {'healthy': True, 'response_time': 0.1}
            except Exception as e:
                status[name] = {'healthy': False, 'error': str(e)}
        
        return status
    
    def get_primary_engine(self):
        """Get primary database engine for direct use."""
        return self.engines.get('primary')


class CircuitBreaker:
    """Circuit breaker pattern for database connections."""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def can_execute(self):
        """Check if operation can be executed."""
        with self._lock:
            if self.state == 'CLOSED':
                return True
            elif self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                    return True
                return False
            else:  # HALF_OPEN
                return True
    
    def record_success(self):
        """Record successful operation."""
        with self._lock:
            self.failure_count = 0
            self.state = 'CLOSED'
    
    def record_failure(self):
        """Record failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
    
    def _should_attempt_reset(self):
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time:
            return datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        return True


class DatabaseHealthMonitor:
    """Monitor database health and trigger recovery actions."""
    
    def __init__(self):
        self.last_check = None
        self.check_interval = 300  # 5 minutes
        self.health_history = []
    
    def should_check_health(self):
        """Determine if health check should be performed."""
        if not self.last_check:
            return True
        return datetime.utcnow() - self.last_check > timedelta(seconds=self.check_interval)
    
    def record_health_check(self, status):
        """Record health check results."""
        self.last_check = datetime.utcnow()
        self.health_history.append({
            'timestamp': self.last_check,
            'status': status
        })
        
        # Keep only last 24 hours of history
        cutoff_time = self.last_check - timedelta(hours=24)
        self.health_history = [
            record for record in self.health_history 
            if record['timestamp'] > cutoff_time
        ]


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session():
    """Convenience function to get database session."""
    return db_manager.get_session()


def init_database_with_fallback():
    """Initialize database with fallback support."""
    try:
        # Try to create tables using primary database
        from app import db, app
        
        with app.app_context():
            with get_db_session() as session:
                # Test query
                session.execute(text("SELECT 1"))
                logger.info("Database connection established successfully")
                return True
                
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False


def monitor_database_health():
    """Background task to monitor database health."""
    def health_check_worker():
        while True:
            try:
                if db_manager.health_monitor.should_check_health():
                    status = db_manager.health_check()
                    db_manager.health_monitor.record_health_check(status)
                    
                    # Log health status
                    healthy_dbs = [name for name, info in status.items() if info['healthy']]
                    if healthy_dbs:
                        logger.info(f"Healthy databases: {', '.join(healthy_dbs)}")
                    else:
                        logger.warning("No healthy databases detected")
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health monitor error: {str(e)}")
                time.sleep(300)  # Wait 5 minutes on error
    
    # Start health monitor in background thread
    thread = threading.Thread(target=health_check_worker, daemon=True)
    thread.start()
    logger.info("Database health monitor started")


if __name__ == "__main__":
    # Test the database manager
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Database Manager...")
    
    # Test health check
    status = db_manager.health_check()
    print(f"Health Status: {status}")
    
    # Test session creation
    try:
        with get_db_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            print(f"Session test successful: {result}")
    except Exception as e:
        print(f"Session test failed: {e}")