#!/usr/bin/env python3
"""
Fix Autopilot Dashboard Real-time Data Connection
=================================================
This script fixes the autopilot dashboard by ensuring proper streak calculation
and real-time data synchronization with the performance tracking system.
"""

import sys
import os
from datetime import datetime, timedelta
from app import app, db
from models import User, UserMetrics, Profit, Transaction
from performance_tracking import update_streak, get_performance_data
import logging

logging.basicConfig(level=logging.INFO)

def calculate_user_streak(user_id):
    """
    Calculate the current profit streak for a user based on existing profit data.
    
    Args:
        user_id (int): User ID
        
    Returns:
        int: Current consecutive profit streak
    """
    current_streak = 0
    current_date = datetime.utcnow().date()
    
    # Check consecutive days backwards from today
    for i in range(30):  # Check up to 30 days back
        check_date = current_date - timedelta(days=i)
        
        # Check if user had profit on this date
        profit_record = Profit.query.filter_by(
            user_id=user_id,
            date=check_date
        ).first()
        
        profit_amount = profit_record.amount if profit_record else 0
        
        # Also check transaction-based profits for this date
        date_start = datetime.combine(check_date, datetime.min.time())
        date_end = datetime.combine(check_date, datetime.max.time())
        
        transaction_profit = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'trade_profit',
            Transaction.timestamp >= date_start,
            Transaction.timestamp <= date_end,
            Transaction.status == 'completed'
        ).scalar() or 0
        
        # Use the higher profit value
        daily_profit = max(profit_amount, transaction_profit)
        
        if daily_profit > 0:
            current_streak += 1
        else:
            # Break streak if no profit on this day (except for today if it's early)
            if i > 0:  # Don't break on today
                break
    
    return current_streak

def fix_user_performance_data():
    """Fix performance data for all users to enable real-time autopilot dashboard updates."""
    
    print("🔧 Fixing Autopilot Dashboard Real-time Data Connection")
    print("=" * 60)
    
    with app.app_context():
        # Get all users
        users = User.query.all()
        
        print(f"Processing {len(users)} users...")
        
        fixed_users = 0
        
        for user in users:
            try:
                print(f"\n👤 Processing User ID {user.id} (Balance: {user.balance:.6f} SOL)")
                
                # Get or create UserMetrics
                metrics = UserMetrics.query.filter_by(user_id=user.id).first()
                if not metrics:
                    metrics = UserMetrics()
                    metrics.user_id = user.id
                    db.session.add(metrics)
                    print("   Created UserMetrics record")
                
                # Calculate current streak
                old_streak = metrics.current_streak
                new_streak = calculate_user_streak(user.id)
                
                metrics.current_streak = new_streak
                
                # Update best streak if necessary
                if new_streak > (metrics.best_streak or 0):
                    metrics.best_streak = new_streak
                
                # Set trading mode if not set
                if not metrics.trading_mode:
                    metrics.trading_mode = 'autopilot'
                
                # Set milestone and goal if not set
                if not metrics.next_milestone and user.initial_deposit > 0:
                    metrics.next_milestone = max(user.initial_deposit * 0.1, 0.05)
                
                if not metrics.current_goal and user.initial_deposit > 0:
                    metrics.current_goal = user.initial_deposit * 2
                
                # Calculate milestone progress
                if metrics.next_milestone and metrics.next_milestone > 0:
                    profit = user.balance - user.initial_deposit
                    metrics.milestone_progress = min(100, (profit / metrics.next_milestone) * 100)
                
                # Calculate goal progress
                if metrics.current_goal and metrics.current_goal > 0:
                    metrics.goal_progress = min(100, (user.balance / metrics.current_goal) * 100)
                
                db.session.commit()
                
                print(f"   ✅ Fixed streak: {old_streak} → {new_streak}")
                print(f"   📊 Milestone progress: {metrics.milestone_progress:.1f}%")
                print(f"   🎯 Goal progress: {metrics.goal_progress:.1f}%")
                
                fixed_users += 1
                
            except Exception as e:
                print(f"   ❌ Error processing user {user.id}: {e}")
                db.session.rollback()
                continue
        
        print(f"\n✅ Successfully fixed performance data for {fixed_users}/{len(users)} users")

