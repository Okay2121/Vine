"""
Database utility module
Provides a unified interface for database operations
"""

import logging
import asyncio
from datetime import datetime
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Initialize database connection
try:
    from app import db, app
    from models import User, Transaction, Trade, ReferralCode
    
    def _get_db_session():
        """Get a database session within app context"""
        return db.session
        
except ImportError:
    logger.warning("Could not import app and models directly - using standalone mode")
    db = None
    app = None
    
    # Mock data for development - will be replaced with actual database queries
    _users = {}
    _trades = {}
    _transactions = {}
    _settings = {}
    
    def _get_db_session():
        """Get a database session in standalone mode"""
        return None

async def get_user_balance(user_id):
    """
    Get a user's balance
    
    Args:
        user_id: The user's ID
        
    Returns:
        float: User's balance or 0 if not found
    """
    try:
        if db and app:
            with app.app_context():
                session = _get_db_session()
                user = session.query(User).filter_by(id=user_id).first()
                return user.balance if user else 0
        else:
            # Use mock data
            return _users.get(user_id, {}).get('balance', 0)
    except Exception as e:
        logger.error(f"Error getting balance for user {user_id}: {e}")
        return 0

async def update_user_balance(user_id, amount):
    """
    Update a user's balance
    
    Args:
        user_id: The user's ID
        amount: Amount to add (positive) or subtract (negative)
        
    Returns:
        bool: Success status
    """
    try:
        if db and app:
            with app.app_context():
                session = _get_db_session()
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    # Update balance
                    old_balance = user.balance
                    user.balance += amount
                    
                    # Prevent negative balance
                    if user.balance < 0:
                        user.balance = 0
                        
                    session.commit()
                    
                    logger.info(f"Updated balance for user {user_id}: {old_balance} -> {user.balance}")
                    return True
                return False
        else:
            # Use mock data
            if user_id in _users:
                old_balance = _users[user_id].get('balance', 0)
                new_balance = old_balance + amount
                
                # Prevent negative balance
                if new_balance < 0:
                    new_balance = 0
                    
                _users[user_id]['balance'] = new_balance
                
                logger.info(f"Updated balance for user {user_id}: {old_balance} -> {new_balance}")
                return True
            return False
    except Exception as e:
        logger.error(f"Error updating balance for user {user_id}: {e}")
        return False

async def create_trade_record(user_id, token, amount, profit, roi_percentage):
    """
    Create a trade record
    
    Args:
        user_id: The user's ID
        token: The token traded
        amount: The amount traded
        profit: The profit made
        roi_percentage: The ROI percentage
        
    Returns:
        dict: Created trade record or None if failed
    """
    try:
        if db and app:
            with app.app_context():
                session = _get_db_session()
                
                # Create new trade record
                new_trade = Trade(
                    user_id=user_id,
                    token=token,
                    amount=amount,
                    profit=profit,
                    roi_percentage=roi_percentage,
                    timestamp=datetime.now()
                )
                
                session.add(new_trade)
                session.commit()
                
                logger.info(f"Created trade record for user {user_id}: {token}, profit: {profit}")
                
                return {
                    'id': new_trade.id,
                    'user_id': new_trade.user_id,
                    'token': new_trade.token,
                    'amount': new_trade.amount,
                    'profit': new_trade.profit,
                    'roi_percentage': new_trade.roi_percentage,
                    'timestamp': new_trade.timestamp
                }
        else:
            # Use mock data
            trade_id = len(_trades.get(user_id, [])) + 1
            new_trade = {
                'id': trade_id,
                'user_id': user_id,
                'token': token,
                'amount': amount,
                'profit': profit,
                'roi_percentage': roi_percentage,
                'timestamp': datetime.now()
            }
            
            if user_id not in _trades:
                _trades[user_id] = []
                
            _trades[user_id].append(new_trade)
            
            logger.info(f"Created trade record for user {user_id}: {token}, profit: {profit}")
            return new_trade
    except Exception as e:
        logger.error(f"Error creating trade record for user {user_id}: {e}")
        return None

