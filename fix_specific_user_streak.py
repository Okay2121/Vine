#!/usr/bin/env python3
"""
Fix Specific User Streak Calculation
===================================
Updates the streak calculation for the user showing 0 days despite having profits
"""

from app import app, db
from models import User, UserMetrics, Profit
from datetime import datetime, timedelta

def calculate_and_update_streak(user_id):
    """Calculate and update streak for a specific user"""
    
    current_streak = 0
    current_date = datetime.utcnow().date()
    
    # Check consecutive days backwards from today
    consecutive = True
    for i in range(30):
        check_date = current_date - timedelta(days=i)
        
        # Check if user had profit on this date
        profit_record = Profit.query.filter_by(
            user_id=user_id,
            date=check_date
        ).first()
        
        profit_amount = profit_record.amount if profit_record else 0
        
        if profit_amount > 0 and consecutive:
            current_streak += 1
        elif profit_amount <= 0 and i > 0:  # Don't break on today
            consecutive = False
            break
    
    return current_streak

def fix_user_streak():
    """Fix the streak for the specific user"""
    
    with app.app_context():
        # Find user with telegram_id 7611754415
        user = User.query.filter_by(telegram_id='7611754415').first()
        if not user:
            print("User not found")
            return False
            
        print(f"Fixing streak for User ID {user.id}")
        print(f"Current balance: {user.balance:.6f} SOL")
        
        # Get or create UserMetrics
        metrics = UserMetrics.query.filter_by(user_id=user.id).first()
        if not metrics:
            metrics = UserMetrics()
            metrics.user_id = user.id
            metrics.trading_mode = 'autopilot'
            db.session.add(metrics)
        
        # Calculate new streak
        old_streak = metrics.current_streak
        new_streak = calculate_and_update_streak(user.id)
        
        # Update metrics
        metrics.current_streak = new_streak
        if new_streak > (metrics.best_streak or 0):
            metrics.best_streak = new_streak
        
        # Set milestone and goal if not set
        if not metrics.next_milestone and user.initial_deposit > 0:
            metrics.next_milestone = max(user.initial_deposit * 0.1, 0.05)
        
        if not metrics.current_goal and user.initial_deposit > 0:
            metrics.current_goal = user.initial_deposit * 2
        
        # Calculate progress
        if metrics.next_milestone and metrics.next_milestone > 0:
            profit = user.balance - user.initial_deposit
            metrics.milestone_progress = min(100, (profit / metrics.next_milestone) * 100)
        
        if metrics.current_goal and metrics.current_goal > 0:
            metrics.goal_progress = min(100, (user.balance / metrics.current_goal) * 100)
        
        db.session.commit()
        
        print(f"Updated streak: {old_streak} → {new_streak}")
        
        # Verify the fix
        from performance_tracking import get_performance_data
        perf_data = get_performance_data(user.id)
        if perf_data:
            print(f"Performance data now shows streak: {perf_data['streak_days']}")
            print(f"Today's profit: {perf_data['today_profit']:.6f} SOL")
            print(f"Total profit: {perf_data['total_profit']:.6f} SOL")
        
        return True

if __name__ == "__main__":
    success = fix_user_streak()
    if success:
        print("✅ User streak fixed successfully!")
    else:
        print("❌ Failed to fix user streak")