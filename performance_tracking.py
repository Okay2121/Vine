"""
Performance Tracking Module
--------------------------
Models and utilities for tracking user performance metrics and trading history
"""

from datetime import datetime, timedelta
from app import db
from models import User, Profit, Transaction, TradingPosition, MilestoneTracker, UserMetrics, DailySnapshot

# DailySnapshot class moved to models.py to avoid duplicate table definition


class TradeLog(db.Model):
    """Detailed log of each individual trade"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token_name = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(10), nullable=False)  # buy, sell
    amount = db.Column(db.Float, nullable=False)  # SOL amount
    token_amount = db.Column(db.Float, nullable=True)  # Amount of tokens
    price = db.Column(db.Float, nullable=False)  # Price in SOL
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    profit_loss = db.Column(db.Float, nullable=True)  # For sell transactions
    percentage = db.Column(db.Float, nullable=True)  # Profit/loss percentage
    
    def __repr__(self):
        return f'<TradeLog {self.action} {self.token_name} {self.amount} SOL>'


# =================================================================
# Performance Tracking Logic
# =================================================================

def ensure_daily_snapshot(user_id):
    """
    Ensure a daily snapshot exists for the user on the current date.
    If it doesn't exist, create one with the current balance as starting balance.
    
    Args:
        user_id (int): User ID
        
    Returns:
        DailySnapshot: The daily snapshot for today
    """
    today = datetime.utcnow().date()
    
    # Check if snapshot already exists for today
    snapshot = DailySnapshot.query.filter_by(
        user_id=user_id,
        date=today
    ).first()
    
    if not snapshot:
        # Create new snapshot with current balance as starting balance
        user = User.query.get(user_id)
        if not user:
            return None
            
        snapshot = DailySnapshot()
        snapshot.user_id = user_id
        snapshot.date = today
        snapshot.starting_balance = user.balance
        snapshot.trades_count = 0
        snapshot.winning_trades = 0
        
        db.session.add(snapshot)
        db.session.commit()
    
    return snapshot


def update_daily_snapshot(user_id, trade_profit=None, is_winning=None):
    """
    Update the daily snapshot with current information.
    
    Args:
        user_id (int): User ID
        trade_profit (float, optional): Profit from a new trade
        is_winning (bool, optional): Whether the trade was winning
        
    Returns:
        DailySnapshot: The updated daily snapshot
    """
    snapshot = ensure_daily_snapshot(user_id)
    if not snapshot:
        return None
        
    user = User.query.get(user_id)
    if not user:
        return None
    
    # Update ending balance
    snapshot.ending_balance = user.balance
    
    # Calculate profit amount and percentage
    if snapshot.starting_balance > 0:
        snapshot.profit_amount = snapshot.ending_balance - snapshot.starting_balance
        snapshot.profit_percentage = (snapshot.profit_amount / snapshot.starting_balance) * 100
    else:
        snapshot.profit_amount = 0
        snapshot.profit_percentage = 0
    
    # Update trade counts if a trade occurred
    if trade_profit is not None:
        snapshot.trades_count += 1
        if is_winning:
            snapshot.winning_trades += 1
    
    db.session.commit()
    return snapshot


def end_of_day_processing(user_id):
    """
    Process end-of-day calculations and updates for a user
    
    Args:
        user_id (int): User ID
        
    Returns:
        bool: Whether processing was successful
    """
    try:
        snapshot = ensure_daily_snapshot(user_id)
        if not snapshot:
            return False
            
        user = User.query.get(user_id)
        if not user:
            return False
        
        # Update ending balance and calculate profit
        snapshot.ending_balance = user.balance
        snapshot.profit_amount = snapshot.ending_balance - snapshot.starting_balance
        
        if snapshot.starting_balance > 0:
            snapshot.profit_percentage = (snapshot.profit_amount / snapshot.starting_balance) * 100
        else:
            snapshot.profit_percentage = 0
        
        # Create profit record for the day if profit exists
        if snapshot.profit_amount != 0:
            daily_profit = Profit()
            daily_profit.user_id = user_id
            daily_profit.amount = snapshot.profit_amount
            daily_profit.percentage = snapshot.profit_percentage
            daily_profit.date = snapshot.date
            db.session.add(daily_profit)
        
        # Update streak information
        update_streak(user_id, snapshot.profit_amount > 0)
        
        # Update milestone progress
        update_milestone_progress(user_id)
        
        # Update goal progress
        update_goal_progress(user_id)
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in end_of_day_processing: {e}")
        return False


def update_streak(user_id, is_profitable_day):
    """
    Update the user's streak based on daily profit
    
    Args:
        user_id (int): User ID
        is_profitable_day (bool): Whether today was profitable
        
    Returns:
        int: The updated streak count
    """
    # Get or create user metrics
    metrics = UserMetrics.query.filter_by(user_id=user_id).first()
    if not metrics:
        metrics = UserMetrics()
        metrics.user_id = user_id
        metrics.current_streak = 0
        metrics.best_streak = 0
        db.session.add(metrics)
    
    today = datetime.utcnow().date()
    
    # Check if this is a new day
    if metrics.last_streak_update != today:
        if is_profitable_day:
            # Increment streak for profitable day
            metrics.current_streak += 1
            # Update best streak if current is better
            if metrics.current_streak > metrics.best_streak:
                metrics.best_streak = metrics.current_streak
        else:
            # Reset streak on non-profitable day
            metrics.current_streak = 0
        
        metrics.last_streak_update = today
        db.session.commit()
    
    return metrics.current_streak


def update_milestone_progress(user_id):
    """
    Update the user's progress toward the next milestone
    
    Args:
        user_id (int): User ID
        
    Returns:
        float: The updated milestone progress percentage
    """
    user = User.query.get(user_id)
    if not user:
        return 0
    
    # Get or create user metrics
    metrics = UserMetrics.query.filter_by(user_id=user_id).first()
    if not metrics:
        metrics = UserMetrics()
        metrics.user_id = user_id
        db.session.add(metrics)
    
    # Set next milestone if not set (10% of initial deposit or minimum 0.05 SOL)
    if not metrics.next_milestone:
        metrics.next_milestone = max(user.initial_deposit * 0.1, 0.05)
    
    # Calculate profit
    profit = user.balance - user.initial_deposit
    
    # Calculate progress percentage (capped at 100%)
    if metrics.next_milestone > 0:
        metrics.milestone_progress = min(100, (profit / metrics.next_milestone) * 100)
    else:
        metrics.milestone_progress = 0
    
    # If milestone reached, set a new one
    if profit >= metrics.next_milestone:
        # Increase by another 10% of initial deposit
        metrics.next_milestone = profit + max(user.initial_deposit * 0.1, 0.05)
        
        # Record milestone achievement
        milestone = MilestoneTracker()
        milestone.user_id = user_id
        milestone.milestone_type = 'profit_amount'
        milestone.value = profit
        milestone.acknowledged = False
        db.session.add(milestone)
    
    db.session.commit()
    return metrics.milestone_progress


def update_goal_progress(user_id):
    """
    Update the user's progress toward their goal
    
    Args:
        user_id (int): User ID
        
    Returns:
        float: The updated goal progress percentage
    """
    user = User.query.get(user_id)
    if not user:
        return 0
    
    # Get or create user metrics
    metrics = UserMetrics.query.filter_by(user_id=user_id).first()
    if not metrics:
        metrics = UserMetrics()
        metrics.user_id = user_id
        db.session.add(metrics)
    
    # Set goal if not set (2x initial deposit)
    if not metrics.current_goal:
        metrics.current_goal = user.initial_deposit * 2
    
    # Calculate progress percentage (capped at 100%)
    if metrics.current_goal > 0:
        metrics.goal_progress = min(100, (user.balance / metrics.current_goal) * 100)
    else:
        metrics.goal_progress = 0
    
    # If goal reached, set a new one
    if user.balance >= metrics.current_goal:
        # Double the goal
        metrics.current_goal = user.balance * 2
        
        # Record goal achievement
        milestone = MilestoneTracker()
        milestone.user_id = user_id
        milestone.milestone_type = 'goal_reached'
        milestone.value = user.balance
        milestone.acknowledged = False
        db.session.add(milestone)
    
    db.session.commit()
    return metrics.goal_progress


def get_recent_trades(user_id, limit=5):
    """
    Get recent trades for a user
    
    Args:
        user_id (int): User ID
        limit (int): Maximum number of trades to return
        
    Returns:
        list: List of recent trade information
    """
    # Get recent buy/sell transactions
    transactions = Transaction.query.filter_by(
        user_id=user_id
    ).filter(
        Transaction.transaction_type.in_(['buy', 'sell'])
    ).order_by(
        Transaction.timestamp.desc()
    ).limit(limit).all()
    
    # Format transaction information
    recent_trades = []
    for tx in transactions:
        # Determine how long ago the trade was
        time_ago = datetime.utcnow() - tx.timestamp
        if time_ago.days > 0:
            time_str = f"{time_ago.days}d"
        elif time_ago.seconds >= 3600:
            time_str = f"{time_ago.seconds // 3600}h"
        else:
            time_str = f"{time_ago.seconds // 60}m"
        
        recent_trades.append({
            "token": tx.token_name or "Unknown",
            "time_ago": time_str,
            "action": "buy" if tx.transaction_type == 'buy' else 'sell',
            "amount": abs(tx.amount)
        })
    
    return recent_trades


def get_performance_data(user_id):
    """
    Get comprehensive performance data for a user
    
    Args:
        user_id (int): User ID
        
    Returns:
        dict: Performance data
    """
    user = User.query.get(user_id)
    if not user:
        return None
    
    # Ensure metrics exist
    metrics = UserMetrics.query.filter_by(user_id=user_id).first()
    if not metrics:
        metrics = UserMetrics()
        metrics.user_id = user_id
        db.session.add(metrics)
        db.session.commit()
    
    # Ensure daily snapshot exists
    snapshot = ensure_daily_snapshot(user_id)
    
    # Calculate days active (capped at 30)
    days_active = min(30, (datetime.utcnow().date() - user.created_at.date()).days + 1) if hasattr(user, 'created_at') else 1
    
    # Get today's P/L - sum all profits/losses for today to accumulate throughout the day
    from sqlalchemy import func
    today = datetime.utcnow().date()
    
    # Sum all profit amounts for today from Profit table
    today_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(
        user_id=user_id,
        date=today
    ).scalar() or 0
    
    # Also check Transaction table for all trade-related entries today
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get all trade profits (positive amounts)
    today_transaction_profits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == 'trade_profit',
        Transaction.timestamp >= today_start,
        Transaction.timestamp <= today_end,
        Transaction.status == 'completed'
    ).scalar() or 0
    
    # Get all trade losses (negative amounts or separate loss transactions)
    today_transaction_losses = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == 'trade_loss',
        Transaction.timestamp >= today_start,
        Transaction.timestamp <= today_end,
        Transaction.status == 'completed'
    ).scalar() or 0
    
    # Calculate net transaction amount (profits minus losses)
    net_transaction_amount = today_transaction_profits - abs(today_transaction_losses)
    
    # Use the net transaction amount as it properly accounts for all profits and losses
    # Don't use max() as it prevents negative values (losses) from being shown
    if abs(net_transaction_amount) > abs(today_profit_amount):
        today_profit_amount = net_transaction_amount
    else:
        # If Profit table has data, still subtract losses from it
        today_profit_amount = today_profit_amount - abs(today_transaction_losses)
    
    # Calculate today's percentage based on starting balance for today, not current balance
    # This ensures losses are properly reflected as negative percentages
    starting_balance_today = user.balance - today_profit_amount
    if starting_balance_today > 0:
        today_profit_percentage = (today_profit_amount / starting_balance_today) * 100
    else:
        today_profit_percentage = 0
    
    # Calculate total profit
    profit_amount = user.balance - user.initial_deposit
    profit_percentage = (profit_amount / user.initial_deposit * 100) if user.initial_deposit > 0 else 0
    
    # Get recent trades
    recent_trades = get_recent_trades(user_id)
    
    # Compile all data
    performance_data = {
        # Balance details
        "initial_deposit": user.initial_deposit,
        "current_balance": user.balance,
        
        # Today's stats
        "today_profit": today_profit_amount,
        "today_percentage": today_profit_percentage,
        
        # Overall stats
        "total_profit": profit_amount,
        "total_percentage": profit_percentage,
        
        # Streak information
        "streak_days": metrics.current_streak,
        "best_streak": metrics.best_streak,
        
        # Cycle information
        "current_day": days_active,
        "total_days": 30,
        
        # Milestone progress
        "milestone_target": metrics.next_milestone or 0,
        "milestone_current": profit_amount if profit_amount > 0 else 0,
        "milestone_progress": metrics.milestone_progress,
        
        # Goal tracking
        "goal_target": metrics.current_goal or 0,
        "goal_current": user.balance,
        "goal_progress": metrics.goal_progress,
        
        # Trading mode
        "trading_mode": metrics.trading_mode,
        
        # Recent activity
        "recent_trades": recent_trades
    }
    
    return performance_data