#!/usr/bin/env python3
"""
Check Balance Update Issue
========================
Check if user balance is being updated correctly after trades
"""

import sys
from datetime import datetime, timedelta
from app import app, db
from models import User, Transaction, TradingPosition
import logging

logging.basicConfig(level=logging.INFO)

def check_user_balance():
    """Check the current user balance and recent transactions."""
    
    with app.app_context():
        # Get the test user
        user = User.query.filter_by(telegram_id='7611754415').first()
        if not user:
            print("User not found")
            return
        
        print(f"User ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Current Balance: {user.balance} SOL")
        print(f"Initial Deposit: {user.initial_deposit} SOL")
        
        # Check recent transactions (last 10)
        print("\nRecent Transactions:")
        recent_txs = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
        for tx in recent_txs:
            print(f"  {tx.timestamp}: {tx.transaction_type} {tx.amount} SOL - {tx.token_name or 'N/A'}")
        
        # Check recent trading positions
        print("\nRecent Trading Positions:")
        recent_positions = TradingPosition.query.filter_by(user_id=user.id).order_by(TradingPosition.timestamp.desc()).limit(5).all()
        for pos in recent_positions:
            print(f"  {pos.timestamp}: {pos.token_name} - Status: {pos.status} - ROI: {pos.roi_percentage or 'N/A'}%")
        
        # Calculate expected balance based on transactions
        print("\nBalance Calculation Check:")
        
        # Get all profit/loss transactions
        profit_txs = Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type.in_(['trade_profit', 'trade_loss'])
        ).all()
        
        total_profits = sum(tx.amount for tx in profit_txs if tx.transaction_type == 'trade_profit')
        total_losses = sum(tx.amount for tx in profit_txs if tx.transaction_type == 'trade_loss')
        
        expected_balance = user.initial_deposit + total_profits - total_losses
        
        print(f"  Initial Deposit: {user.initial_deposit} SOL")
        print(f"  Total Profits: +{total_profits} SOL")
        print(f"  Total Losses: -{total_losses} SOL")
        print(f"  Expected Balance: {expected_balance} SOL")
        print(f"  Actual Balance: {user.balance} SOL")
        print(f"  Difference: {user.balance - expected_balance} SOL")
        
        if abs(user.balance - expected_balance) > 0.001:
            print("  ⚠️ Balance mismatch detected!")
        else:
            print("  ✅ Balance matches expected calculation")

def check_zomboink_trades():
    """Check specifically for ZOMBOINK trades that were just processed."""
    
    with app.app_context():
        print("\nZOMBOINK Trade Analysis:")
        
        # Look for ZOMBOINK transactions from the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        zomboink_txs = Transaction.query.filter(
            Transaction.token_name.like('%ZOMBOINK%'),
            Transaction.timestamp >= one_hour_ago
        ).order_by(Transaction.timestamp.desc()).all()
        
        print(f"Found {len(zomboink_txs)} ZOMBOINK transactions in last hour:")
        for tx in zomboink_txs:
            user = User.query.get(tx.user_id)
            print(f"  User {tx.user_id} ({user.telegram_id if user else 'Unknown'}): {tx.transaction_type} {tx.amount} SOL at {tx.timestamp}")
        
        # Check ZOMBOINK positions
        zomboink_positions = TradingPosition.query.filter(
            TradingPosition.token_name.like('%ZOMBOINK%'),
            TradingPosition.timestamp >= one_hour_ago
        ).order_by(TradingPosition.timestamp.desc()).all()
        
        print(f"\nFound {len(zomboink_positions)} ZOMBOINK positions in last hour:")
        for pos in zomboink_positions:
            print(f"  Position {pos.id}: User {pos.user_id} - Status: {pos.status} - ROI: {pos.roi_percentage or 'N/A'}%")

def main():
    """Run balance check analysis."""
    
    print("Balance Update Analysis")
    print("=" * 40)
    
    check_user_balance()
    check_zomboink_trades()
    
    print("\n" + "=" * 40)
    print("Analysis complete")

if __name__ == "__main__":
    main()