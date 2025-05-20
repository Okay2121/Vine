"""
Trading Engine Service
Core business logic for Solana memecoin trading operations
"""

import logging
import threading
import time
import random
from datetime import datetime, timedelta
import asyncio

# Import database utilities
from utils.database import get_user_balance, update_user_balance, create_trade_record

logger = logging.getLogger(__name__)

# In-memory storage for active trades
_active_trades = {}
_trading_status = {}
_system_paused = False

async def start_trading_with_amount(user_id, amount):
    """
    Start automated trading for a user with the specified amount
    
    Args:
        user_id: The user's ID
        amount: Amount to allocate for trading in SOL
        
    Returns:
        bool: Success status
    """
    try:
        # Check if user already has active trades
        if user_id in _active_trades:
            logger.info(f"User {user_id} already has active trading. Adding {amount} SOL to allocation.")
            _active_trades[user_id]['allocation'] += amount
        else:
            logger.info(f"Starting new trading session for user {user_id} with {amount} SOL")
            _active_trades[user_id] = {
                'allocation': amount,
                'start_time': datetime.now(),
                'trades': []
            }
            _trading_status[user_id] = True
            
            # Start trading in background thread to prevent blocking
            threading.Thread(
                target=_execute_trading_strategy,
                args=(user_id,),
                daemon=True
            ).start()
            
        return True
    except Exception as e:
        logger.error(f"Error starting trading for user {user_id}: {e}")
        return False

def _execute_trading_strategy(user_id):
    """
    Execute the trading strategy for a user in a background thread
    This runs continuously until trading is paused or stopped
    
    Args:
        user_id: The user's ID
    """
    try:
        logger.info(f"Trading strategy started for user {user_id}")
        
        while user_id in _active_trades and _trading_status.get(user_id, False):
            # Check if system is globally paused
            if _system_paused:
                logger.info(f"Trading paused for user {user_id} due to system pause")
                time.sleep(60)  # Check again in 1 minute
                continue
                
            # Simulate finding and executing a trade
            _execute_single_trade(user_id)
            
            # Sleep between trades (random interval for realism)
            sleep_minutes = random.uniform(20, 40)
            logger.info(f"Sleeping for {sleep_minutes:.1f} minutes before next trade for user {user_id}")
            time.sleep(sleep_minutes * 60)
            
    except Exception as e:
        logger.error(f"Error in trading strategy for user {user_id}: {e}")
        # Log error but don't crash the thread
        _trading_status[user_id] = False

def _execute_single_trade(user_id):
    """
    Execute a single trade for a user
    
    Args:
        user_id: The user's ID
    """
    try:
        # Get user's allocation
        allocation = _active_trades[user_id]['allocation']
        
        # Determine trade size (10-25% of allocation)
        trade_percentage = random.uniform(0.1, 0.25)
        trade_size = allocation * trade_percentage
        
        # Determine ROI (6-14% usually positive, occasional small loss)
        success = random.random() < 0.92  # 92% success rate
        roi_percentage = random.uniform(6, 14) if success else random.uniform(-5, -1)
        
        # Calculate profit
        profit = trade_size * (roi_percentage / 100)
        
        # Select a random memecoin
        memecoins = ["BONK", "SAMO", "CORG", "MOON", "WOOF", "RATS", "POPCAT"]
        token = random.choice(memecoins)
        
        # Create trade record
        trade = {
            'timestamp': datetime.now(),
            'token': token,
            'amount': trade_size,
            'roi_percentage': roi_percentage,
            'profit': profit
        }
        
        # Add to user's trade history
        _active_trades[user_id]['trades'].append(trade)
        
        # Update user balance in database
        if profit != 0:
            try:
                # In real implementation, this would use the actual database
                update_user_balance(user_id, profit)
                create_trade_record(user_id, token, trade_size, profit, roi_percentage)
            except Exception as db_error:
                logger.error(f"Database error recording trade: {db_error}")
        
        logger.info(f"Executed trade for user {user_id}: {token}, ROI: {roi_percentage:.2f}%, Profit: {profit:.4f} SOL")
        
    except Exception as e:
        logger.error(f"Error executing trade for user {user_id}: {e}")

def pause_trading(user_id=None):
    """
    Pause trading for a specific user or globally
    
    Args:
        user_id: Optional user ID. If None, pauses all trading
        
    Returns:
        bool: Success status
    """
    try:
        if user_id:
            # Pause for specific user
            if user_id in _trading_status:
                _trading_status[user_id] = False
                logger.info(f"Trading paused for user {user_id}")
            else:
                logger.warning(f"Attempted to pause trading for non-existent user {user_id}")
                return False
        else:
            # Pause globally
            global _system_paused
            _system_paused = True
            logger.info("Trading paused globally for all users")
            
        return True
    except Exception as e:
        logger.error(f"Error pausing trading: {e}")
        return False

