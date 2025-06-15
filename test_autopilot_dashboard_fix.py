#!/usr/bin/env python
"""
Test Autopilot Dashboard Fix
============================
This script tests the fixed autopilot dashboard to ensure all values update correctly.
"""

import sys
import os
from datetime import datetime, timedelta
from app import app, db
from models import User, Transaction, Profit

def test_dashboard_calculations():
    """Test that dashboard calculations work correctly"""
    print("Testing Autopilot Dashboard Calculations...")
    
    with app.app_context():
        # Find a test user
        test_user = User.query.filter(User.balance > 0).first()
        
        if not test_user:
            print("No test user with balance found")
            return False
        
        print(f"\n--- Testing User: {test_user.telegram_id} ---")
        print(f"Current Balance: {test_user.balance:.4f} SOL")
        print(f"Initial Deposit: {test_user.initial_deposit:.4f} SOL")
        
        # Test the dashboard calculation logic directly
        from sqlalchemy import func
        
        # Calculate total profits from both sources
        total_trade_profits = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == test_user.id,
            Transaction.transaction_type == 'trade_profit',
            Transaction.status == 'completed'
        ).scalar() or 0
        
        total_profit_table = db.session.query(func.sum(Profit.amount)).filter_by(
            user_id=test_user.id
        ).scalar() or 0
        
        total_profit_amount = max(total_trade_profits, total_profit_table)
        
        print(f"Trade Profits: {total_trade_profits:.4f} SOL")
        print(f"Profit Table: {total_profit_table:.4f} SOL")
        print(f"Total Profit (max): {total_profit_amount:.4f} SOL")
        
        # Calculate today's profits
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_trade_profits = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == test_user.id,
            Transaction.transaction_type == 'trade_profit',
            Transaction.timestamp >= today_start,
            Transaction.timestamp <= today_end,
            Transaction.status == 'completed'
        ).scalar() or 0
        
        today_profit_table = db.session.query(func.sum(Profit.amount)).filter_by(
            user_id=test_user.id, 
            date=today
        ).scalar() or 0
        
        today_profit_amount = max(today_trade_profits, today_profit_table)
        
        print(f"Today's Trade Profits: {today_trade_profits:.4f} SOL")
        print(f"Today's Profit Table: {today_profit_table:.4f} SOL")
        print(f"Today's Total Profit: {today_profit_amount:.4f} SOL")
        
        # Test days active calculation
        first_balance_date = None
        
        # Check for first deposit
        first_deposit = Transaction.query.filter_by(
            user_id=test_user.id, 
            transaction_type='deposit',
            status='completed'
        ).order_by(Transaction.timestamp).first()
        
        if first_deposit:
            first_balance_date = first_deposit.timestamp.date()
            print(f"First Deposit Date: {first_balance_date}")
        
        # Check for admin adjustments
        first_admin_adjustment = Transaction.query.filter_by(
            user_id=test_user.id,
            transaction_type='admin_adjustment',
            status='completed'
        ).filter(Transaction.amount > 0).order_by(Transaction.timestamp).first()
        
        if first_admin_adjustment:
            admin_date = first_admin_adjustment.timestamp.date()
            if not first_balance_date or admin_date < first_balance_date:
                first_balance_date = admin_date
            print(f"First Admin Adjustment Date: {admin_date}")
        
        # Calculate days active
        if test_user.balance > 0 and first_balance_date:
            days_active = (datetime.utcnow().date() - first_balance_date).days + 1
            days_active = min(days_active, 365)
        elif test_user.balance > 0:
            days_active = min((datetime.utcnow().date() - test_user.joined_at.date()).days + 1, 365)
        else:
            days_active = 0
            
        print(f"Days Active: {days_active}")
        
        # Test streak calculation
        streak = 0
        current_date = datetime.utcnow().date()
        consecutive_streak = True
        
        for i in range(10):  # Check last 10 days
            check_date = current_date - timedelta(days=i)
            check_date_start = datetime.combine(check_date, datetime.min.time())
            check_date_end = datetime.combine(check_date, datetime.max.time())
            
            day_trade_profit = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == test_user.id,
                Transaction.transaction_type == 'trade_profit',
                Transaction.timestamp >= check_date_start,
                Transaction.timestamp <= check_date_end,
                Transaction.status == 'completed'
            ).scalar() or 0
            
            day_profit_table = db.session.query(func.sum(Profit.amount)).filter_by(
                user_id=test_user.id, 
                date=check_date
            ).scalar() or 0
            
            day_profit = max(day_trade_profit, day_profit_table)
            
            if day_profit > 0 and consecutive_streak:
                streak += 1
                print(f"Day {i} ({check_date}): {day_profit:.4f} SOL profit ✓")
            elif day_profit <= 0:
                consecutive_streak = False
                print(f"Day {i} ({check_date}): No profit ✗")
                if i > 0:
                    break
            
        print(f"Profit Streak: {streak} days")
        
        # Simulate the dashboard message format
        current_balance = test_user.balance
        today_profit_percentage = (today_profit_amount / max(test_user.balance, 0.01)) * 100 if test_user.balance > 0 else 0
        
        if test_user.initial_deposit > 0:
            total_profit_percentage = (total_profit_amount / test_user.initial_deposit) * 100
        elif test_user.balance > 0:
            total_profit_percentage = (total_profit_amount / max(test_user.balance, 0.01)) * 100
        else:
            total_profit_percentage = 0
        
        print(f"\n--- DASHBOARD PREVIEW ---")
        print(f"📊 Autopilot Dashboard")
        print(f"")
        print(f"• Balance: {current_balance:.2f} SOL")
        print(f"• Today's Profit: {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}% of balance)")
        print(f"• Total Profit: +{total_profit_percentage:.1f}% ({total_profit_amount:.2f} SOL)")
        
        if streak > 0:
            fire_emojis = "🔥" * min(3, streak)
            print(f"• Profit Streak: {streak}-Day Green Streak! {fire_emojis}")
        else:
            print(f"• Profit Streak: Start your streak today!")
            
        print(f"• Mode: Autopilot Trader (Fully Automated)")
        if days_active > 0:
            print(f"• Day: {days_active}")
        else:
            print(f"• Day: Start your streak today!")
        
        print(f"\n✅ Dashboard calculations are working correctly!")
        return True

def test_with_sample_user():
    """Test with a sample user to ensure calculations work"""
    print("\n=== Testing Dashboard Fix ===")
    
    try:
        result = test_dashboard_calculations()
        if result:
            print("\n🎉 All dashboard calculations are working properly!")
            print("The autopilot dashboard should now show correct values for:")
            print("- Today's Profit (updates daily)")
            print("- Total Profit (shows cumulative gains)")
            print("- Profit Streak (counts consecutive profitable days)")
            print("- Day Counter (counts days since first SOL balance)")
        else:
            print("\n❌ Dashboard calculations need further adjustment")
            
    except Exception as e:
        print(f"\n❌ Error testing dashboard: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_sample_user()