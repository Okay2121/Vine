"""
Telegram Dashboard Generator
---------------------------
Connects performance tracking data to Telegram-formatted UI messages
"""

from datetime import datetime
from performance_tracking import get_performance_data
from telegram_compact_performance import format_compact_performance

def generate_performance_dashboard(user_id):
    """
    Generate a complete performance dashboard for a Telegram user
    
    This function connects real user data to the Telegram UI format
    
    Args:
        user_id (int): Database user ID
        
    Returns:
        str: Formatted Telegram message (markdown)
    """
    # Get all performance data from tracking system
    performance_data = get_performance_data(user_id)
    
    if not performance_data:
        return "⚠️ *Performance data unavailable*\nPlease try again later."
    
    # Format recent trades for display
    recent_trades = []
    for trade in performance_data['recent_trades']:
        recent_trades.append({
            "token": trade['token'],
            "time_ago": trade['time_ago']
        })
    
    # Generate formatted dashboard using the compact performance formatter
    dashboard = format_compact_performance(
        # Balance details
        initial_deposit=performance_data['initial_deposit'],
        current_balance=performance_data['current_balance'],
        
        # Today's stats
        today_profit=performance_data['today_profit'],
        today_percentage=performance_data['today_percentage'],
        
        # Overall stats
        total_profit=performance_data['total_profit'],
        total_percentage=performance_data['total_percentage'],
        
        # Streak information
        streak_days=performance_data['streak_days'],
        
        # Cycle information
        current_day=performance_data['current_day'],
        total_days=performance_data['total_days'],
        
        # Milestone progress
        milestone_target=performance_data['milestone_target'],
        milestone_current=performance_data['milestone_current'],
        
        # Goal tracking
        goal_target=performance_data['goal_target'],
        
        # Recent activity
        recent_trades=recent_trades
    )
    
    # Add trading mode information at the bottom
    trading_mode = performance_data['trading_mode']
    mode_display = f"🤖 *Mode: {trading_mode.upper()}*"
    
    # Return complete dashboard
    return f"{dashboard}\n{mode_display}"


def refresh_user_data(user_id, trade_completed=False, is_winning=None):
    """
    Refresh user performance data after events
    
    Args:
        user_id (int): Database user ID
        trade_completed (bool): Whether a trade was completed
        is_winning (bool): Whether the trade was winning
        
    Returns:
        bool: Success
    """
    from performance_tracking import (
        update_daily_snapshot,
        update_streak,
        update_milestone_progress,
        update_goal_progress
    )
    
    try:
        # Update daily snapshot with new trade info if applicable
        if trade_completed:
            update_daily_snapshot(user_id, trade_profit=is_winning, is_winning=is_winning)
        else:
            update_daily_snapshot(user_id)
        
        # Update other metrics
        update_streak(user_id, is_winning if trade_completed else None)
        update_milestone_progress(user_id)
        update_goal_progress(user_id)
        
        return True
    except Exception as e:
        print(f"Error refreshing user data: {e}")
        return False


def schedule_daily_reset():
    """
    Schedule the daily reset job to run at midnight UTC
    
    This should be called when the application starts
    """
    import schedule
    from performance_tracking import end_of_day_processing
    from models import User
    
    def daily_reset_job():
        """Process end-of-day calculations for all users"""
        # Get all active users
        users = User.query.all()
        for user in users:
            end_of_day_processing(user.id)
    
    # Schedule the job to run at midnight UTC
    schedule.every().day.at("00:00").do(daily_reset_job)
    
    print("Daily reset job scheduled")


# ====================================================
# Telegram Bot Command Handlers
# ====================================================

async def dashboard_command_handler(update, context):
    """
    Handle the /dashboard command
    
    This shows the performance dashboard to the user
    """
    from models import User
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Find the user in the database
    db_user = User.query.filter_by(telegram_id=str(user.id)).first()
    if not db_user:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Please start the bot with /start first."
        )
        return
    
    # Refresh the user's data
    refresh_user_data(db_user.id)
    
    # Generate and send the dashboard
    dashboard = generate_performance_dashboard(db_user.id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=dashboard,
        parse_mode="Markdown"
    )


# When trade is completed, call this function
def on_trade_completed(user_id, profit_amount, token_name):
    """
    Handle trade completion event
    
    Args:
        user_id (int): Database user ID
        profit_amount (float): Profit amount (negative for losses)
        token_name (str): Name of the traded token
        
    Returns:
        bool: Success
    """
    # Refresh user data with trade information
    is_winning = profit_amount > 0
    return refresh_user_data(user_id, trade_completed=True, is_winning=is_winning)


# Scheduled job to refresh data periodically
def refresh_all_users_data():
    """Refresh data for all users"""
    from models import User
    
    users = User.query.all()
    for user in users:
        refresh_user_data(user.id)