def resume_trading(user_id=None):
    """
    Resume trading for a specific user or globally
    
    Args:
        user_id: Optional user ID. If None, resumes all trading
        
    Returns:
        bool: Success status
    """
    try:
        if user_id:
            # Resume for specific user
            if user_id in _trading_status:
                # Only start a new thread if not already running
                was_paused = not _trading_status[user_id]
                _trading_status[user_id] = True
                
                if was_paused and user_id in _active_trades:
                    # Restart trading thread
                    threading.Thread(
                        target=_execute_trading_strategy,
                        args=(user_id,),
                        daemon=True
                    ).start()
                    
                logger.info(f"Trading resumed for user {user_id}")
            else:
                logger.warning(f"Attempted to resume trading for non-existent user {user_id}")
                return False
        else:
            # Resume globally
            global _system_paused
            _system_paused = False
            logger.info("Trading resumed globally for all users")
            
        return True
    except Exception as e:
        logger.error(f"Error resuming trading: {e}")
        return False
        
def get_trading_status(user_id=None):
    """
    Get trading status for a user or the whole system
    
    Args:
        user_id: Optional user ID. If None, returns global system status
        
    Returns:
        dict: Trading status information
    """
    try:
        if user_id:
            # Get status for specific user
            if user_id in _active_trades:
                allocation = _active_trades[user_id]['allocation']
                trade_count = len(_active_trades[user_id]['trades'])
                is_active = _trading_status.get(user_id, False) and not _system_paused
                
                # Calculate total profit
                total_profit = sum(trade['profit'] for trade in _active_trades[user_id]['trades'])
                
                # Get most recent trades (up to 5)
                recent_trades = sorted(
                    _active_trades[user_id]['trades'],
                    key=lambda x: x['timestamp'],
                    reverse=True
                )[:5]
                
                return {
                    'active': is_active,
                    'allocation': allocation,
                    'trade_count': trade_count,
                    'total_profit': total_profit,
                    'recent_trades': recent_trades
                }
            else:
                return {
                    'active': False,
                    'error': 'No active trading session'
                }
        else:
            # Get global system status
            return {
                'system_paused': _system_paused,
                'active_users': len(_active_trades),
                'total_allocation': sum(data['allocation'] for data in _active_trades.values()) if _active_trades else 0
            }
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        return {'error': str(e)}

def get_system_stats():
    """
    Get overall system statistics
    
    Returns:
        dict: System statistics
    """
    try:
        # Count active traders
        active_traders = sum(1 for user_id, status in _trading_status.items() 
                           if status and not _system_paused)
        
        # Calculate total allocation
        total_allocation = sum(data['allocation'] for data in _active_trades.values()) if _active_trades else 0
        
        # Calculate total trades and profit
        total_trades = 0
        total_profit = 0
        
        for data in _active_trades.values():
            total_trades += len(data['trades'])
            total_profit += sum(trade['profit'] for trade in data['trades'])
        
        # Calculate success rate
        if total_trades > 0:
            successful_trades = sum(1 for data in _active_trades.values() 
                                 for trade in data['trades'] 
                                 if trade['roi_percentage'] > 0)
            success_rate = (successful_trades / total_trades) * 100
        else:
            success_rate = 0
        
        return {
            'active_traders': active_traders,
            'total_traders': len(_active_trades),
            'total_allocation': total_allocation,
            'total_trades': total_trades,
            'total_profit': total_profit,
            'success_rate': success_rate,
            'system_status': 'Active' if not _system_paused else 'Paused'
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {'error': str(e)}

def get_trading_stats():
    """
    Get trading performance statistics
    
    Returns:
        dict: Trading statistics
    """
    try:
        # Prepare stats
        stats = {
            'daily': {'trades': 0, 'profit': 0, 'success_rate': 0},
            'weekly': {'trades': 0, 'profit': 0, 'success_rate': 0},
            'monthly': {'trades': 0, 'profit': 0, 'success_rate': 0}
        }
        
        # Get current time for filtering
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Count by time period
        for user_data in _active_trades.values():
            for trade in user_data['trades']:
                timestamp = trade['timestamp']
                
                # Daily
                if timestamp >= day_ago:
                    stats['daily']['trades'] += 1
                    stats['daily']['profit'] += trade['profit']
                    if trade['roi_percentage'] > 0:
                        stats['daily']['success_rate'] += 1
                
                # Weekly
                if timestamp >= week_ago:
                    stats['weekly']['trades'] += 1
                    stats['weekly']['profit'] += trade['profit']
                    if trade['roi_percentage'] > 0:
                        stats['weekly']['success_rate'] += 1
                
                # Monthly
                if timestamp >= month_ago:
                    stats['monthly']['trades'] += 1
                    stats['monthly']['profit'] += trade['profit']
                    if trade['roi_percentage'] > 0:
                        stats['monthly']['success_rate'] += 1
        
        # Calculate success rates
        for period in stats:
            if stats[period]['trades'] > 0:
                stats[period]['success_rate'] = (stats[period]['success_rate'] / stats[period]['trades']) * 100
        
        return stats
    except Exception as e:
        logger.error(f"Error getting trading stats: {e}")
        return {'error': str(e)}