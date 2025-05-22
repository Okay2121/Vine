"""
Telegram Performance UI
-----------------------
A visually stunning and user-friendly Performance Page UI for the Solana Memecoin Trading Bot.
This module provides functions to generate elegantly formatted performance messages
for delivery in Telegram chat.
"""

from datetime import datetime, timedelta
import math
from models import User, Transaction, Profit, TradingPosition

def get_user_balance_breakdown(user_id):
    """Get user balance breakdown including initial deposit and profit"""
    user = User.query.get(user_id)
    if not user:
        return None
    
    # Calculate profit
    profit = user.balance - user.initial_deposit
    profit_percentage = (profit / user.initial_deposit * 100) if user.initial_deposit > 0 else 0
    
    return {
        'initial_deposit': user.initial_deposit,
        'current_balance': user.balance,
        'profit': profit,
        'profit_percentage': profit_percentage
    }

def get_daily_profit(user_id):
    """Get today's profit for a user"""
    today = datetime.utcnow().date()
    
    # Get profits for today
    today_profit = Profit.query.filter_by(
        user_id=user_id, 
        date=today
    ).all()
    
    total_amount = sum(p.amount for p in today_profit)
    avg_percentage = sum(p.percentage for p in today_profit) if today_profit else 0
    
    return {
        'amount': total_amount,
        'percentage': avg_percentage
    }

def get_total_profit(user_id):
    """Get total profit for a user"""
    user = User.query.get(user_id)
    if not user or user.initial_deposit == 0:
        return {'amount': 0, 'percentage': 0}
    
    profit_amount = user.balance - user.initial_deposit
    profit_percentage = (profit_amount / user.initial_deposit * 100)
    
    return {
        'amount': profit_amount,
        'percentage': profit_percentage
    }

def get_profit_streak(user_id):
    """Get the current profit streak (consecutive days with profit)"""
    # Get all profits ordered by date descending
    profits = Profit.query.filter_by(user_id=user_id).order_by(Profit.date.desc()).all()
    
    # Group by date to determine if each day was profitable
    profit_by_date = {}
    for profit in profits:
        date_str = profit.date.strftime('%Y-%m-%d')
        if date_str not in profit_by_date:
            profit_by_date[date_str] = 0
        profit_by_date[date_str] += profit.amount
    
    # Calculate streak
    streak = 0
    today = datetime.utcnow().date()
    
    for i in range(30):  # Check up to 30 days back
        check_date = today - timedelta(days=i)
        date_str = check_date.strftime('%Y-%m-%d')
        
        if date_str in profit_by_date and profit_by_date[date_str] > 0:
            streak += 1
        else:
            # Break on first non-profitable day
            break
    
    return streak

def get_cycle_progress(user_id):
    """Get progress in the 30-day trading cycle"""
    user = User.query.get(user_id)
    if not user:
        return {'day': 0, 'remaining': 30}
    
    # Calculate days since user started
    if not user.created_at:
        return {'day': 1, 'remaining': 29}
    
    days_active = (datetime.utcnow() - user.created_at).days + 1
    current_day = min(30, days_active)
    days_remaining = max(0, 30 - current_day)
    
    return {
        'day': current_day,
        'remaining': days_remaining,
        'percentage': (current_day / 30) * 100
    }

def get_milestone_progress(user_id):
    """Get progress toward the next milestone"""
    user = User.query.get(user_id)
    if not user or user.initial_deposit == 0:
        return {'progress': 0, 'target': 0, 'current': 0}
    
    # Set milestone target at 2x initial deposit
    milestone_target = user.initial_deposit
    profit = user.balance - user.initial_deposit
    
    progress_percentage = min(100, (profit / milestone_target * 100)) if milestone_target > 0 else 0
    
    return {
        'progress': progress_percentage,
        'target': milestone_target,
        'current': profit
    }

def get_goal_completion(user_id):
    """Get goal completion tracking"""
    user = User.query.get(user_id)
    if not user or user.initial_deposit == 0:
        return {'progress': 0, 'target': 0, 'current': 0}
    
    # Goal is set at 2x initial deposit (100% profit)
    goal_target = user.initial_deposit * 2
    
    progress_percentage = min(100, (user.balance / goal_target * 100)) if goal_target > 0 else 0
    
    return {
        'progress': progress_percentage,
        'target': goal_target,
        'current': user.balance
    }

