#!/usr/bin/env python3
"""
Performance Dashboard Issue Diagnostic and Fix
==============================================
This script diagnoses and fixes issues with the performance dashboard:
1. Initial deposit not reflecting properly
2. Performance calculations not working correctly
3. Real-time data synchronization issues
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Transaction, TradingPosition, Profit
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnose_user_data():
    """Diagnose user data issues"""
    with app.app_context():
        print("\n" + "="*60)
        print("PERFORMANCE DASHBOARD DIAGNOSTIC")
        print("="*60)
        
        # Get all users
        users = User.query.all()
        print(f"\nFound {len(users)} users in database")
        
        for user in users[:5]:  # Check first 5 users
            print(f"\n--- User: {user.username} (ID: {user.id}) ---")
            print(f"Telegram ID: {user.telegram_id}")
            print(f"Current Balance: {user.balance:.6f} SOL")
            print(f"Initial Deposit: {user.initial_deposit:.6f} SOL")
            print(f"Status: {user.status}")
            print(f"Joined: {user.joined_at}")
            
            # Check transactions
            deposits = Transaction.query.filter_by(
                user_id=user.id, 
                transaction_type='deposit'
            ).order_by(Transaction.timestamp.asc()).all()
            
            print(f"Deposit Transactions: {len(deposits)}")
            for i, deposit in enumerate(deposits[:3]):  # Show first 3 deposits
                print(f"  {i+1}. {deposit.amount:.6f} SOL on {deposit.timestamp}")
            
            # Check if initial_deposit matches first deposit
            if deposits and user.initial_deposit == 0:
                print(f"⚠️  ISSUE: Initial deposit is 0 but user has {len(deposits)} deposit transactions!")
                first_deposit = deposits[0]
                print(f"   First deposit was {first_deposit.amount:.6f} SOL on {first_deposit.timestamp}")
            
            # Check profit records
            profits = Profit.query.filter_by(user_id=user.id).all()
            print(f"Profit Records: {len(profits)}")
            
            # Calculate expected total profit
            total_deposits = sum(t.amount for t in deposits)
            expected_initial = deposits[0].amount if deposits else 0
            current_profit = user.balance - expected_initial if expected_initial > 0 else 0
            
            print(f"Total Deposits: {total_deposits:.6f} SOL")
            print(f"Expected Initial: {expected_initial:.6f} SOL")
            print(f"Current Profit: {current_profit:.6f} SOL")
            
            if abs(user.initial_deposit - expected_initial) > 0.000001:
                print(f"🔧 NEEDS FIX: initial_deposit should be {expected_initial:.6f}")

def fix_initial_deposit_issues():
    """Fix initial deposit issues for all users"""
    with app.app_context():
        print("\n" + "="*60)
        print("FIXING INITIAL DEPOSIT ISSUES")
        print("="*60)
        
        users_fixed = 0
        
        for user in User.query.all():
            # Find the first deposit transaction
            first_deposit = Transaction.query.filter_by(
                user_id=user.id,
                transaction_type='deposit'
            ).order_by(Transaction.timestamp.asc()).first()
            
            if first_deposit and user.initial_deposit == 0:
                print(f"Fixing user {user.username}: setting initial_deposit to {first_deposit.amount:.6f} SOL")
                user.initial_deposit = first_deposit.amount
                users_fixed += 1
            elif first_deposit and abs(user.initial_deposit - first_deposit.amount) > 0.000001:
                print(f"Correcting user {user.username}: initial_deposit from {user.initial_deposit:.6f} to {first_deposit.amount:.6f} SOL")
                user.initial_deposit = first_deposit.amount
                users_fixed += 1
        
        if users_fixed > 0:
            db.session.commit()
            print(f"✅ Fixed initial_deposit for {users_fixed} users")
        else:
            print("✅ No initial_deposit issues found")

def test_performance_calculations():
    """Test performance calculation logic"""
    with app.app_context():
        print("\n" + "="*60)
        print("TESTING PERFORMANCE CALCULATIONS")
        print("="*60)
        
        # Find a user with data
        user = User.query.filter(User.balance > 0).first()
        if not user:
            print("❌ No users with balance found for testing")
            return
        
        print(f"Testing with user: {user.username}")
        print(f"Current Balance: {user.balance:.6f} SOL")
        print(f"Initial Deposit: {user.initial_deposit:.6f} SOL")
        
        # Test different calculation methods
        
        # Method 1: Direct calculation
        if user.initial_deposit > 0:
            total_profit = user.balance - user.initial_deposit
            total_percentage = (total_profit / user.initial_deposit) * 100
            print(f"Direct Calculation: {total_profit:.6f} SOL ({total_percentage:.2f}%)")
        else:
            print("⚠️  Cannot calculate - initial_deposit is 0")
        
        # Method 2: Performance tracking system
        try:
            from performance_tracking import get_performance_data
            perf_data = get_performance_data(user.id)
            if perf_data:
                print(f"Performance Tracking: {perf_data['total_profit']:.6f} SOL ({perf_data['total_percentage']:.2f}%)")
                print(f"Today's P/L: {perf_data['today_profit']:.6f} SOL ({perf_data['today_percentage']:.2f}%)")
            else:
                print("⚠️  Performance tracking returned no data")
        except ImportError:
            print("⚠️  Performance tracking module not available")
        except Exception as e:
            print(f"⚠️  Performance tracking error: {e}")
        
        # Method 3: Database aggregation
        from sqlalchemy import func
        total_profit_from_db = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
        print(f"DB Profit Records: {total_profit_from_db:.6f} SOL")

def simulate_performance_dashboard():
    """Simulate the performance dashboard display"""
    with app.app_context():
        print("\n" + "="*60)
        print("SIMULATING PERFORMANCE DASHBOARD")
        print("="*60)
        
        # Find a user with data
        user = User.query.filter(User.balance > 0).first()
        if not user:
            print("❌ No users with balance found for testing")
            return
        
        print(f"Simulating dashboard for: {user.username}")
        
        # Use the same logic as the trading_history_handler
        try:
            from performance_tracking import get_performance_data
            performance_data = get_performance_data(user.id)
            
            if performance_data:
                current_balance = performance_data['current_balance']
                initial_deposit = performance_data['initial_deposit']
                total_profit_amount = performance_data['total_profit']
                total_profit_percentage = performance_data['total_percentage']
                today_profit_amount = performance_data['today_profit']
                today_profit_percentage = performance_data['today_percentage']
                streak = performance_data['streak_days']
                
                print("📊 PERFORMANCE DASHBOARD 📊")
                print()
                print("💰 BALANCE")
                print(f"Initial: {initial_deposit:.2f} SOL")
                print(f"Current: {current_balance:.2f} SOL")
                
                if total_profit_amount >= 0:
                    print(f"Total P/L: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)")
                else:
                    print(f"Total P/L: {total_profit_amount:.2f} SOL ({total_profit_percentage:.1f}%)")
                
                print()
                print("📈 TODAY'S PERFORMANCE")
                if today_profit_amount > 0:
                    print(f"P/L today: +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)")
                elif today_profit_amount < 0:
                    print(f"P/L today: {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}%)")
                else:
                    print("No P/L recorded yet today")
                
                print()
                print("🔥 WINNING STREAK")
                if streak > 0:
                    print(f"{streak} day{'s' if streak > 1 else ''} in a row!")
                else:
                    print("Start your streak today with your first profit!")
                
            else:
                # Fallback calculation
                print("Using fallback calculation...")
                current_balance = user.balance
                initial_deposit = user.initial_deposit or 1.0
                total_profit_amount = current_balance - initial_deposit
                total_profit_percentage = (total_profit_amount / initial_deposit) * 100
                
                print("📊 PERFORMANCE DASHBOARD 📊")
                print()
                print("💰 BALANCE")
                print(f"Initial: {initial_deposit:.2f} SOL")
                print(f"Current: {current_balance:.2f} SOL")
                print(f"Total P/L: {total_profit_amount:+.2f} SOL ({total_profit_percentage:+.1f}%)")
                
        except Exception as e:
            print(f"❌ Error simulating dashboard: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Run all diagnostics and fixes"""
    print("Starting Performance Dashboard Diagnostic...")
    
    diagnose_user_data()
    fix_initial_deposit_issues()
    test_performance_calculations()
    simulate_performance_dashboard()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("If issues persist, check:")
    print("1. performance_tracking.py module")
    print("2. Database transaction integrity")
    print("3. Real-time data synchronization")

if __name__ == "__main__":
    main()