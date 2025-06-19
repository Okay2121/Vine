#!/usr/bin/env python3
"""
Quick Test - Verify P/L Fix Works
"""
import sys
sys.path.append('.')

from app import app, db
from models import User

def test_user_61_sol():
    """Test user with 0.61 SOL balance from screenshot"""
    with app.app_context():
        user = User.query.filter_by(username='electrocute2011').first()
        if user:
            print(f"User: {user.username}")
            print(f"Balance: {user.balance:.2f} SOL")
            print(f"Initial Deposit: {user.initial_deposit:.2f} SOL")
            
            try:
                from performance_tracking import get_performance_data
                data = get_performance_data(user.id)
                if data:
                    print(f"Expected Dashboard:")
                    print(f"  Initial: {data['initial_deposit']:.2f} SOL")
                    print(f"  Current: {data['current_balance']:.2f} SOL")
                    print(f"  Total P/L: {data['total_profit']:.2f} SOL ({data['total_percentage']:.1f}%)")
                    
                    if data['total_profit'] == 0:
                        print("✅ SUCCESS: P/L is now 0.00 as expected!")
                    else:
                        print(f"❌ Issue: P/L should be 0.00, got {data['total_profit']:.2f}")
                else:
                    print("❌ No performance data")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("❌ User not found")

if __name__ == "__main__":
    test_user_61_sol()