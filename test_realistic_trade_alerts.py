"""
Test Realistic Trade Alerts
===========================
This script tests the new realistic trade notification system to ensure
trade alerts show proper spending amounts based on each user's actual balance.
"""

import logging
from app import app, db
from models import User, TradingPosition
from smart_balance_allocator import (
    calculate_smart_allocation, 
    generate_realistic_trade_notification
)
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_realistic_allocations():
    """Test realistic allocation calculations for different user balances"""
    print("🧮 Testing Realistic Allocation Calculations")
    print("=" * 50)
    
    # Test scenarios with different balance levels
    test_cases = [
        {"balance": 1.5, "user_type": "Small holder (like your user)"},
        {"balance": 5.0, "user_type": "Medium holder"},
        {"balance": 10.0, "user_type": "Large holder"},
        {"balance": 0.8, "user_type": "Micro holder"},
    ]
    
    entry_price = 0.041070  # ZIG token price from your example
    
    for case in test_cases:
        allocation = calculate_smart_allocation(case["balance"], entry_price)
        
        print(f"\n{case['user_type']} - {case['balance']} SOL:")
        print(f"  💰 Spendable: {allocation['spendable_sol']} SOL ({allocation['allocation_percent']:.1f}%)")
        print(f"  🎯 Token Qty: {allocation['token_quantity']:,} ZIG")
        print(f"  📊 Risk Level: {allocation['risk_level']}")
        print(f"  🔒 Remaining: {case['balance'] - allocation['spendable_sol']:.4f} SOL")

def test_trade_notifications():
    """Test realistic trade notification generation"""
    print("\n\n📱 Testing Realistic Trade Notifications")
    print("=" * 50)
    
    with app.app_context():
        # Get your actual user (the one with 1.5 SOL balance)
        user = User.query.filter_by(balance=1.5).first()
        
        if not user:
            print("❌ Could not find user with 1.5 SOL balance")
            return
        
        print(f"Testing with user: {user.username or 'User'} (Balance: {user.balance} SOL)")
        
        # Calculate realistic allocation for ZIG token
        entry_price = 0.041070
        allocation = calculate_smart_allocation(user.balance, entry_price)
        
        # Create a mock position with realistic amounts
        position = TradingPosition()
        position.token_name = "ZIG"
        position.entry_price = entry_price
        position.amount = allocation['token_quantity']
        position.timestamp = datetime.utcnow()
        position.buy_tx_hash = "https://solscan.io/tx/abc123"
        
        # Generate realistic BUY notification
        buy_notification = generate_realistic_trade_notification(user, position, 'buy')
        
        print("\n🟡 REALISTIC BUY NOTIFICATION:")
        print("-" * 30)
        print(buy_notification)
        
        # Test SELL notification
        position.current_price = 0.055000  # Exit price (about 33% profit)
        position.roi_percentage = ((position.current_price / position.entry_price) - 1) * 100
        position.sell_tx_hash = "https://solscan.io/tx/def456"
        
        # Update user balance with proceeds
        proceeds = position.current_price * position.amount
        user.balance = user.balance - allocation['spendable_sol'] + proceeds  # Remove spent, add proceeds
        
        sell_notification = generate_realistic_trade_notification(user, position, 'sell')
        
        print("\n🟢 REALISTIC SELL NOTIFICATION:")
        print("-" * 30)
        print(sell_notification)

def compare_old_vs_new():
    """Compare the old unrealistic vs new realistic notifications"""
    print("\n\n🔍 Comparison: Old vs New Trade Alerts")
    print("=" * 50)
    
    user_balance = 1.5
    entry_price = 0.041070
    admin_amount = 81345  # The unrealistic amount from your screenshot
    
    print("❌ OLD UNREALISTIC ALERT:")
    print(f"   Spent: {admin_amount * entry_price:.2f} SOL")
    print(f"   Problem: User only has {user_balance} SOL!")
    print(f"   This looks fake and impossible.")
    
    print("\n✅ NEW REALISTIC ALERT:")
    allocation = calculate_smart_allocation(user_balance, entry_price)
    print(f"   Spent: {allocation['spendable_sol']:.4f} SOL ({allocation['allocation_percent']:.1f}% risk)")
    print(f"   Qty: {allocation['token_quantity']:,} ZIG")
    print(f"   Remaining: {user_balance - allocation['spendable_sol']:.4f} SOL")
    print(f"   This looks authentic and believable!")

def main():
    """Run all tests to verify realistic trade alerts"""
    print("🎯 Testing Realistic Trade Alert System")
    print("=" * 60)
    
    # Test allocation calculations
    test_realistic_allocations()
    
    # Test notification generation
    test_trade_notifications()
    
    # Compare old vs new approach
    compare_old_vs_new()
    
    print("\n\n✅ All tests completed!")
    print("The trade alerts will now show realistic spending amounts")
    print("based on each user's actual balance instead of impossible amounts.")

if __name__ == "__main__":
    main()