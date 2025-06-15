#!/usr/bin/env python3
"""
Refresh Performance Data
=======================
Force refresh performance tracking data to ensure balance updates are reflected
"""

from app import app, db
from models import User, Transaction, TradingPosition
from performance_tracking import get_performance_data, update_daily_snapshot
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

def refresh_user_performance():
    """Refresh performance data for all users to ensure real-time updates."""
    
    with app.app_context():
        print("Refreshing performance data for all users...")
        
        # Get all users with balances
        users = User.query.filter(User.balance > 0).all()
        print(f"Found {len(users)} users with balances")
        
        for user in users:
            try:
                # Update daily snapshot
                update_daily_snapshot(user.id)
                
                # Get updated performance data
                perf_data = get_performance_data(user.id)
                
                if perf_data:
                    print(f"User {user.id} ({user.telegram_id}):")
                    print(f"  Balance: {perf_data['current_balance']:.6f} SOL")
                    print(f"  Today's Profit: {perf_data['today_profit']:.6f} SOL ({perf_data['today_percentage']:.2f}%)")
                    print(f"  Total Profit: {perf_data['total_profit']:.6f} SOL ({perf_data['total_percentage']:.2f}%)")
                
            except Exception as e:
                print(f"Error refreshing data for user {user.id}: {e}")
        
        print("Performance data refresh complete")

def check_recent_trade_impacts():
    """Check how recent trades affected user balances."""
    
    with app.app_context():
        print("\nChecking recent trade impacts...")
        
        # Get trades from the last hour
        one_hour_ago = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        recent_transactions = Transaction.query.filter(
            Transaction.timestamp >= one_hour_ago,
            Transaction.transaction_type.in_(['trade_profit', 'trade_loss'])
        ).order_by(Transaction.timestamp.desc()).all()
        
        print(f"Found {len(recent_transactions)} recent trade transactions")
        
        for tx in recent_transactions:
            user = User.query.get(tx.user_id)
            action = "profit" if tx.transaction_type == 'trade_profit' else "loss"
            amount_display = f"+{tx.amount}" if tx.transaction_type == 'trade_profit' else f"-{tx.amount}"
            
            print(f"  {tx.timestamp}: User {tx.user_id} ({user.telegram_id if user else 'N/A'}) - {action} {amount_display} SOL from {tx.token_name or 'N/A'}")

def main():
    """Main function to refresh and verify performance data."""
    
    print("Performance Data Refresh Tool")
    print("=" * 40)
    
    # Check recent trade impacts first
    check_recent_trade_impacts()
    
    # Refresh all performance data
    refresh_user_performance()
    
    print("\n" + "=" * 40)
    print("Data refresh complete. Dashboard should now show updated values.")

if __name__ == "__main__":
    main()