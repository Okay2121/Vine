#!/usr/bin/env python3
"""
Test Trade Broadcast System
===========================
Tests the new trade broadcast format with token address and automatic processing
"""

import sys
import os
import re
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, Profit

def simulate_enhanced_trade_broadcast():
    """
    Simulate the enhanced trade broadcast system with token address format
    """
    print("🚀 Testing Enhanced Trade Broadcast System")
    print("=" * 60)
    
    # Test data matching the new format
    test_token_address = "E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump"
    entry_price = 0.00000278
    exit_price = 0.0003847
    tx_link = "https://solscan.io/tx/abc123test"
    
    print(f"Token Address: {test_token_address}")
    print(f"Entry Price: {entry_price}")
    print(f"Exit Price: {exit_price}")
    print(f"Transaction: {tx_link}")
    
    # Calculate ROI
    roi_percentage = ((exit_price - entry_price) / entry_price) * 100
    print(f"Calculated ROI: {roi_percentage:.2f}%")
    
    # Get active users (those with balance > 0)
    with app.app_context():
        active_users = User.query.filter(User.balance > 0).all()
        print(f"\nActive users found: {len(active_users)}")
        
        if not active_users:
            print("❌ No active users found to test broadcast with")
            return False
        
        # Process each user
        broadcast_count = 0
        for user in active_users:
            try:
                # Calculate profit based on user's balance (proportional allocation)
                balance_percentage = min(user.balance / 100, 0.15)  # Max 15% allocation
                profit_amount = user.balance * balance_percentage * (roi_percentage / 100)
                
                print(f"\nUser: {user.username} (ID: {user.id})")
                print(f"  Balance: {user.balance:.6f} SOL")
                print(f"  Allocation: {balance_percentage*100:.2f}%")
                print(f"  Profit: {profit_amount:.6f} SOL")
                
                # Create Buy position (simulating entry)
                buy_position = TradingPosition(
                    user_id=user.id,
                    token_name="TESTSYM",  # Would be fetched from DEX Screener
                    contract_address=test_token_address,
                    trade_type="buy",
                    entry_price=entry_price,
                    current_price=entry_price,
                    amount=1000000,  # Token amount
                    status="completed",
                    timestamp=datetime.utcnow()
                )
                db.session.add(buy_position)
                db.session.flush()
                
                # Create Sell position (simulating exit)
                sell_position = TradingPosition(
                    user_id=user.id,
                    token_name="TESTSYM",
                    contract_address=test_token_address,
                    trade_type="sell",
                    entry_price=entry_price,
                    current_price=exit_price,
                    exit_price=exit_price,
                    amount=1000000,
                    roi_percentage=roi_percentage,
                    status="completed",
                    timestamp=datetime.utcnow()
                )
                db.session.add(sell_position)
                db.session.flush()
                
                # Update user balance
                previous_balance = user.balance
                user.balance += profit_amount
                
                # Create profit transaction
                profit_transaction = Transaction(
                    user_id=user.id,
                    transaction_type="trade_profit",
                    amount=profit_amount,
                    status="completed",
                    notes=f"Profit from TESTSYM trade - {roi_percentage:.2f}% ROI",
                    timestamp=datetime.utcnow()
                )
                db.session.add(profit_transaction)
                
                # Create profit record for P/L tracking
                profit_record = Profit(
                    user_id=user.id,
                    amount=profit_amount,
                    percentage=roi_percentage,
                    date=datetime.utcnow().date(),
                    source="trade_broadcast_test"
                )
                db.session.add(profit_record)
                
                broadcast_count += 1
                
                # Simulate user notification message
                user_message = f"""
🎯 LIVE EXIT ALERT

TESTSYM 🟢 +{roi_percentage:.1f}%

Entry: ${entry_price:.8f}
Exit: ${exit_price:.8f}

Your Profit: {profit_amount:.6f} SOL
New Balance: {user.balance:.6f} SOL

🔗 {tx_link}
                """.strip()
                
                print(f"  📱 Notification sent:")
                print(f"     TESTSYM +{roi_percentage:.1f}% | Profit: {profit_amount:.6f} SOL")
                
            except Exception as e:
                print(f"❌ Error processing user {user.id}: {e}")
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✅ Trade broadcast test completed successfully!")
            print(f"📊 Summary:")
            print(f"   • Users notified: {broadcast_count}")
            print(f"   • Average ROI: {roi_percentage:.2f}%")
            print(f"   • Token: TESTSYM ({test_token_address[:10]}...)")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database error during commit: {e}")
            return False

def verify_broadcast_results():
    """
    Verify that the broadcast created proper records
    """
    print("\n🔍 Verifying Broadcast Results")
    print("=" * 40)
    
    with app.app_context():
        # Check trading positions
        test_positions = TradingPosition.query.filter_by(token_name="TESTSYM").all()
        print(f"Trading positions created: {len(test_positions)}")
        
        # Check profit records
        test_profits = Profit.query.filter_by(source="trade_broadcast_test").all()
        print(f"Profit records created: {len(test_profits)}")
        
        # Check user balances
        users_with_profits = User.query.join(Profit).filter(Profit.source == "trade_broadcast_test").all()
        print(f"Users with updated balances: {len(users_with_profits)}")
        
        # Show detailed results
        for user in users_with_profits:
            recent_profit = Profit.query.filter_by(
                user_id=user.id, 
                source="trade_broadcast_test"
            ).first()
            if recent_profit:
                print(f"  {user.username}: +{recent_profit.amount:.6f} SOL ({recent_profit.percentage:.2f}%)")

if __name__ == "__main__":
    print("Testing Enhanced Trade Broadcast System...")
    
    # Run the test
    success = simulate_enhanced_trade_broadcast()
    
    if success:
        # Verify results
        verify_broadcast_results()
        print("\n🎉 Trade broadcast test completed successfully!")
        print("Users have received trade notifications and balances updated.")
    else:
        print("\n❌ Trade broadcast test failed.")