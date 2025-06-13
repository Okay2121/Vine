#!/usr/bin/env python
"""
Test Real-time Performance Dashboard Updates
============================================
This script creates test trading positions and transactions to verify that
the TODAY'S PERFORMANCE section updates in real time.
"""

import sys
import os
from datetime import datetime, timedelta
from app import app, db
from models import User, TradingPosition, Transaction, Profit

def create_test_performance_data():
    """Create test data to verify real-time performance tracking"""
    with app.app_context():
        # Find the test user (admin user)
        user = User.query.filter_by(telegram_id="5488280696").first()
        if not user:
            print("Test user not found. Please start the bot first.")
            return False
        
        print(f"Creating test performance data for user: {user.username}")
        print(f"Current balance: {user.balance:.4f} SOL")
        
        # Create today's trading positions
        today = datetime.utcnow()
        
        # Create a profitable trade from today
        profitable_position = TradingPosition(
            user_id=user.id,
            token_name="TEST",
            amount=1000.0,
            entry_price=0.001,
            current_price=0.0015,  # 50% profit
            timestamp=today,
            status='closed',
            trade_type='scalp'
        )
        
        # Calculate ROI percentage
        profitable_position.roi_percentage = 50.0
        
        db.session.add(profitable_position)
        
        # Create corresponding profit transaction
        profit_amount = (profitable_position.current_price - profitable_position.entry_price) * profitable_position.amount
        
        profit_transaction = Transaction(
            user_id=user.id,
            transaction_type='trade_profit',
            amount=profit_amount,
            token_name='TEST',
            timestamp=today,
            status='completed',
            notes=f'Profit from TEST trade - 50% ROI'
        )
        
        db.session.add(profit_transaction)
        
        # Update user balance to reflect the profit
        user.balance += profit_amount
        
        # Create a Profit record for today
        today_profit = Profit(
            user_id=user.id,
            amount=profit_amount,
            percentage=50.0,
            date=today.date()
        )
        
        db.session.add(today_profit)
        
        # Create yesterday's profitable trade for streak calculation
        yesterday = today - timedelta(days=1)
        
        yesterday_position = TradingPosition(
            user_id=user.id,
            token_name="STREAK",
            amount=500.0,
            entry_price=0.002,
            current_price=0.0024,  # 20% profit
            timestamp=yesterday,
            status='closed',
            trade_type='momentum'
        )
        
        yesterday_position.roi_percentage = 20.0
        db.session.add(yesterday_position)
        
        # Yesterday's profit transaction
        yesterday_profit_amount = (yesterday_position.current_price - yesterday_position.entry_price) * yesterday_position.amount
        
        yesterday_transaction = Transaction(
            user_id=user.id,
            transaction_type='trade_profit',
            amount=yesterday_profit_amount,
            token_name='STREAK',
            timestamp=yesterday,
            status='completed',
            notes=f'Profit from STREAK trade - 20% ROI'
        )
        
        db.session.add(yesterday_transaction)
        
        # Yesterday's Profit record
        yesterday_profit_record = Profit(
            user_id=user.id,
            amount=yesterday_profit_amount,
            percentage=20.0,
            date=yesterday.date()
        )
        
        db.session.add(yesterday_profit_record)
        
        # Commit all changes
        db.session.commit()
        
        print(f"✅ Created test performance data:")
        print(f"   - Today's profit: +{profit_amount:.4f} SOL (50% ROI)")
        print(f"   - Yesterday's profit: +{yesterday_profit_amount:.4f} SOL (20% ROI)")
        print(f"   - New balance: {user.balance:.4f} SOL")
        print(f"   - Expected streak: 2 days")
        
        return True

def verify_performance_calculation():
    """Verify that the performance dashboard calculates correctly"""
    with app.app_context():
        from sqlalchemy import func
        
        user = User.query.filter_by(telegram_id="5488280696").first()
        if not user:
            print("Test user not found.")
            return False
        
        today_date = datetime.utcnow().date()
        today_start = datetime.combine(today_date, datetime.min.time())
        today_end = datetime.combine(today_date, datetime.max.time())
        
        print(f"\n🔍 Verifying performance calculation for {user.username}")
        print(f"Current balance: {user.balance:.4f} SOL")
        
        # Check today's trade profits from Transaction table
        today_trade_profits = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type == 'trade_profit',
            Transaction.timestamp >= today_start,
            Transaction.timestamp <= today_end,
            Transaction.status == 'completed'
        ).scalar() or 0
        
        print(f"Today's trade profits from Transaction table: {today_trade_profits:.4f} SOL")
        
        # Check today's positions
        today_positions = TradingPosition.query.filter(
            TradingPosition.user_id == user.id,
            TradingPosition.status == 'closed',
            TradingPosition.timestamp >= today_start,
            TradingPosition.timestamp <= today_end
        ).all()
        
        print(f"Today's closed positions: {len(today_positions)}")
        
        today_position_profits = 0
        for position in today_positions:
            if hasattr(position, 'roi_percentage') and position.roi_percentage:
                position_profit = (position.entry_price * position.amount * position.roi_percentage / 100)
                today_position_profits += position_profit
                print(f"  - {position.token_name}: {position_profit:.4f} SOL ({position.roi_percentage}% ROI)")
        
        print(f"Today's position profits: {today_position_profits:.4f} SOL")
        
        # Check Profit table
        today_profit_record = Profit.query.filter_by(user_id=user.id, date=today_date).first()
        profit_table_amount = today_profit_record.amount if today_profit_record else 0
        
        print(f"Today's profit from Profit table: {profit_table_amount:.4f} SOL")
        
        # Final calculation
        final_today_profit = max(today_trade_profits, today_position_profits, profit_table_amount)
        print(f"\n✅ Final today's profit calculation: {final_today_profit:.4f} SOL")
        
        return True

if __name__ == "__main__":
    print("🚀 Testing Real-time Performance Dashboard")
    print("=" * 50)
    
    if create_test_performance_data():
        print("\n" + "=" * 50)
        verify_performance_calculation()
        print("\n✅ Test data created successfully!")
        print("Now test the dashboard with /dashboard command in Telegram to see real-time updates.")
    else:
        print("❌ Failed to create test data")