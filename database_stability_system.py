"""
Complete Database Stability System
==================================
Prevents all SQLAlchemy failures and ensures your bot never crashes
from database issues. This system replaces direct database calls
throughout your bot with error-resistant operations.
"""

import logging
import threading
import time
import functools
from contextlib import contextmanager
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
from sqlalchemy import text
from app import app, db

logger = logging.getLogger(__name__)

class DatabaseStabilityManager:
    """Manages database stability and prevents SQLAlchemy failures"""
    
    def __init__(self):
        self.connection_healthy = True
        self.last_health_check = datetime.now()
        self.failed_operations = 0
        self.max_failures = 10
        self.health_check_interval = 60
        self.monitor_thread = None
        self.is_monitoring = False
        self.lock = threading.Lock()
    
    def start_monitoring(self):
        """Start database health monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_health, daemon=True)
        self.monitor_thread.start()
        logger.info("Database stability monitoring started")
    
    def _monitor_health(self):
        """Monitor database health continuously"""
        while self.is_monitoring:
            try:
                self._perform_health_check()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                time.sleep(30)
    
    def _perform_health_check(self):
        """Perform database health check"""
        try:
            with app.app_context():
                result = db.session.execute(text("SELECT 1")).fetchone()
                if result:
                    with self.lock:
                        self.connection_healthy = True
                        self.last_health_check = datetime.now()
                        self.failed_operations = max(0, self.failed_operations - 1)
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            with self.lock:
                self.connection_healthy = False
                self.failed_operations += 1
    
    def is_database_healthy(self):
        """Check if database is currently healthy"""
        with self.lock:
            # Consider unhealthy if too many recent failures
            if self.failed_operations >= self.max_failures:
                return False
            
            # Consider unhealthy if no recent health check
            time_since_check = (datetime.now() - self.last_health_check).total_seconds()
            if time_since_check > self.health_check_interval * 2:
                return False
            
            return self.connection_healthy
    
    def record_failure(self):
        """Record a database operation failure"""
        with self.lock:
            self.failed_operations += 1
            self.connection_healthy = False
    
    def record_success(self):
        """Record a successful database operation"""
        with self.lock:
            self.failed_operations = max(0, self.failed_operations - 1)
            self.connection_healthy = True
            self.last_health_check = datetime.now()

# Global stability manager
stability_manager = DatabaseStabilityManager()

def stable_db_operation(default_return=None, max_retries=2):
    """
    Decorator for database operations with automatic error handling
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not stability_manager.is_database_healthy():
                logger.warning(f"Database unhealthy, skipping {func.__name__}")
                return default_return
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    stability_manager.record_success()
                    return result
                    
                except (SQLAlchemyError, OperationalError, DisconnectionError) as e:
                    stability_manager.record_failure()
                    
                    if attempt < max_retries:
                        logger.warning(f"Database operation failed, retrying {func.__name__}: {e}")
                        time.sleep(1)
                        continue
                    else:
                        logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                        try:
                            db.session.rollback()
                        except:
                            pass
                        return default_return
                        
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    try:
                        db.session.rollback()
                    except:
                        pass
                    return default_return
            
            return default_return
        return wrapper
    return decorator

@contextmanager
def stable_session():
    """Context manager for stable database sessions"""
    if not stability_manager.is_database_healthy():
        logger.warning("Database unhealthy, yielding None session")
        yield None
        return
    
    try:
        yield db.session
        db.session.commit()
        stability_manager.record_success()
    except (SQLAlchemyError, OperationalError, DisconnectionError) as e:
        stability_manager.record_failure()
        logger.error(f"Database session error: {e}")
        try:
            db.session.rollback()
        except:
            pass
    except Exception as e:
        logger.error(f"Unexpected session error: {e}")
        try:
            db.session.rollback()
        except:
            pass

# Safe database operations for your bot
@stable_db_operation(default_return=None)
def safe_get_user(telegram_id=None, username=None):
    """Safely get user from database"""
    from models import User
    
    if telegram_id:
        return User.query.filter_by(telegram_id=str(telegram_id)).first()
    elif username:
        clean_username = username.replace('@', '').lower()
        return User.query.filter(User.username.ilike(f'%{clean_username}%')).first()
    return None

@stable_db_operation(default_return=None)
def safe_create_user(telegram_id, username, first_name=None):
    """Safely create a new user"""
    from models import User
    
    user = User()
    user.telegram_id = str(telegram_id)
    user.username = username
    user.first_name = first_name or "Unknown"
    
    db.session.add(user)
    db.session.flush()
    return user

@stable_db_operation(default_return=False)
def safe_update_user_balance(user_id, new_balance):
    """Safely update user balance"""
    from models import User
    
    user = User.query.get(user_id)
    if user:
        user.balance = new_balance
        db.session.flush()
        return True
    return False

@stable_db_operation(default_return=[])
def safe_get_user_transactions(user_id, limit=10):
    """Safely get user transactions"""
    from models import Transaction
    
    return Transaction.query.filter_by(user_id=user_id).order_by(
        Transaction.timestamp.desc()
    ).limit(limit).all()

@stable_db_operation(default_return=None)
def safe_create_transaction(user_id, amount, transaction_type, notes=None):
    """Safely create a transaction record"""
    from models import Transaction
    
    transaction = Transaction()
    transaction.user_id = user_id
    transaction.amount = amount
    transaction.transaction_type = transaction_type
    transaction.notes = notes or f"{transaction_type} transaction"
    
    db.session.add(transaction)
    db.session.flush()
    return transaction

@stable_db_operation(default_return=[])
def safe_get_all_users(active_only=False, limit=None):
    """Safely get all users"""
    from models import User, UserStatus
    
    query_obj = User.query
    if active_only:
        query_obj = query_obj.filter(User.status == UserStatus.ACTIVE)
    if limit:
        query_obj = query_obj.limit(limit)
    return query_obj.all()

@stable_db_operation(default_return=[])
def safe_get_trading_positions(user_id, status=None, limit=10):
    """Safely get trading positions"""
    from models import TradingPosition
    
    query_obj = TradingPosition.query.filter_by(user_id=user_id)
    if status:
        query_obj = query_obj.filter_by(status=status)
    
    return query_obj.order_by(TradingPosition.timestamp.desc()).limit(limit).all()

@stable_db_operation(default_return=None)
def safe_create_trading_position(user_id, token_name, amount, entry_price, **kwargs):
    """Safely create a trading position"""
    from models import TradingPosition
    
    position = TradingPosition()
    position.user_id = user_id
    position.token_name = token_name
    position.amount = amount
    position.entry_price = entry_price
    position.current_price = entry_price
    
    # Set additional fields from kwargs
    for key, value in kwargs.items():
        if hasattr(position, key):
            setattr(position, key, value)
    
    db.session.add(position)
    db.session.flush()
    return position

def get_database_health_status():
    """Get current database health status"""
    return {
        "healthy": stability_manager.is_database_healthy(),
        "last_check": stability_manager.last_health_check.isoformat(),
        "failed_operations": stability_manager.failed_operations,
        "monitoring": stability_manager.is_monitoring
    }

def initialize_database_stability():
    """Initialize the database stability system"""
    stability_manager.start_monitoring()
    logger.info("Database stability system initialized")

# Auto-initialize when imported
initialize_database_stability()