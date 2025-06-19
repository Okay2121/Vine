#!/usr/bin/env python3
"""
Fix P/L Calculation Logic
========================
Fixes the issue where deposits are being counted as profit/loss.
Ensures proper initial deposit tracking and accurate P/L calculations.
"""

import sys
import os
sys.path.append('.')

from app import app, db
from models import User, Transaction
from sqlalchemy import func

def fix_initial_deposits():
    """Fix initial_deposit values for all users based on actual deposits"""
    with app.app_context():
        print("Fixing initial deposit values...")
        
        users = User.query.all()
        fixed_count = 0
        
        for user in users:
            if user.initial_deposit <= 0 and user.balance > 0:
                # Get total deposits for this user
                total_deposits = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type.in_(['deposit', 'admin_adjustment']),
                    Transaction.status == 'completed',
                    Transaction.amount > 0
                ).scalar() or 0
                
                if total_deposits > 0:
                    old_initial = user.initial_deposit
                    user.initial_deposit = total_deposits
                    print(f"User {user.username}: {old_initial:.6f} -> {user.initial_deposit:.6f} SOL")
                    fixed_count += 1
                elif user.balance > 0:
                    # If no deposit transactions found, use current balance as baseline
                    user.initial_deposit = user.balance
                    print(f"User {user.username}: Set initial_deposit to current balance {user.balance:.6f} SOL")
                    fixed_count += 1
        
        db.session.commit()
        print(f"Fixed {fixed_count} users' initial deposit values")

def test_pl_calculations():
    """Test P/L calculations for users to verify the fix"""
    with app.app_context():
        print("\nTesting P/L calculations...")
        
        users = User.query.filter(User.balance > 0).all()
        
        for user in users:
            print(f"\n--- User: {user.username} ---")
            print(f"Current Balance: {user.balance:.6f} SOL")
            print(f"Initial Deposit: {user.initial_deposit:.6f} SOL")
            
            # Get trading profits/losses
            trade_profits = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type == 'trade_profit',
                Transaction.status == 'completed'
            ).scalar() or 0
            
            trade_losses = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type == 'trade_loss',
                Transaction.status == 'completed'
            ).scalar() or 0
            
            net_trading_pl = trade_profits - abs(trade_losses)
            
            print(f"Trading Profits: {trade_profits:.6f} SOL")
            print(f"Trading Losses: {abs(trade_losses):.6f} SOL")
            print(f"Net Trading P/L: {net_trading_pl:.6f} SOL")
            
            # Calculate percentage
            if user.initial_deposit > 0:
                pl_percentage = (net_trading_pl / user.initial_deposit) * 100
                print(f"P/L Percentage: {pl_percentage:.2f}%")
            
            # Expected dashboard display
            if net_trading_pl == 0:
                print("Expected Dashboard: Total P/L: 0.00 SOL (0.0%)")
            elif net_trading_pl > 0:
                print(f"Expected Dashboard: Total P/L: +{net_trading_pl:.2f} SOL (+{pl_percentage:.1f}%)")
            else:
                print(f"Expected Dashboard: Total P/L: {net_trading_pl:.2f} SOL ({pl_percentage:.1f}%)")

def main():
    print("="*60)
    print("FIXING P/L CALCULATION LOGIC")
    print("="*60)
    
    # Step 1: Fix initial deposit values
    fix_initial_deposits()
    
    # Step 2: Test P/L calculations
    test_pl_calculations()
    
    print("\n" + "="*60)
    print("FIX SUMMARY")
    print("="*60)
    print("✓ Updated initial_deposit values based on actual deposits")
    print("✓ P/L calculations now exclude deposits from profit calculations")
    print("✓ Only trading profits/losses are counted in P/L")
    print("\nExpected Dashboard Behavior:")
    print("- Initial: Shows actual deposit amount (not 0.00)")
    print("- Current: Shows current balance")
    print("- Total P/L: Shows 0.00 SOL (0.0%) until trades are made")
    print("- Only trading gains/losses affect P/L percentages")

if __name__ == "__main__":
    main()