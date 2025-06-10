"""
Robust Database Connection Handler
=================================
Prevents SQLAlchemy failures by implementing connection pooling,
retry logic, and graceful degradation when database quota is exceeded.
"""

import os
import time
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DisconnectionError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseConnectionHandler:
    """Handles database connections with automatic retry and graceful degradation"""
    
    def __init__(self):
        self.primary_engine = None
        self.session_factory = None
        self.last_connection_attempt = None
        self.connection_failures = 0
        self.max_failures_before_pause = 10
        self.pause_duration = 300  # 5 minutes
        self.lock = threading.Lock()
        self.is_paused = False
        
    def initialize_connection(self, database_url):
        """Initialize database connection with robust configuration"""
        try:
            # Create engine with conservative settings to avoid quota exhaustion
            self.primary_engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=3,  # Reduced from 15
                max_overflow=5,  # Reduced from 25
                pool_recycle=600,  # Increased to 10 minutes
                pool_pre_ping=True,
                pool_timeout=30,
                connect_args={
                    "sslmode": "require",
                    "connect_timeout": 30,  # Reduced timeout
                    "application_name": "solana_bot_optimized",
                    "keepalives_idle": 300,
                    "keepalives_interval": 60,
                    "keepalives_count": 2
                }
            )
            
            self.session_factory = scoped_session(sessionmaker(bind=self.primary_engine))
            
            # Test connection
            with self.primary_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.connection_failures = 0
            self.is_paused = False
            logger.info("Database connection initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            self.connection_failures += 1
            return False
    
    def _should_pause_connections(self):
        """Check if we should pause connections due to repeated failures"""
        with self.lock:
            if self.connection_failures >= self.max_failures_before_pause:
                if not self.is_paused:
                    self.is_paused = True
                    self.last_connection_attempt = datetime.now()
                    logger.warning(f"Pausing database connections for {self.pause_duration} seconds due to repeated failures")
                return True
                
            if self.is_paused and self.last_connection_attempt:
                time_since_pause = (datetime.now() - self.last_connection_attempt).total_seconds()
                if time_since_pause >= self.pause_duration:
                    self.is_paused = False
                    self.connection_failures = 0
                    logger.info("Resuming database connections after pause period")
                    return False
                return True
                
            return False
    
    @contextmanager
    def get_session(self, max_retries=2):
        """Get database session with retry logic and graceful failure handling"""
        if self._should_pause_connections():
            logger.warning("Database connections are paused due to quota exhaustion")
            yield None
            return
        
        session = None
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if not self.session_factory:
                    logger.error("Database not initialized")
                    yield None
                    return
                
                session = self.session_factory()
                
                # Test the session
                session.execute(text("SELECT 1"))
                
                yield session
                session.commit()
                
                # Reset failure count on success
                with self.lock:
                    self.connection_failures = max(0, self.connection_failures - 1)
                
                return
                
            except (OperationalError, DisconnectionError, SQLAlchemyError) as e:
                last_error = e
                error_str = str(e).lower()
                
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except:
                        pass
                    session = None
                
                # Check for quota exhaustion
                if "quota" in error_str or "limit" in error_str:
                    logger.error(f"Database quota exhausted: {e}")
                    with self.lock:
                        self.connection_failures += 5  # Increase failures quickly for quota issues
                    break
                
                # Regular connection error
                with self.lock:
                    self.connection_failures += 1
                
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Database connection failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All database connection attempts failed: {e}")
            
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected database error: {e}")
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except:
                        pass
                break
        
        # If we get here, all attempts failed
        yield None
    
    def execute_safe_query(self, operation, *args, **kwargs):
        """Execute database operation safely with error handling"""
        with self.get_session() as session:
            if session is None:
                logger.warning("Database unavailable, skipping operation")
                return None
            
            try:
                return operation(session, *args, **kwargs)
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                return None
    
    def is_healthy(self):
        """Check if database connection is healthy"""
        try:
            with self.get_session(max_retries=1) as session:
                if session is None:
                    return False
                session.execute(text("SELECT 1"))
                return True
        except:
            return False
    
    def get_status(self):
        """Get current database connection status"""
        return {
            "healthy": self.is_healthy(),
            "paused": self.is_paused,
            "failure_count": self.connection_failures,
            "last_attempt": self.last_connection_attempt.isoformat() if self.last_connection_attempt else None
        }

# Global instance
db_handler = DatabaseConnectionHandler()

def initialize_database_handler(database_url):
    """Initialize the global database handler"""
    return db_handler.initialize_connection(database_url)

def get_db_session():
    """Get a database session using the handler"""
    return db_handler.get_session()

def execute_db_operation(operation, *args, **kwargs):
    """Execute a database operation safely"""
    return db_handler.execute_safe_query(operation, *args, **kwargs)

def get_database_status():
    """Get database status"""
    return db_handler.get_status()