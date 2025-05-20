"""
ROI Tracker Service
Tracks Return on Investment and profit metrics for users
"""

import logging
from datetime import datetime, timedelta

# Import utilities
from utils.database import get_user_trades, get_user

logger = logging.getLogger(__name__)

async def get_user_roi(user_id, period='all'):
    """
    Calculate a user's ROI for the specified time period
    
    Args:
        user_id: The user's ID
        period: Time period ('day', 'week', 'month', 'all')
        
    Returns:
        dict: ROI statistics
    """
    try:
        # In a real implementation, this would fetch from the database
        # Mock data for demonstration
        trades = await get_user_trades(user_id)
        
        # Filter trades by period
        now = datetime.now()
        filtered_trades = []
        
        if period == 'day':
            cutoff = now - timedelta(days=1)
        elif period == 'week':
            cutoff = now - timedelta(days=7)
        elif period == 'month':
            cutoff = now - timedelta(days=30)
        else:  # 'all'
            cutoff = datetime.min
            
        filtered_trades = [trade for trade in trades if trade['timestamp'] >= cutoff]
        
        # Calculate ROI
        total_investment = sum(trade['amount'] for trade in filtered_trades)
        total_profit = sum(trade['profit'] for trade in filtered_trades)
        
        if total_investment > 0:
            roi_percentage = (total_profit / total_investment) * 100
        else:
            roi_percentage = 0
            
        # Calculate success rate
        total_trades = len(filtered_trades)
        successful_trades = sum(1 for trade in filtered_trades if trade['profit'] > 0)
        
        if total_trades > 0:
            success_rate = (successful_trades / total_trades) * 100
        else:
            success_rate = 0
            
        return {
            'period': period,
            'total_trades': total_trades,
            'total_investment': total_investment,
            'total_profit': total_profit,
            'roi_percentage': roi_percentage,
            'success_rate': success_rate
        }
    except Exception as e:
        logger.error(f"Error calculating ROI for user {user_id}: {e}")
        return {
            'period': period,
            'error': str(e)
        }

async def get_profit_history(user_id, limit=10):
    """
    Get a user's profit history
    
    Args:
        user_id: The user's ID
        limit: Maximum number of trades to return
        
    Returns:
        list: Trade history
    """
    try:
        # In a real implementation, this would fetch from the database
        # Mock data for demonstration
        trades = await get_user_trades(user_id)
        
        # Sort trades by timestamp (newest first) and limit
        sorted_trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        return sorted_trades
    except Exception as e:
        logger.error(f"Error getting profit history for user {user_id}: {e}")
        return []

async def get_performance_stats(user_id):
    """
    Get detailed performance statistics for a user
    
    Args:
        user_id: The user's ID
        
    Returns:
        dict: Performance statistics
    """
    try:
        # Get ROI statistics for different time periods
        daily_roi = await get_user_roi(user_id, 'day')
        weekly_roi = await get_user_roi(user_id, 'week')
        monthly_roi = await get_user_roi(user_id, 'month')
        all_time_roi = await get_user_roi(user_id, 'all')
        
        # Get user information
        user = await get_user(user_id)
        
        # Calculate profit streak (consecutive profitable days)
        streak = calculate_profit_streak(user_id)
        
        return {
            'user_id': user_id,
            'username': user.get('username', 'Unknown'),
            'balance': user.get('balance', 0),
            'daily': daily_roi,
            'weekly': weekly_roi,
            'monthly': monthly_roi,
            'all_time': all_time_roi,
            'profit_streak': streak
        }
    except Exception as e:
        logger.error(f"Error getting performance stats for user {user_id}: {e}")
        return {'error': str(e)}

def calculate_profit_streak(user_id):
    """
    Calculate a user's profit streak (consecutive days with profit)
    
    Args:
        user_id: The user's ID
        
    Returns:
        int: Number of consecutive days with profit
    """
    try:
        # In a real implementation, this would fetch from the database
        # and actually calculate the streak based on daily profits
        return 3  # Mock value for demonstration
    except Exception as e:
        logger.error(f"Error calculating profit streak for user {user_id}: {e}")
        return 0