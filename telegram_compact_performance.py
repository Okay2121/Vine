"""
Telegram Compact Performance Display
-----------------------------------
A visually stunning and compact performance dashboard specifically formatted for Telegram chat.
This module provides a single function to generate beautifully formatted performance messages.
"""

def format_compact_performance(
    # Balance details
    initial_deposit=10.0,
    current_balance=15.0,
    
    # Today's stats
    today_profit=1.2,
    today_percentage=12.0,
    
    # Overall stats
    total_profit=5.0,
    total_percentage=50.0,
    
    # Streak information
    streak_days=3,
    
    # Cycle information
    current_day=8,
    total_days=30,
    
    # Milestone progress
    milestone_target=10.0,
    milestone_current=5.0,
    
    # Goal tracking
    goal_target=20.0,
    
    # Recent activity
    recent_trades=None
):
    """
    Generate a compact, visually stunning performance dashboard for Telegram
    
    All parameters are optional and will be filled with sample data if not provided
    
    Returns:
        str: Beautifully formatted string for Telegram (using markdown formatting)
    """
    if recent_trades is None:
        recent_trades = [
            {"token": "BONK", "time_ago": "1h"},
            {"token": "WIF", "time_ago": "3h"}
        ]
    
    # Calculate derived values
    profit = current_balance - initial_deposit
    remaining_days = total_days - current_day
    
    # Progress percentages
    cycle_percentage = min(100, (current_day / total_days * 100))
    milestone_percentage = min(100, (milestone_current / milestone_target * 100)) if milestone_target > 0 else 0
    goal_percentage = min(100, (current_balance / goal_target * 100)) if goal_target > 0 else 0
    
    # Create progress bars
    def generate_bar(percentage, length=10):
        filled = round(percentage / 100 * length)
        return '█' * filled + '░' * (length - filled)
    
    # Build the message with careful spacing and grouping
    msg = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
    
    # Balance section - clean and minimal
    msg += f"💰 *{initial_deposit:.2f} + {profit:.2f} = {current_balance:.2f} SOL*\n\n"
    
    # Today's profit - highlighted and prominent
    msg += f"📈 *TODAY: +{today_profit:.2f} SOL (+{today_percentage:.1f}%)*\n\n"
    
    # Total profit - clear and motivational
    msg += f"💎 *TOTAL: +{total_profit:.2f} SOL (+{total_percentage:.1f}%)*\n\n"
    
    # Profit streak - if exists, make it exciting
    if streak_days > 0:
        streak_emoji = "🔥" if streak_days >= 3 else "✨"
        msg += f"{streak_emoji} *{streak_days} DAY {'STREAK' if streak_days > 1 else 'WIN'}!*\n\n"
    
    # Cycle progress - countdown feel
    msg += f"⏱️ *DAY {current_day}/{total_days}* · {remaining_days} days left\n"
    cycle_bar = generate_bar(cycle_percentage)
    msg += f"{cycle_bar} {cycle_percentage:.0f}%\n\n"
    
    # Milestone progress - visual progress bar
    msg += f"🏁 *MILESTONE: {milestone_current:.2f}/{milestone_target:.2f} SOL*\n"
    milestone_bar = generate_bar(milestone_percentage)
    msg += f"{milestone_bar} {milestone_percentage:.0f}%\n\n"
    
    # Goal tracker - clear visual of progress
    msg += f"🎯 *GOAL: {current_balance:.2f}/{goal_target:.2f} SOL*\n"
    goal_bar = generate_bar(goal_percentage)
    msg += f"{goal_bar} {goal_percentage:.0f}%\n\n"
    
    # Recent activity - live trading feel
    msg += "⚡ *RECENT TRADES:*\n"
    for trade in recent_trades:
        msg += f"● {trade['token']} · {trade['time_ago']} ago\n"
    
    return msg

# Example usage
if __name__ == "__main__":
    # Example data to demonstrate the formatting
    example = format_compact_performance(
        initial_deposit=10.0,
        current_balance=14.5,
        today_profit=1.2,
        today_percentage=12.0,
        total_profit=4.5,
        total_percentage=45.0,
        streak_days=3,
        current_day=8,
        total_days=30,
        milestone_target=10.0,
        milestone_current=4.5,
        goal_target=20.0,
        recent_trades=[
            {"token": "BONK", "time_ago": "1h"},
            {"token": "WIF", "time_ago": "3h"}
        ]
    )
    
    print(example)