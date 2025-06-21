"""
Fix Streak Calculation for Users
================================
Updates UserMetrics table with correct streak calculations based on actual profit data
"""

from app import app, db
from models import User, Profit, UserMetrics
from datetime import datetime, timedelta
from sqlalchemy import func

def calculate_and_update_streak(user_id):
    """Calculate and update the correct streak for a user"""
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User {user_id} not found")
            return
        
        # Get or create UserMetrics
        metrics = UserMetrics.query.filter_by(user_id=user_id).first()
        if not metrics:
            metrics = UserMetrics()
            metrics.user_id = user_id
            db.session.add(metrics)
        
        # Calculate streak manually
        current_date = datetime.utcnow().date()
        streak = 0
        
        print(f"Calculating streak for User {user_id}...")
        
        # Check up to 30 days back
        for i in range(30):
            check_date = current_date - timedelta(days=i)
            
            # Get profits for this date
            day_profits = db.session.query(func.sum(Profit.amount)).filter_by(
                user_id=user_id, 
                date=check_date
            ).scalar() or 0
            
            print(f"  Date {check_date}: {day_profits:.4f} SOL profit")
            
            if day_profits > 0:
                if i == 0 or streak > 0:  # Today or continuing streak
                    streak += 1
                    print(f"    -> Streak continues: {streak} days")
                else:
                    break
            else:
                if i == 0:
                    print(f"    -> No profit today, streak stays at {streak}")
                else:
                    print(f"    -> No profit, breaking streak at {streak} days")
                    break
        
        # Update metrics
        old_streak = metrics.current_streak
        metrics.current_streak = streak
        metrics.last_streak_update = current_date
        
        # Update best streak if needed
        if streak > metrics.best_streak:
            metrics.best_streak = streak
        
        app.db.session.commit()
        
        print(f"Updated streak: {old_streak} -> {streak} days")
        print(f"Best streak: {metrics.best_streak} days")
        
        return streak

def fix_all_user_streaks():
    """Fix streaks for all users with profit data"""
    with app.app_context():
        # Get all users who have profit records
        users_with_profits = db.session.query(Profit.user_id).distinct().all()
        
        print(f"Found {len(users_with_profits)} users with profit records")
        
        for (user_id,) in users_with_profits:
            calculate_and_update_streak(user_id)
            print("-" * 50)

if __name__ == "__main__":
    print("Fixing streak calculations...")
    fix_all_user_streaks()
    print("Done!")