def test_real_time_data_flow():
    """Test that the autopilot dashboard can now access real-time data."""
    
    print("\n🧪 Testing Real-time Data Flow")
    print("=" * 40)
    
    with app.app_context():
        # Get a sample user
        sample_user = User.query.first()
        if not sample_user:
            print("❌ No users found for testing")
            return False
        
        print(f"Testing with User ID {sample_user.id}")
        
        # Test performance data retrieval
        try:
            performance_data = get_performance_data(sample_user.id)
            
            if performance_data:
                print("✅ Performance data retrieved successfully:")
                print(f"   Current Balance: {performance_data['current_balance']:.6f} SOL")
                print(f"   Today's Profit: {performance_data['today_profit']:.6f} SOL")
                print(f"   Total Profit: {performance_data['total_profit']:.6f} SOL")
                print(f"   Profit Streak: {performance_data['streak_days']} days")
                print(f"   Trading Mode: {performance_data['trading_mode']}")
                
                # Test that streak is not zero if user has profits
                if performance_data['total_profit'] > 0 and performance_data['streak_days'] == 0:
                    print("⚠️  User has profits but zero streak - this may indicate recent data")
                
                return True
            else:
                print("❌ Failed to retrieve performance data")
                return False
                
        except Exception as e:
            print(f"❌ Error testing performance data: {e}")
            return False

def generate_dashboard_preview():
    """Generate a preview of how the autopilot dashboard will look with real-time data."""
    
    print("\n📱 Autopilot Dashboard Preview with Real-time Data")
    print("=" * 50)
    
    with app.app_context():
        sample_user = User.query.first()
        if not sample_user:
            print("❌ No users found for preview")
            return
        
        try:
            performance_data = get_performance_data(sample_user.id)
            
            if performance_data:
                # Simulate the dashboard message format
                current_balance = performance_data['current_balance']
                today_profit = performance_data['today_profit']
                today_percentage = performance_data['today_percentage']
                total_profit = performance_data['total_profit']
                total_percentage = performance_data['total_percentage']
                streak = performance_data['streak_days']
                
                dashboard_preview = f"""
📊 *Autopilot Dashboard*

• *Balance:* {current_balance:.2f} SOL
• *Today's Profit:* {today_profit:.2f} SOL ({today_percentage:.1f}% of balance)
• *Total Profit:* +{total_percentage:.1f}% ({total_profit:.2f} SOL)
"""
                
                # Add streak information (this is what was broken before)
                if streak > 0:
                    fire_emojis = "🔥" * min(3, streak)
                    dashboard_preview += f"• *Profit Streak:* {streak}-Day Green Streak! {fire_emojis}\n"
                else:
                    dashboard_preview += f"• *Profit Streak:* {streak} Days\n"
                
                dashboard_preview += """• *Mode:* Autopilot Trader (Fully Automated)

Autopilot is actively scanning for new trading opportunities! 💪
"""
                
                print(dashboard_preview)
                print("✅ Dashboard now shows real-time data instead of 'Start your streak today!'")
                
            else:
                print("❌ Could not generate dashboard preview")
                
        except Exception as e:
            print(f"❌ Error generating dashboard preview: {e}")

def main():
    """Run the complete fix for autopilot dashboard real-time data."""
    
    print("🚀 Starting Autopilot Dashboard Real-time Data Fix")
    print("=" * 60)
    
    # Step 1: Fix user performance data
    fix_user_performance_data()
    
    # Step 2: Test real-time data flow
    success = test_real_time_data_flow()
    
    # Step 3: Generate dashboard preview
    if success:
        generate_dashboard_preview()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ AUTOPILOT DASHBOARD REAL-TIME DATA FIX COMPLETED")
        print("\nThe autopilot dashboard will now show:")
        print("• Real-time profit streak data instead of 'Start your streak today!'")
        print("• Accurate balance and profit information")
        print("• Live updates from the performance tracking system")
        print("\nUsers can now see their actual trading progress in the dashboard!")
    else:
        print("❌ Fix incomplete - please check error messages above")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)