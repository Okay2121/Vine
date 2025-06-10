"""
Database Error Handler - Prevents Bot Crashes from SQLAlchemy Failures
=====================================================================
This module wraps all database operations with error handling to ensure
the Telegram bot continues running even when database issues occur.
"""

import logging
import functools
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
from app import db

logger = logging.getLogger(__name__)

def handle_db_errors(default_return=None, log_error=True):
    """
    Decorator to handle database errors gracefully
    
    Args:
        default_return: Value to return if database operation fails
        log_error: Whether to log the error (default: True)
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (SQLAlchemyError, OperationalError, DisconnectionError) as e:
                if log_error:
                    logger.error(f"Database error in {func.__name__}: {str(e)}")
                try:
                    db.session.rollback()
                except:
                    pass
                return default_return
            except Exception as e:
                if log_error:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                try:
                    db.session.rollback()
                except:
                    pass
                return default_return
        return wrapper
    return decorator

@contextmanager
def safe_db_session():
    """
    Context manager for safe database sessions
    Automatically handles errors and rollbacks
    """
    try:
        yield db.session
        db.session.commit()
    except (SQLAlchemyError, OperationalError, DisconnectionError) as e:
        logger.error(f"Database session error: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        raise e
    except Exception as e:
        logger.error(f"Unexpected session error: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        raise e

def safe_query(query_func, default_return=None, max_retries=2):
    """
    Execute database query with automatic retry and error handling
    
    Args:
        query_func: Function that performs the database query
        default_return: Value to return if all attempts fail
        max_retries: Maximum number of retry attempts
    
    Returns:
        Query result or default_return if failed
    """
    for attempt in range(max_retries + 1):
        try:
            with safe_db_session():
                return query_func()
        except (SQLAlchemyError, OperationalError, DisconnectionError) as e:
            if attempt < max_retries:
                logger.warning(f"Database query failed (attempt {attempt + 1}), retrying: {str(e)}")
                continue
            else:
                logger.error(f"All database query attempts failed: {str(e)}")
                return default_return
        except Exception as e:
            logger.error(f"Unexpected error in database query: {str(e)}")
            return default_return

def get_user_safely(telegram_id=None, username=None):
    """
    Safely get user from database with error handling
    
    Args:
        telegram_id: User's Telegram ID
        username: User's username
    
    Returns:
        User object or None if not found/error
    """
    def query():
        from models import User
        if telegram_id:
            return User.query.filter_by(telegram_id=str(telegram_id)).first()
        elif username:
            clean_username = username.replace('@', '').lower()
            return User.query.filter(User.username.ilike(f'%{clean_username}%')).first()
        return None
    
    return safe_query(query, default_return=None)

def create_user_safely(telegram_id, username, first_name=None):
    """
    Safely create a new user with error handling
    
    Args:
        telegram_id: User's Telegram ID
        username: User's username
        first_name: User's first name
    
    Returns:
        User object or None if creation failed
    """
    def query():
        from models import User
        user = User(
            telegram_id=str(telegram_id),
            username=username,
            first_name=first_name or "Unknown"
        )
        db.session.add(user)
        db.session.flush()
        return user
    
    return safe_query(query, default_return=None)

def update_user_balance_safely(user_id, new_balance):
    """
    Safely update user balance with error handling
    
    Args:
        user_id: User's database ID
        new_balance: New balance amount
    
    Returns:
        True if successful, False otherwise
    """
    def query():
        from models import User
        user = User.query.get(user_id)
        if user:
            user.balance = new_balance
            db.session.flush()
            return True
        return False
    
    result = safe_query(query, default_return=False)
    return result is not False

def get_user_transactions_safely(user_id, limit=10):
    """
    Safely get user transactions with error handling
    
    Args:
        user_id: User's database ID
        limit: Maximum number of transactions to return
    
    Returns:
        List of transactions or empty list if error
    """
    def query():
        from models import Transaction
        return Transaction.query.filter_by(user_id=user_id).order_by(
            Transaction.created_at.desc()
        ).limit(limit).all()
    
    return safe_query(query, default_return=[])

def create_transaction_safely(user_id, amount, transaction_type, description=None):
    """
    Safely create a transaction record with error handling
    
    Args:
        user_id: User's database ID
        amount: Transaction amount
        transaction_type: Type of transaction
        description: Optional description
    
    Returns:
        Transaction object or None if creation failed
    """
    def query():
        from models import Transaction
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description or f"{transaction_type} transaction"
        )
        db.session.add(transaction)
        db.session.flush()
        return transaction
    
    return safe_query(query, default_return=None)

def get_all_users_safely(active_only=False, limit=None):
    """
    Safely get all users with error handling
    
    Args:
        active_only: Whether to return only active users
        limit: Maximum number of users to return
    
    Returns:
        List of users or empty list if error
    """
    def query():
        from models import User
        query_obj = User.query
        if active_only:
            query_obj = query_obj.filter(User.is_active == True)
        if limit:
            query_obj = query_obj.limit(limit)
        return query_obj.all()
    
    return safe_query(query, default_return=[])

# Wrapper functions for common bot operations
def bot_get_user(telegram_id=None, username=None):
    """Bot-safe user retrieval"""
    return get_user_safely(telegram_id=telegram_id, username=username)

def bot_create_user(telegram_id, username, first_name=None):
    """Bot-safe user creation"""
    return create_user_safely(telegram_id, username, first_name)

def bot_update_balance(user_id, new_balance):
    """Bot-safe balance update"""
    return update_user_balance_safely(user_id, new_balance)

def bot_get_transactions(user_id, limit=10):
    """Bot-safe transaction retrieval"""
    return get_user_transactions_safely(user_id, limit)

def bot_create_transaction(user_id, amount, transaction_type, description=None):
    """Bot-safe transaction creation"""
    return create_transaction_safely(user_id, amount, transaction_type, description)

def bot_get_all_users(active_only=False, limit=None):
    """Bot-safe user listing"""
    return get_all_users_safely(active_only, limit)