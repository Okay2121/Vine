"""
Enhanced Performance UI
----------------------
A more visually striking and well-arranged performance dashboard
"""

def format_enhanced_performance(
    # Balance details
    initial_deposit=0.00,
    current_balance=3.30,
    
    # Today's stats
    today_profit=0.00,
    today_percentage=0.0,
    
    # Overall stats
    total_profit=0.00,
    total_percentage=0.0,
    
    # Streak information
    streak_days=0,
    
    # Cycle information
    current_day=1,
    total_days=30,
    
    # Milestone progress
    milestone_target=0.05,
    milestone_current=0.00,
    
    # Goal tracking
    goal_target=0.05,
    
    # Trading stats
    profitable_trades=0,
    loss_trades=0,
    
    # Recent activity
    recent_trades=None
):
    """
    Generate a beautifully formatted performance dashboard optimized for Telegram
    
    Returns:
        str: Markdown formatted performance dashboard
    """
    # Calculate derived values
    profit = current_balance - initial_deposit
    win_rate = (profitable_trades / (profitable_trades + loss_trades) * 100) if (profitable_trades + loss_trades) > 0 else 0
    
    # Progress percentages
    cycle_percentage = min(100, (current_day / total_days * 100))
    milestone_percentage = min(100, (milestone_current / milestone_target * 100)) if milestone_target > 0 else 0
    goal_percentage = min(100, (current_balance / goal_target * 100)) if goal_target > 0 else 0
    
    # Generate progress bars
    def generate_bar(percentage, length=10):
        filled = round(percentage / 100 * length)
        return '█' * filled + '░' * (length - filled)
    
    # Build the message with improved spacing and grouping
    msg = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
    
    # Balance section - highlight the important numbers
    msg += "💰 *BALANCE*\n"
    msg += f"Initial: {initial_deposit:.2f} SOL\n"
    msg += f"Current: {current_balance:.2f} SOL\n"
    msg += f"Profit: +{profit:.2f} SOL (+{total_percentage:.1f}%)\n\n"
    
    # Today's profit - emphasized and eye-catching
    msg += "📈 *TODAY'S PERFORMANCE*\n"
    if today_profit > 0:
        msg += f"Profit: +{today_profit:.2f} SOL (+{today_percentage:.1f}%)\n"
        today_bar = generate_bar(today_percentage)
        msg += f"{today_bar} {today_percentage:.0f}% of daily target\n\n"
    else:
        msg += "No profit recorded yet today\n"
        msg += f"Starting: {current_balance:.2f} SOL\n\n"
    
    # Profit streak - motivational and prominent
    msg += "🔥 *WINNING STREAK*\n"
    if streak_days > 0:
        streak_emoji = "🔥" if streak_days >= 3 else "✨"
        msg += f"{streak_emoji} {streak_days} day{'s' if streak_days > 1 else ''} in a row!\n\n"
    else:
        msg += "Start your streak today with your first profit!\n\n"
    
    # Cycle progress - clean and visual
    msg += "⏱️ *TRADING CYCLE*\n"
    msg += f"Day {current_day} of {total_days}\n"
    cycle_bar = generate_bar(cycle_percentage)
    msg += f"{cycle_bar} {cycle_percentage:.0f}% complete\n\n"
    
    # Milestone progress - visual and motivational
    msg += "🏁 *NEXT MILESTONE*\n"
    msg += f"Target: +{milestone_target:.2f} SOL\n"
    msg += f"Current: +{milestone_current:.2f} SOL\n"
    milestone_bar = generate_bar(milestone_percentage)
    msg += f"{milestone_bar} {milestone_percentage:.0f}% progress\n\n"
    
    # Goal tracker - clear progress visualization
    msg += "🎯 *GOAL TRACKER*\n"
    msg += f"Target: {goal_target:.2f} SOL\n"
    msg += f"Current: {current_balance:.2f} SOL\n"
    goal_bar = generate_bar(goal_percentage)
    msg += f"{goal_bar} {goal_percentage:.0f}% complete\n\n"
    
    # Trading stats - clean and informative
    msg += "📊 *TRADING STATS*\n"
    msg += f"✅ Wins: {profitable_trades}\n"
    msg += f"❌ Losses: {loss_trades}\n"
    
    if profitable_trades + loss_trades > 0:
        msg += f"Win rate: {win_rate:.0f}%\n\n"
    else:
        msg += "No trades completed today\n\n"
    
    # Recent activity - only if there are trades
    if recent_trades and len(recent_trades) > 0:
        msg += "⚡ *RECENT TRADES*\n"
        for trade in recent_trades:
            token = trade.get("token", "Unknown")
            time_ago = trade.get("time_ago", "recent")
            msg += f"● {token} · {time_ago} ago\n"
    
    return msg

# Example with realistic data
if __name__ == "__main__":
    sample = format_enhanced_performance(
        initial_deposit=0.00,
        current_balance=3.30,
        today_profit=0.00,
        today_percentage=0.0,
        total_profit=0.00,
        total_percentage=0.0,
        streak_days=0,
        current_day=1,
        total_days=30,
        milestone_target=0.05,
        milestone_current=0.00,
        goal_target=0.05,
        profitable_trades=0,
        loss_trades=0,
        recent_trades=[
            {"token": "BONK", "time_ago": "2h"},
            {"token": "WIF", "time_ago": "5h"}
        ]
    )
    
    print("\n" + "=" * 50)
    print("ENHANCED PERFORMANCE DASHBOARD")
    print("=" * 50)
    print("\n" + sample)