async def get_user_trades(user_id):
    """
    Get a user's trade history
    
    Args:
        user_id: The user's ID
        
    Returns:
        list: Trade records or empty list if none found
    """
    try:
        if db and app:
            with app.app_context():
                session = _get_db_session()
                trades = session.query(Trade).filter_by(user_id=user_id).order_by(Trade.timestamp.desc()).all()
                
                return [
                    {
                        'id': trade.id,
                        'user_id': trade.user_id,
                        'token': trade.token,
                        'amount': trade.amount,
                        'profit': trade.profit,
                        'roi_percentage': trade.roi_percentage,
                        'timestamp': trade.timestamp
                    }
                    for trade in trades
                ]
        else:
            # Use mock data
            return _trades.get(user_id, [])
    except Exception as e:
        logger.error(f"Error getting trades for user {user_id}: {e}")
        return []

async def get_user(user_id):
    """
    Get user by ID
    
    Args:
        user_id: The user's ID
        
    Returns:
        dict: User data or None if not found
    """
    try:
        if db and app:
            with app.app_context():
                session = _get_db_session()
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    return {
                        'id': user.id,
                        'username': user.username,
                        'telegram_id': user.telegram_id,
                        'balance': user.balance,
                        'wallet_address': user.wallet_address,
                        'created_at': user.created_at
                    }
                return None
        else:
            # Use mock data
            return _users.get(user_id)
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

async def get_user_settings(user_id):
    """
    Get user settings
    
    Args:
        user_id: The user's ID
        
    Returns:
        dict: User settings or default settings if none found
    """
    try:
        if db and app:
            with app.app_context():
                session = _get_db_session()
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    return {
                        'wallet_address': user.wallet_address,
                        'risk_level': user.risk_level or 'Medium',
                        'auto_reinvest': user.auto_reinvest or False,
                        'notifications_enabled': user.notifications_enabled or True,
                        'daily_report': user.daily_report or True
                    }
        
        # Use mock data or return defaults
        if user_id in _settings:
            return _settings[user_id]
        else:
            return {
                'wallet_address': 'Not set',
                'risk_level': 'Medium',
                'auto_reinvest': False,
                'notifications_enabled': True,
                'daily_report': True
            }
    except Exception as e:
        logger.error(f"Error getting settings for user {user_id}: {e}")
        return {
            'wallet_address': 'Not set',
            'risk_level': 'Medium',
            'auto_reinvest': False,
            'notifications_enabled': True,
            'daily_report': True
        }

async def update_user_setting(user_id, setting_name, value):
    """
    Update a user setting
    
    Args:
        user_id: The user's ID
        setting_name: Name of the setting to update
        value: New value for the setting
        
    Returns:
        bool: Success status
    """
    try:
        if db and app:
            with app.app_context():
                session = _get_db_session()
                user = session.query(User).filter_by(id=user_id).first()
                
                if user:
                    # Update setting
                    if hasattr(user, setting_name):
                        setattr(user, setting_name, value)
                        session.commit()
                        logger.info(f"Updated setting '{setting_name}' for user {user_id}")
                        return True
                    else:
                        logger.warning(f"Setting '{setting_name}' not found for user {user_id}")
                        return False
                return False
        else:
            # Use mock data
            if user_id not in _settings:
                _settings[user_id] = {
                    'wallet_address': 'Not set',
                    'risk_level': 'Medium',
                    'auto_reinvest': False,
                    'notifications_enabled': True,
                    'daily_report': True
                }
                
            if setting_name in _settings[user_id]:
                _settings[user_id][setting_name] = value
                logger.info(f"Updated setting '{setting_name}' for user {user_id}")
                return True
            else:
                logger.warning(f"Setting '{setting_name}' not found for user {user_id}")
                return False
    except Exception as e:
        logger.error(f"Error updating setting '{setting_name}' for user {user_id}: {e}")
        return False