def get_recent_trades(user_id, limit=3):
    """Get recent trade activity"""
    recent_trades = Transaction.query.filter_by(
        user_id=user_id,
        transaction_type='buy'
    ).order_by(Transaction.timestamp.desc()).limit(limit).all()
    
    trades_data = []
    for trade in recent_trades:
        trades_data.append({
            'token': trade.token_name,
            'amount': trade.amount,
            'timestamp': trade.timestamp
        })
    
    return trades_data

def generate_progress_bar(percentage, length=10):
    """Generate a visual progress bar using block characters"""
    filled_length = math.floor(percentage / 100 * length)
    empty_length = length - filled_length
    
    bar = '█' * filled_length + '░' * empty_length
    return bar

def format_performance_message(user_id):
    """
    Generate a beautifully formatted performance message for Telegram
    
    Returns a string formatted for Telegram Markdown
    """
    # Get all required data
    balance = get_user_balance_breakdown(user_id)
    daily_profit = get_daily_profit(user_id)
    total_profit = get_total_profit(user_id)
    streak = get_profit_streak(user_id)
    cycle = get_cycle_progress(user_id)
    milestone = get_milestone_progress(user_id)
    goal = get_goal_completion(user_id)
    recent_trades = get_recent_trades(user_id)
    
    if not balance:
        return "⚠️ *User data not found*"

    # Format the message
    message = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
    
    # Balance Section
    message += "💰 *BALANCE*\n"
    message += f"Initial: {balance['initial_deposit']:.3f} SOL\n"
    message += f"Profit: +{balance['profit']:.3f} SOL\n"
    message += f"Total: {balance['current_balance']:.3f} SOL\n\n"
    
    # Today's Profit
    message += "📈 *TODAY'S PROFIT*\n"
    message += f"+{daily_profit['amount']:.3f} SOL (+{daily_profit['percentage']:.1f}%)\n\n"
    
    # Total Profit
    message += "💎 *TOTAL PROFIT*\n"
    message += f"+{total_profit['amount']:.3f} SOL (+{total_profit['percentage']:.1f}%)\n\n"
    
    # Profit Streak
    if streak > 0:
        message += "🔥 *PROFIT STREAK*\n"
        message += f"{streak} profitable {'days' if streak > 1 else 'day'} in a row!\n"
        if streak >= 7:
            message += "Incredible winning streak! 🏆\n"
        elif streak >= 3:
            message += "You're on fire! 🔥\n"
        else:
            message += "Keep it going! ✨\n"
        message += "\n"
    
    # Cycle Progress
    message += "⏱️ *TRADING CYCLE*\n"
    message += f"Day {cycle['day']} of 30 "
    message += f"({30 - cycle['day']} days remaining)\n"
    cycle_bar = generate_progress_bar(cycle['percentage'])
    message += f"{cycle_bar} {cycle['percentage']:.0f}%\n\n"
    
    # Milestone Progress
    message += "🏁 *MILESTONE PROGRESS*\n"
    message += f"Target: +{milestone['target']:.3f} SOL\n"
    message += f"Current: +{milestone['current']:.3f} SOL\n"
    milestone_bar = generate_progress_bar(milestone['progress'])
    message += f"{milestone_bar} {milestone['progress']:.0f}%\n\n"
    
    # Goal Tracker
    message += "🎯 *GOAL TRACKER*\n"
    message += f"Target: {goal['target']:.3f} SOL\n"
    message += f"Current: {goal['current']:.3f} SOL\n"
    goal_bar = generate_progress_bar(goal['progress'])
    message += f"{goal_bar} {goal['progress']:.0f}%\n"
    
    # Add motivational message based on progress
    if goal['progress'] >= 90:
        message += "Almost there! Final push! 💪\n\n"
    elif goal['progress'] >= 75:
        message += "Great progress! Getting closer! 🚀\n\n"
    elif goal['progress'] >= 50:
        message += "Halfway there! Keep going! 🔄\n\n"
    elif goal['progress'] >= 25:
        message += "Good start! Stay consistent! 📊\n\n"
    else:
        message += "Just getting started! Exciting journey ahead! ✨\n\n"
    
    # Recent Trading Activity
    message += "⚡ *RECENT ACTIVITY*\n"
    if recent_trades:
        for trade in recent_trades:
            time_ago = datetime.utcnow() - trade['timestamp']
            if time_ago.days > 0:
                time_str = f"{time_ago.days}d ago"
            elif time_ago.seconds >= 3600:
                time_str = f"{time_ago.seconds // 3600}h ago"
            else:
                time_str = f"{time_ago.seconds // 60}m ago"
            
            message += f"Bought {trade['token']} · {time_str}\n"
    else:
        message += "No recent trading activity\n"
    
    return message