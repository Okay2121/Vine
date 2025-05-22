"""
Performance UI Preview Tool
--------------------------
This tool demonstrates how the new performance UI looks in Telegram
"""

from telegram_compact_performance import format_compact_performance

def display_sample_dashboard():
    """Display a sample dashboard with realistic data"""
    # Sample data that resembles real trading activity
    dashboard = format_compact_performance(
        # Balance details
        initial_deposit=10.0,
        current_balance=14.5,
        
        # Today's stats
        today_profit=1.2,
        today_percentage=12.0,
        
        # Overall stats
        total_profit=4.5,
        total_percentage=45.0,
        
        # Streak information
        streak_days=3,
        
        # Cycle information
        current_day=8,
        total_days=30,
        
        # Milestone progress
        milestone_target=10.0,
        milestone_current=4.5,
        
        # Goal tracking
        goal_target=20.0,
        
        # Recent activity
        recent_trades=[
            {"token": "BONK", "time_ago": "1h"},
            {"token": "WIF", "time_ago": "3h"},
            {"token": "SAMO", "time_ago": "6h"}
        ]
    )
    
    print("\n" + "=" * 50)
    print("TELEGRAM PERFORMANCE DASHBOARD PREVIEW")
    print("=" * 50)
    print("\nThis is how the dashboard will appear in Telegram:")
    print("\n" + "-" * 50 + "\n")
    
    # Display the formatted dashboard
    print(dashboard)
    
    print("\n" + "-" * 50)
    print("Note: In Telegram, this will be properly formatted with Markdown.")

if __name__ == "__main__":
    display_sample_dashboard()