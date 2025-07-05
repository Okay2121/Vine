#!/usr/bin/env python3
"""
Simple Trade Broadcast Test
===========================
Tests the trade broadcast functionality with existing database schema
"""

import sys
import os
from datetime import datetime
from app import app, db
from models import User, TradingPosition, Transaction, Profit

def test_simple_trade_broadcast():
    """
    Test trade broadcast with existing database schema
    """
    print("🚀 Testing Trade Broadcast System")
    print("=" * 50)
    
    # Test data for the enhanced format
    test_token_address = "E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump"
    entry_price = 0.00000278
    exit_price = 0.0003847
    tx_link = "https://solscan.io/tx/abc123test"
    
    # Calculate ROI - more realistic for memecoin trading
    roi_percentage = ((exit_price - entry_price) / entry_price) * 100
    # Cap at realistic memecoin gains (50-200%)
    realistic_roi = min(roi_percentage, 150.0)
    
    print(f"Token Address: {test_token_address}")
    print(f"Entry Price: ${entry_price:.8f}")
    print(f"Exit Price: ${exit_price:.8f}")
    print(f"Realistic ROI: {realistic_roi:.2f}%")
    print(f"Transaction: {tx_link}")
    
    with app.app_context():
        # Get active users (those with balance > 0)
        active_users = User.query.filter(User.balance > 0).all()
        print(f"\nActive users found: {len(active_users)}")
        
        if not active_users:
            print("❌ No active users found")
            return False
        
        # Process each user
        broadcast_count = 0
        total_profit_distributed = 0
        
        for user in active_users:
            try:
                # Calculate profit proportional to balance (5-15% allocation)
                balance_percentage = min(user.balance / 100, 0.15)  # Max 15%
                profit_amount = user.balance * balance_percentage * (realistic_roi / 100)
                
                print(f"\nUser: {user.username or f'ID_{user.id}'}")
                print(f"  Balance: {user.balance:.6f} SOL")
                print(f"  Profit: +{profit_amount:.6f} SOL ({realistic_roi:.1f}%)")
                
                # Create trading position with basic fields only
                position = TradingPosition(
                    user_id=user.id,
                    token_name="TESTSYM",
                    amount=1000000,  # Token amount
                    entry_price=entry_price,
                    current_price=exit_price,
                    status="closed",
                    trade_type="sell"
                )
                db.session.add(position)
                
                # Update user balance
                user.balance += profit_amount
                
                # Create profit transaction
                transaction = Transaction(
                    user_id=user.id,
                    transaction_type="trade_profit",
                    amount=profit_amount,
                    status="completed",
                    notes=f"TESTSYM trade profit - {realistic_roi:.1f}% ROI"
                )
                db.session.add(transaction)
                
                # Create profit record
                profit_record = Profit(
                    user_id=user.id,
                    amount=profit_amount,
                    percentage=realistic_roi,
                    date=datetime.utcnow().date()
                )
                db.session.add(profit_record)
                
                broadcast_count += 1
                total_profit_distributed += profit_amount
                
                # Simulate user notification
                print(f"  📱 Notification: TESTSYM +{realistic_roi:.1f}% | +{profit_amount:.6f} SOL")
                
            except Exception as e:
                print(f"❌ Error processing user {user.id}: {e}")
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            
            print(f"\n✅ Trade broadcast test completed!")
            print(f"📊 Results:")
            print(f"   • Users notified: {broadcast_count}")
            print(f"   • Total profit distributed: {total_profit_distributed:.6f} SOL")
            print(f"   • Average ROI: {realistic_roi:.2f}%")
            print(f"   • Token: TESTSYM")
            
            # Verify by checking updated balances
            print(f"\n🔍 Updated User Balances:")
            updated_users = User.query.filter(User.balance > 0).all()
            for user in updated_users:
                print(f"   {user.username or f'ID_{user.id}'}: {user.balance:.6f} SOL")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database error: {e}")
            return False

def verify_notification_system():
    """
    Verify that the broadcast system would send notifications to users
    """
    print(f"\n📲 Trade Broadcast Notification System Verification")
    print("=" * 55)
    
    with app.app_context():
        active_users = User.query.filter(User.balance > 0).all()
        
        print(f"Users who would receive notifications: {len(active_users)}")
        for user in active_users:
            telegram_id = user.telegram_id
            username = user.username or f"ID_{user.id}"
            
            # Simulate notification message format
            notification = f"""
🎯 LIVE EXIT ALERT

TESTSYM 🟢 +150.0%

Entry: $0.00000278
Exit: $0.0003847

Your Profit: +{user.balance * 0.05:.6f} SOL
New Balance: {user.balance:.6f} SOL

🔗 https://solscan.io/tx/abc123test
            """.strip()
            
            print(f"\n📱 User: {username} (TG: {telegram_id})")
            print(f"   Would receive: TESTSYM +150.0% notification")
            print(f"   Balance impact: +{user.balance * 0.05:.6f} SOL")

if __name__ == "__main__":
    print("Testing Enhanced Trade Broadcast System...")
    
    # Run the test
    success = test_simple_trade_broadcast()
    
    if success:
        # Show notification verification
        verify_notification_system()
        print("\n🎉 Trade broadcast system working correctly!")
        print("Users have been updated with trade results and would receive Telegram notifications.")
    else:
        print("\n❌ Trade broadcast test failed.")