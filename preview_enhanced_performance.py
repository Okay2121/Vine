"""
Preview of Enhanced Performance Dashboard
This script will print a sample of the enhanced performance dashboard design
with your current data values
"""

def preview_enhanced_dashboard(
    user_initial_deposit=0.00,
    current_balance=3.30,
    total_profit_amount=0.00,
    total_profit_percentage=0.0,
    today_profit_amount=0.00,
    today_profit_percentage=0.0,
    yesterday_balance=3.30,
    streak=0,
    days_active=1,
    milestone_target=0.05,
    milestone_progress=0,
    profitable_trades=0,
    loss_trades=0
):
    """Generate and display a preview of the enhanced dashboard"""
    
    # Build a visually stunning and user-friendly performance dashboard
    performance_message = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
    
    # Balance section - highlight the important numbers
    performance_message += "💰 *BALANCE*\n"
    performance_message += f"Initial: {user_initial_deposit:.2f} SOL\n"
    performance_message += f"Current: {current_balance:.2f} SOL\n"
    performance_message += f"Profit: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)\n\n"
    
    # Today's profit - emphasized and eye-catching
    performance_message += "📈 *TODAY'S PERFORMANCE*\n"
    if today_profit_amount > 0:
        performance_message += f"Profit: +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)\n"
        daily_goal_progress = 0  # Example value
        daily_blocks = int(min(10, daily_goal_progress / 10))
        daily_bar = f"{'█' * daily_blocks}{'░' * (10 - daily_blocks)} {daily_goal_progress:.0f}% of target\n\n"
        performance_message += f"{daily_bar}"
    else:
        performance_message += "No profit recorded yet today\n"
        performance_message += f"Starting: {yesterday_balance:.2f} SOL\n\n"
    
    # Profit streak - motivational and prominent
    performance_message += "🔥 *WINNING STREAK*\n"
    if streak > 0:
        streak_emoji = "🔥" if streak >= 3 else "✨"
        performance_message += f"{streak_emoji} {streak} day{'s' if streak > 1 else ''} in a row!\n"
        if streak >= 5:
            performance_message += "Incredible winning streak! Keep it up! 🏆\n\n"
        else:
            performance_message += "You're on fire! Keep building momentum! 💪\n\n"
    else:
        performance_message += "Start your streak today with your first profit!\n\n"
    
    # Cycle progress - clean and visual
    performance_message += "⏱️ *TRADING CYCLE*\n"
    performance_message += f"Day {days_active} of 30\n"
    cycle_percentage = (days_active / 30) * 100
    cycle_blocks = int(min(10, cycle_percentage / 10))
    cycle_bar = f"{'█' * cycle_blocks}{'░' * (10 - cycle_blocks)} {cycle_percentage:.0f}% complete\n\n"
    performance_message += f"{cycle_bar}"
    
    # Milestone progress - visual and motivational
    performance_message += "🏁 *NEXT MILESTONE*\n"
    milestone_profit_target = milestone_target
    performance_message += f"Target: +{milestone_profit_target:.2f} SOL\n"
    performance_message += f"Current: +{total_profit_amount:.2f} SOL\n"
    milestone_blocks = int(min(10, milestone_progress / 10))
    milestone_bar = f"{'█' * milestone_blocks}{'░' * (10 - milestone_blocks)} {milestone_progress:.0f}% progress\n\n"
    performance_message += f"{milestone_bar}"
    
    # Goal tracker - clear progress visualization
    performance_message += "🎯 *GOAL TRACKER*\n"
    goal_target = user_initial_deposit + milestone_target
    performance_message += f"Target: {goal_target:.2f} SOL\n"
    performance_message += f"Current: {current_balance:.2f} SOL\n"
    goal_progress = min(100, (current_balance / goal_target * 100)) if goal_target > 0 else 0
    goal_blocks = int(min(10, goal_progress / 10))
    goal_bar = f"{'█' * goal_blocks}{'░' * (10 - goal_blocks)} {goal_progress:.0f}% complete\n\n"
    performance_message += f"{goal_bar}"
    
    # Trading stats - clean and informative
    performance_message += "📊 *TRADING STATS*\n"
    performance_message += f"✅ Wins: {profitable_trades}\n"
    performance_message += f"❌ Losses: {loss_trades}\n"
    total_trades = profitable_trades + loss_trades
    win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
    
    if total_trades > 0:
        performance_message += f"Win rate: {win_rate:.0f}%\n\n"
        if win_rate >= 50:
            performance_message += "Your auto-trading strategy is profitable today! 📈\n"
        else:
            performance_message += "Market conditions are challenging, but the bot is adapting. 🔄\n"
    else:
        performance_message += "No trades completed today\n"
    
    return performance_message


if __name__ == "__main__":
    # Use your actual current values
    dashboard = preview_enhanced_dashboard(
        user_initial_deposit=0.00,
        current_balance=3.30,
        total_profit_amount=0.00,
        total_profit_percentage=0.0,
        today_profit_amount=0.00,
        today_profit_percentage=0.0,
        yesterday_balance=3.30,
        streak=0,
        days_active=1,
        milestone_target=0.05,
        milestone_progress=0,
        profitable_trades=0,
        loss_trades=0
    )
    
    print("\n" + "=" * 60)
    print("ENHANCED PERFORMANCE DASHBOARD PREVIEW")
    print("=" * 60)
    print("\nThis is how your new dashboard will look in Telegram:\n")
    print(dashboard)
    print("\nNote: In Telegram, this will be properly formatted with Markdown styling.")