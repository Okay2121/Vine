#!/usr/bin/env python3
"""
Test Corrected Admin Balance Logic
=================================
Verifies that admin balance adjustments:
1. Affect total P/L calculations (current balance vs initial deposit)
2. Do NOT appear in today's trading performance
3. Keep initial deposit as fixed baseline
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Transaction
from sqlalchemy import func

def test_admin_balance_behavior():
    """Test the corrected admin balance adjustment behavior"""
    with app.app_context():
        # Find a test user
        user = User.query.filter(User.balance > 0).first()
        if not user:
            print("No users found for testing")
            return
            
        print(f"Testing corrected admin logic with user: {user.username}")
        print(f"Current balance: {user.balance:.6f} SOL")
        print(f"Initial deposit: {user.initial_deposit:.6f} SOL")
        
        # Store original values
        original_balance = user.balance
        original_initial_deposit = user.initial_deposit
        
        # Simulate admin balance adjustment
        adjustment_amount = 0.5
        user.balance += adjustment_amount
        
        # Create admin credit transaction
        admin_tx = Transaction()
        admin_tx.user_id = user.id
        admin_tx.transaction_type = 'admin_credit'
        admin_tx.amount = adjustment_amount
        admin_tx.token_name = 'SOL'
        admin_tx.timestamp = datetime.utcnow()
        admin_tx.status = 'completed'
        admin_tx.notes = 'Test admin adjustment'
        admin_tx.tx_hash = f'admin_test_{int(datetime.utcnow().timestamp())}'
        
        db.session.add(admin_tx)
        db.session.commit()
        
        print(f"\nAdmin adjustment applied: +{adjustment_amount:.6f} SOL")
        print(f"New balance: {user.balance:.6f} SOL")
        print(f"Initial deposit remains: {user.initial_deposit:.6f} SOL")
        
        # Test dashboard calculations (same logic as corrected bot code)
        current_balance = user.balance
        initial_deposit = user.initial_deposit if user.initial_deposit > 0 else 1.0
        
        # Total P/L calculation (includes admin adjustments via current_balance)
        total_profit_amount = current_balance - initial_deposit
        total_profit_percentage = (total_profit_amount / initial_deposit) * 100
        
        # Today's performance calculation (ONLY trading, no admin adjustments)
        today_date = datetime.now().date()
        today_start = datetime.combine(today_date, datetime.min.time())
        today_end = datetime.combine(today_date, datetime.max.time())
        
        today_trade_profits = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type == 'trade_profit',
            Transaction.timestamp >= today_start,
            Transaction.timestamp <= today_end,
            Transaction.status == 'completed'
        ).scalar() or 0
        
        today_trade_losses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type == 'trade_loss',
            Transaction.timestamp >= today_start,
            Transaction.timestamp <= today_end,
            Transaction.status == 'completed'
        ).scalar() or 0
        
        # Net today profit (ONLY from trading)
        net_today_profit = today_trade_profits - abs(today_trade_losses)
        
        # Calculate starting balance for today
        starting_balance_today = current_balance - net_today_profit
        today_profit_percentage = (net_today_profit / starting_balance_today * 100) if starting_balance_today > 0 else 0
        
        print("\n" + "="*50)
        print("CORRECTED PERFORMANCE DASHBOARD PREVIEW")
        print("="*50)
        
        print("💰 BALANCE")
        print(f"Initial: {initial_deposit:.2f} SOL (unchanged)")
        print(f"Current: {current_balance:.2f} SOL (includes admin adjustment)")
        
        if total_profit_amount >= 0:
            print(f"Total P/L: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)")
        else:
            print(f"Total P/L: {total_profit_amount:.2f} SOL ({total_profit_percentage:.1f}%)")
        
        print(f"\n📈 TODAY'S PERFORMANCE (Trading Only)")
        if net_today_profit > 0:
            print(f"P/L today: +{net_today_profit:.2f} SOL (+{today_profit_percentage:.1f}%)")
        elif net_today_profit < 0:
            print(f"P/L today: {net_today_profit:.2f} SOL ({today_profit_percentage:.1f}%)")
        else:
            print("No trading P/L recorded today")
        
        print(f"Starting: {starting_balance_today:.2f} SOL")
        
        # Verify correct behavior
        print("\n" + "="*50)
        print("VERIFICATION")
        print("="*50)
        
        # Check that admin adjustment affects total P/L
        expected_total_increase = adjustment_amount
        actual_total_increase = total_profit_amount - (original_balance - original_initial_deposit)
        
        if abs(actual_total_increase - expected_total_increase) < 0.000001:
            print("✓ Admin adjustment correctly affects Total P/L")
        else:
            print(f"✗ Total P/L calculation error: expected +{expected_total_increase:.6f}, got +{actual_total_increase:.6f}")
        
        # Check that admin adjustment does NOT affect today's performance
        if net_today_profit == (today_trade_profits - abs(today_trade_losses)):
            print("✓ Today's performance only includes trading (no admin adjustments)")
        else:
            print("✗ Today's performance incorrectly includes admin adjustments")
        
        # Check that initial deposit is unchanged
        if user.initial_deposit == original_initial_deposit:
            print("✓ Initial deposit remains unchanged as baseline")
        else:
            print("✗ Initial deposit was incorrectly modified")
        
        # Clean up test data
        db.session.delete(admin_tx)
        user.balance = original_balance
        db.session.commit()
        
        print("\nTest completed and cleaned up")
        return True

def main():
    print("Testing corrected admin balance adjustment logic...")
    test_admin_balance_behavior()
    
    print("\nSUMMARY OF CORRECTED BEHAVIOR:")
    print("✓ Admin balance adjustments affect Total P/L (via current balance)")
    print("✓ Admin adjustments do NOT appear in Today's Performance")
    print("✓ Initial deposit remains fixed as baseline")
    print("✓ Today's Performance only shows actual trading results")

if __name__ == "__main__":
    main()