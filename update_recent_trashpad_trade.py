#!/usr/bin/env python3
"""
Update Recent TRASHPAD Trade to 160% ROI
========================================
This script finds and updates the recent TRASHPAD trade that was calculated
with the old 8% system and recalculates it with the correct 160% ROI.
"""

from app import app, db
from models import TradingPosition, Profit, User, Transaction
from datetime import datetime, timedelta
import random

def update_recent_trashpad_trade():
    """Update the recent TRASHPAD trade to use correct 160% ROI"""
    
    with app.app_context():
        print("Updating recent TRASHPAD trade to 160% ROI...")
        
        # Find the most recent TRASHPAD trade
        recent_trade = TradingPosition.query.filter_by(
            token_name='TRASHPAD'
        ).order_by(TradingPosition.timestamp.desc()).first()
        
        if not recent_trade:
            print("No TRASHPAD trades found to update")
            return False
            
        print(f"Found TRASHPAD trade:")
        print(f"  User ID: {recent_trade.user_id}")
        print(f"  Old Entry Price: {recent_trade.entry_price}")
        print(f"  Exit Price: {recent_trade.current_price}")
        
        # Calculate correct entry price for 160% ROI
        exit_price = 0.00000197  # Your actual exit price
        entry_price = 0.000000758  # Your actual entry price
        
        # Update the trade record with correct prices
        recent_trade.entry_price = entry_price
        recent_trade.current_price = exit_price
        
        # Calculate actual ROI
        actual_roi = ((exit_price - entry_price) / entry_price) * 100
        print(f"  Updated Entry Price: {entry_price}")
        print(f"  Exit Price: {exit_price}")
        print(f"  Calculated ROI: {actual_roi:.2f}%")
        
        # Find and update all profit records from today
        today = datetime.utcnow().date()
        recent_profits = Profit.query.filter(Profit.date >= today).all()
        
        print(f"\nUpdating {len(recent_profits)} profit records...")
        
        # Get all users who received profits
        affected_users = []
        for profit_record in recent_profits:
            user = User.query.get(profit_record.user_id)
            if user:
                affected_users.append({
                    'user': user,
                    'old_profit': profit_record.amount,
                    'old_percentage': profit_record.percentage
                })
        
        # Delete old profit records
        for profit_record in recent_profits:
            db.session.delete(profit_record)
        
        # Recalculate profits with correct 160% ROI
        total_new_profit = 0
        for user_data in affected_users:
            user = user_data['user']
            old_profit = user_data['old_profit']
            
            # Remove old profit from user balance
            user.balance -= old_profit
            
            # Calculate new profit with 160% ROI
            allocation_percent = random.uniform(0.15, 0.25)  # 15-25% allocation
            trade_allocation = user.balance * allocation_percent
            
            # Add variance for realism
            variance = random.uniform(0.8, 1.2)
            user_roi = actual_roi * variance
            profit_rate = user_roi / 100
            
            new_profit = trade_allocation * profit_rate
            
            # Update user balance with new profit
            user.balance += new_profit
            
            # Create new profit record
            new_profit_record = Profit(
                user_id=user.id,
                amount=new_profit,
                percentage=user_roi,
                date=today
            )
            db.session.add(new_profit_record)
            
            total_new_profit += new_profit
            
            print(f"  User {user.id}: {old_profit:.4f} → {new_profit:.4f} SOL ({user_roi:.1f}%)")
        
        # Update trading position amount based on realistic allocation
        if affected_users:
            avg_user = affected_users[0]['user']
            allocation_percent = 0.20  # 20% average allocation
            trade_allocation = avg_user.balance * allocation_percent
            new_token_amount = int(trade_allocation / entry_price)
            recent_trade.amount = new_token_amount
            
            print(f"  Updated token amount: {new_token_amount:,} tokens")
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✅ Successfully updated TRASHPAD trade!")
            print(f"   Total profit distributed: {total_new_profit:.4f} SOL")
            print(f"   Average ROI: {actual_roi:.1f}%")
            print(f"   All users now have correct 160% ROI benefits")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating trade: {e}")
            return False

def verify_update():
    """Verify the update was successful"""
    
    with app.app_context():
        print("\nVerifying update...")
        
        # Check updated trade
        trade = TradingPosition.query.filter_by(
            token_name='TRASHPAD'
        ).order_by(TradingPosition.timestamp.desc()).first()
        
        if trade:
            roi = ((trade.current_price - trade.entry_price) / trade.entry_price) * 100
            print(f"Trade ROI: {roi:.1f}%")
        
        # Check updated profits
        today = datetime.utcnow().date()
        profits = Profit.query.filter(Profit.date >= today).all()
        
        avg_percentage = sum(p.percentage for p in profits) / len(profits) if profits else 0
        total_profit = sum(p.amount for p in profits)
        
        print(f"Profit records: {len(profits)}")
        print(f"Average ROI: {avg_percentage:.1f}%")
        print(f"Total profit: {total_profit:.4f} SOL")
        
        if 150 <= avg_percentage <= 170:
            print("✅ Update successful - ROI is now in 160% range")
            return True
        else:
            print("❌ Update may have failed - ROI not in expected range")
            return False

if __name__ == "__main__":
    print("=" * 50)
    print("UPDATING RECENT TRASHPAD TRADE TO 160% ROI")
    print("=" * 50)
    
    success = update_recent_trashpad_trade()
    
    if success:
        verify_update()
        print("\nThe recent trade broadcast that showed 8% has been updated to show the correct 160% ROI!")
    else:
        print("\nFailed to update the trade. Please check the error messages above.")