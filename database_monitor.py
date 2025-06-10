"""
Database Health Monitor - Prevents SQLAlchemy Failures
====================================================
Monitors database health and automatically handles connection issues
to prevent bot crashes from database problems.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from app import app, db
from sqlalchemy import text
from database_error_handler import safe_query

logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """Monitors database health and handles connection issues"""
    
    def __init__(self):
        self.is_running = False
        self.monitor_thread = None
        self.last_health_check = None
        self.consecutive_failures = 0
        self.max_failures = 5
        self.check_interval = 30  # seconds
        
    def start_monitoring(self):
        """Start the database health monitoring"""
        if self.is_running:
            logger.info("Database monitor already running")
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Database health monitor started")
    
    def stop_monitoring(self):
        """Stop the database health monitoring"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Database health monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._perform_health_check()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in database monitor loop: {e}")
                time.sleep(self.check_interval)
    
    def _perform_health_check(self):
        """Perform database health check"""
        try:
            with app.app_context():
                # Simple connectivity test
                def test_query():
                    return db.session.execute(text("SELECT 1")).fetchone()
                
                result = safe_query(test_query, default_return=None, max_retries=1)
                
                if result is not None:
                    # Health check passed
                    self.consecutive_failures = 0
                    self.last_health_check = datetime.now()
                    logger.debug("Database health check passed")
                else:
                    # Health check failed
                    self.consecutive_failures += 1
                    logger.warning(f"Database health check failed (attempt {self.consecutive_failures})")
                    
                    if self.consecutive_failures >= self.max_failures:
                        self._handle_persistent_failure()
                        
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Database health check error: {e}")
    
    def _handle_persistent_failure(self):
        """Handle persistent database failures"""
        logger.error(f"Database has failed {self.consecutive_failures} consecutive health checks")
        
        # Try to reset the connection pool
        try:
            db.engine.dispose()
            logger.info("Database connection pool reset")
        except Exception as e:
            logger.error(f"Failed to reset connection pool: {e}")
        
        # Reset failure counter to prevent spam
        self.consecutive_failures = 0
    
    def get_status(self):
        """Get current monitor status"""
        return {
            "is_running": self.is_running,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "consecutive_failures": self.consecutive_failures,
            "check_interval": self.check_interval
        }

# Global monitor instance
db_monitor = DatabaseMonitor()

def start_database_monitor():
    """Start the global database monitor"""
    db_monitor.start_monitoring()

def stop_database_monitor():
    """Stop the global database monitor"""
    db_monitor.stop_monitoring()

def get_monitor_status():
    """Get database monitor status"""
    return db_monitor.get_status()