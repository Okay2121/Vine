"""
Robust Database Connection Handler
==================================
Replaces direct database operations with resilient connection handling
to prevent bot failures from database quota exhaustion.
"""
import os
import logging
import time
import psycopg2
from psycopg2 import OperationalError
from contextlib import contextmanager
from app import app, db
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError

logger = logging.getLogger(__name__)

class RobustDatabase:
    """Handles database operations with automatic retry and connection management"""
    
    def __init__(self, max_retries=3, retry_delay=2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    @contextmanager
    def safe_session(self):
        """Context manager for safe database sessions with automatic retry"""
        session = None
        for attempt in range(self.max_retries):
            try:
                session = db.session
                yield session
                session.commit()
                return
                
            except (SQLAlchemyError, DisconnectionError, OperationalError) as e:
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if session:
                    try:
                        session.rollback()
                    except:
                        pass
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    # Try to recreate the session
                    try:
                        db.session.remove()
                        db.create_all()
                    except:
                        pass
                else:
                    logger.error(f"All {self.max_retries} database operation attempts failed")
                    raise e
    
    def execute_with_retry(self, operation, *args, **kwargs):
        """Execute a database operation with automatic retry"""
        for attempt in range(self.max_retries):
            try:
                with app.app_context():
                    return operation(*args, **kwargs)
                    
            except (SQLAlchemyError, DisconnectionError, OperationalError) as e:
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    try:
                        db.session.rollback()
                    except:
                        pass
                else:
                    logger.error(f"Database operation failed after {self.max_retries} attempts")
                    raise e
    
    def safe_query(self, model, **filters):
        """Safely query a model with retry logic"""
        def query_operation():
            return model.query.filter_by(**filters).all()
        
        return self.execute_with_retry(query_operation)
    
    def safe_get(self, model, id):
        """Safely get a model by ID with retry logic"""
        def get_operation():
            return model.query.get(id)
        
        return self.execute_with_retry(get_operation)
    
    def safe_create(self, model_class, **data):
        """Safely create a new record with retry logic"""
        def create_operation():
            with self.safe_session() as session:
                instance = model_class(**data)
                session.add(instance)
                session.flush()  # Get the ID without committing
                return instance
        
        return create_operation()
    
    def safe_update(self, instance, **updates):
        """Safely update a record with retry logic"""
        def update_operation():
            with self.safe_session() as session:
                for key, value in updates.items():
                    setattr(instance, key, value)
                session.add(instance)
                return instance
        
        return update_operation()

# Global instance
robust_db = RobustDatabase()

# Helper functions for common operations
def safe_user_lookup(telegram_id):
    """Safely look up a user by telegram ID"""
    try:
        from models import User
        return robust_db.safe_query(User, telegram_id=str(telegram_id))
    except Exception as e:
        logger.error(f"Failed to lookup user {telegram_id}: {e}")
        return []

def safe_user_create(telegram_id, username=None, **extra_data):
    """Safely create a new user"""
    try:
        from models import User
        from datetime import datetime
        
        user_data = {
            'telegram_id': str(telegram_id),
            'username': username,
            'balance': 0.0,
            'joined_at': datetime.utcnow(),
            **extra_data
        }
        
        return robust_db.safe_create(User, **user_data)
    except Exception as e:
        logger.error(f"Failed to create user {telegram_id}: {e}")
        return None

def safe_balance_update(user_id, new_balance):
    """Safely update user balance"""
    try:
        from models import User
        user = robust_db.safe_get(User, user_id)
        if user:
            return robust_db.safe_update(user, balance=new_balance)
        return None
    except Exception as e:
        logger.error(f"Failed to update balance for user {user_id}: {e}")
        return None

def safe_transaction_create(user_id, transaction_type, amount, **extra_data):
    """Safely create a transaction record"""
    try:
        from models import Transaction
        from datetime import datetime
        import uuid
        
        tx_data = {
            'user_id': user_id,
            'transaction_type': transaction_type,
            'amount': amount,
            'timestamp': datetime.utcnow(),
            'status': 'completed',
            'tx_hash': f"{transaction_type}_{user_id}_{uuid.uuid4().hex[:8]}",
            **extra_data
        }
        
        return robust_db.safe_create(Transaction, **tx_data)
    except Exception as e:
        logger.error(f"Failed to create transaction for user {user_id}: {e}")
        return None

def safe_trading_position_create(user_id, token_name, amount, entry_price, **extra_data):
    """Safely create a trading position"""
    try:
        from models import TradingPosition
        from datetime import datetime
        
        position_data = {
            'user_id': user_id,
            'token_name': token_name,
            'amount': amount,
            'entry_price': entry_price,
            'current_price': entry_price,
            'timestamp': datetime.utcnow(),
            'status': 'open',
            **extra_data
        }
        
        return robust_db.safe_create(TradingPosition, **position_data)
    except Exception as e:
        logger.error(f"Failed to create trading position for user {user_id}: {e}")
        return None