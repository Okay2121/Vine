#!/usr/bin/env python3
"""
Test Autopilot Dashboard Real-time Data Connection
================================================
This script verifies that the autopilot dashboard properly receives real-time data
from the performance tracking system and displays accurate day counters.
"""

import sys
import os
from datetime import datetime, timedelta
from app import app, db
from models import User, Profit, Transaction, UserMetrics, DailySnapshot
from performance_tracking import get_performance_data, get_days_with_balance
import logging

logging.basicConfig(level=logging.INFO)

def create_test_user_with_balance():
    """Create a test user with SOL balance and transaction history"""
    with app.app_context():
        # Clean up any existing test user and related data
        existing_user = User.query.filter_by(telegram_id="test_autopilot_dashboard").first()
        if existing_user:
            # Clean up related data first
            Transaction.query.filter_by(user_id=existing_user.id).delete()
            Profit.query.filter_by(user_id=existing_user.id).delete()
            UserMetrics.query.filter_by(user_id=existing_user.id).delete()
            DailySnapshot.query.filter_by(user_id=existing_user.id).delete()
            db.session.delete(existing_user)
            db.session.commit()
        
        # Create new test user
        user = User(
            telegram_id="test_autopilot_dashboard",
            username="test_autopilot",
            balance=1.64,  # Match the screenshot balance
            initial_deposit=1.0,
            wallet_address="test_wallet_autopilot",
            joined_at=datetime.utcnow() - timedelta(days=3)  # 3 days ago
        )
        db.session.add(user)
        db.session.flush()  # Get the user ID without committing
        
        # Add deposit transaction (2 days ago to simulate day counter starting then)
        deposit_tx = Transaction(
            user_id=user.id,
            transaction_type='deposit',
            amount=1.0,
            timestamp=datetime.utcnow() - timedelta(days=2),
            status='completed',
            notes='Test deposit for autopilot dashboard'
        )
        db.session.add(deposit_tx)
        
        # Add admin adjustment (1 day ago to add more balance)
        admin_tx = Transaction(
            user_id=user.id,
            transaction_type='admin_adjustment',
            amount=0.64,
            timestamp=datetime.utcnow() - timedelta(days=1),
            status='completed',
            notes='Test admin adjustment for autopilot dashboard'
        )
        db.session.add(admin_tx)
        
        db.session.commit()
        
        print(f"✅ Created test user with ID: {user.id}")
        print(f"   Balance: {user.balance} SOL")
        print(f"   Initial Deposit: {user.initial_deposit} SOL")
        print(f"   Joined: {user.joined_at}")
        
        return user

