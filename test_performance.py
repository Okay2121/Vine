#!/usr/bin/env python3
"""
Test script to debug the performance button issue
"""
import sys
sys.path.append('.')

# Import the bot context
from app import app, db
from models import User, Transaction, Profit
from datetime import datetime, timedelta

def test_performance_handler():
    """Test the performance data generation without bot integration"""
    try:
        with app.app_context():
            # Test with a sample user ID
            user = User.query.first()
            if not user:
                print("No users found in database")
                return
            
            print(f"Testing performance data for user: {user.username}")
            
            # Get today's date for filtering trades
            today_date = datetime.now().date()
            
            # Get all trades for today
            trades_today = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type.in_(['buy', 'sell']),
                Transaction.timestamp >= datetime.combine(today_date, datetime.min.time())
            ).all()
            
            print(f"Found {len(trades_today)} trades today")
            
            # Calculate trading stats
            profitable_trades = 0
            loss_trades = 0
            
            for trade in trades_today:
                if trade.amount > 0:
                    profitable_trades += 1
                else:
                    loss_trades += 1
            
            total_trades = profitable_trades + loss_trades
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            
            print(f"Trading stats: {profitable_trades} wins, {loss_trades} losses, {win_rate:.1f}% win rate")
            
            # Build performance message
            performance_message = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
            performance_message += "💰 *BALANCE*\n"
            performance_message += f"Initial: {user.initial_deposit:.2f} SOL\n"
            performance_message += f"Current: {user.balance:.2f} SOL\n"
            
            # Get total profit
            total_profit_amount = user.balance - user.initial_deposit
            total_profit_percentage = (total_profit_amount / user.initial_deposit * 100) if user.initial_deposit > 0 else 0
            
            performance_message += f"Profit: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)\n\n"
            
            print("Performance message generated successfully:")
            print(performance_message)
            
            return True
            
    except Exception as e:
        print(f"Error in test_performance_handler: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing performance handler...")
    success = test_performance_handler()
    if success:
        print("✅ Performance handler test completed successfully")
    else:
        print("❌ Performance handler test failed")