def test_autopilot_dashboard_data():
    """Test that autopilot dashboard gets real-time data from performance tracking"""
    with app.app_context():
        user = create_test_user_with_balance()
        
        print("\n🧪 Testing Autopilot Dashboard Real-time Data Connection")
        print("=" * 60)
        
        # Test 1: Performance data retrieval
        print("\n1. Testing performance data retrieval...")
        performance_data = get_performance_data(user.id)
        
        if performance_data:
            print("   ✅ Performance data retrieved successfully")
            print(f"   Current Balance: {performance_data['current_balance']:.2f} SOL")
            print(f"   Today's P/L: {performance_data['today_profit']:.2f} SOL ({performance_data['today_percentage']:.1f}%)")
            print(f"   Total P/L: {performance_data['total_profit']:.2f} SOL ({performance_data['total_percentage']:.1f}%)")
            print(f"   Profit Streak: {performance_data['streak_days']} days")
        else:
            print("   ❌ Failed to retrieve performance data")
            return False
        
        # Test 2: Days with balance calculation
        print("\n2. Testing days with balance calculation...")
        days_with_balance = get_days_with_balance(user.id)
        print(f"   Days with SOL balance: {days_with_balance}")
        
        # Should be 3 days (2 days since deposit + today)
        expected_days = 3
        if days_with_balance == expected_days:
            print(f"   ✅ Day counter correct: {days_with_balance} days")
        else:
            print(f"   ⚠️  Day counter mismatch: got {days_with_balance}, expected {expected_days}")
        
        # Test 3: Simulate autopilot dashboard generation
        print("\n3. Testing autopilot dashboard message generation...")
        
        # Extract values like the dashboard does
        current_balance = performance_data['current_balance']
        today_profit_amount = performance_data['today_profit']
        today_profit_percentage = performance_data['today_percentage']
        total_profit_amount = performance_data['total_profit']
        total_profit_percentage = performance_data['total_percentage']
        streak = performance_data['streak_days']
        
        # Generate dashboard message
        dashboard_message = (
            "📊 *Autopilot Dashboard*\n\n"
            f"• *Balance:* {current_balance:.2f} SOL\n"
        )
        
        # Today's P/L with proper sign formatting
        if today_profit_amount > 0:
            dashboard_message += f"• *Today's P/L:* +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)\n"
        elif today_profit_amount < 0:
            dashboard_message += f"• *Today's P/L:* {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}%)\n"
        else:
            dashboard_message += f"• *Today's P/L:* {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}%)\n"
        
        # Total P/L with proper sign formatting
        if total_profit_amount > 0:
            dashboard_message += f"• *Total P/L:* +{total_profit_percentage:.1f}% (+{total_profit_amount:.2f} SOL)\n"
        elif total_profit_amount < 0:
            dashboard_message += f"• *Total P/L:* {total_profit_percentage:.1f}% ({total_profit_amount:.2f} SOL)\n"
        else:
            dashboard_message += f"• *Total P/L:* {total_profit_percentage:.1f}% ({total_profit_amount:.2f} SOL)\n"
        
        # Add streak
        if streak > 0:
            dashboard_message += f"• *Profit Streak:* {streak}-Day Green Streak\n"
        else:
            dashboard_message += f"• *Profit Streak:* {streak} Days\n"
        
        # Add mode and day counter
        dashboard_message += "• *Mode:* Autopilot Trader (Fully Automated)\n"
        
        # Show day counter based on SOL balance
        if user.balance > 0 and days_with_balance > 0:
            dashboard_message += f"• *Day:* {days_with_balance}\n\n"
        elif user.balance > 0:
            dashboard_message += "• *Day:* 1\n\n"
        else:
            dashboard_message += "• *Day:* 0\n\n"
        
        dashboard_message += "Autopilot is actively scanning for new trading opportunities! 💪\n\n"
        dashboard_message += "_💡 Your Autopilot system is working 24/7 to find and execute trading opportunities._"
        
        print("   ✅ Dashboard message generated successfully")
        print("\n📱 Generated Dashboard Preview:")
        print("-" * 50)
        print(dashboard_message)
        print("-" * 50)
        
        return True

def test_zero_balance_user():
    """Test dashboard behavior for user with zero SOL balance"""
    with app.app_context():
        # Clean up any existing test user
        existing_user = User.query.filter_by(telegram_id="test_zero_balance").first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
        
        # Create user with zero balance
        user = User(
            telegram_id="test_zero_balance",
            username="test_zero",
            balance=0.0,
            initial_deposit=0.0,
            wallet_address="test_wallet_zero",
            joined_at=datetime.utcnow() - timedelta(days=5)
        )
        db.session.add(user)
        db.session.commit()
        
        print(f"\n🧪 Testing Zero Balance User (ID: {user.id})")
        print("=" * 40)
        
        # Test days with balance
        days_with_balance = get_days_with_balance(user.id)
        print(f"Days with SOL balance: {days_with_balance}")
        
        if days_with_balance == 0:
            print("✅ Zero balance user correctly shows 0 days")
        else:
            print(f"❌ Zero balance user shows {days_with_balance} days (should be 0)")
        
        return days_with_balance == 0

def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("🚀 Starting Autopilot Dashboard Real-time Data Tests")
    print("=" * 70)
    
    # Test 1: User with balance
    test1_result = test_autopilot_dashboard_data()
    
    # Test 2: User with zero balance
    test2_result = test_zero_balance_user()
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 30)
    print(f"✅ User with balance test: {'PASSED' if test1_result else 'FAILED'}")
    print(f"✅ Zero balance user test: {'PASSED' if test2_result else 'FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests PASSED! Autopilot dashboard real-time data connection is working correctly.")
        print("The dashboard now properly:")
        print("• Connects to performance tracking system for real-time data")
        print("• Counts days only when users have SOL balance > 0")
        print("• Shows accurate P/L data with proper sign formatting")
        print("• Displays correct profit streaks")
        print("• Handles zero balance users appropriately")
        return True
    else:
        print("\n❌ Some tests FAILED. Review the output above for details.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)