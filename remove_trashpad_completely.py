#!/usr/bin/env python3
"""
Complete TRASHPAD Trade Removal
===============================
This script completely removes all TRASHPAD-related records from the database
and reverts user balances as if the trades never happened.
"""

from app import app, db
from models import TradingPosition, Transaction, Profit, User
from datetime import datetime

def remove_trashpad_completely():
    """Remove all TRASHPAD trades and revert user balances"""
    
    with app.app_context():
        print("=" * 60)
        print("COMPLETE TRASHPAD TRADE REMOVAL")
        print("=" * 60)
        
        # Step 1: Find all TRASHPAD-related records
        print("1. Finding TRASHPAD-related records...")
        
        trashpad_positions = TradingPosition.query.filter_by(token_name='TRASHPAD').all()
        print(f"   Found {len(trashpad_positions)} TRASHPAD positions")
        
        # Get affected user IDs
        affected_user_ids = set()
        for position in trashpad_positions:
            affected_user_ids.add(position.user_id)
        
        print(f"   Affects {len(affected_user_ids)} users")
        
        # Step 2: Find and remove TRASHPAD profit records
        print("\n2. Removing TRASHPAD profit records...")
        
        trashpad_profits = Profit.query.filter(
            Profit.user_id.in_(affected_user_ids),
            Profit.date >= datetime(2025, 6, 21)  # Today's TRASHPAD trades
        ).all()
        
        removed_profits = 0
        profit_amounts_to_revert = {}
        
        for profit in trashpad_profits:
            # Track profit amounts to revert from user balances
            user_id = profit.user_id
            profit_amount = profit.amount if hasattr(profit, 'amount') else 0
            
            if user_id not in profit_amounts_to_revert:
                profit_amounts_to_revert[user_id] = 0
            profit_amounts_to_revert[user_id] += profit_amount
            
            print(f"   Removing profit record: User {user_id}, Amount: {profit_amount} SOL")
            db.session.delete(profit)
            removed_profits += 1
        
        print(f"   Removed {removed_profits} profit records")
        
        # Step 3: Find and remove TRASHPAD transaction records
        print("\n3. Removing TRASHPAD transaction records...")
        
        trashpad_transactions = Transaction.query.filter(
            Transaction.user_id.in_(affected_user_ids),
            Transaction.transaction_type.in_(['trade_profit', 'trade_loss']),
            Transaction.timestamp >= datetime(2025, 6, 21)
        ).all()
        
        removed_transactions = 0
        for transaction in trashpad_transactions:
            print(f"   Removing transaction: User {transaction.user_id}, Type: {transaction.transaction_type}, Amount: {transaction.amount}")
            db.session.delete(transaction)
            removed_transactions += 1
        
        print(f"   Removed {removed_transactions} transaction records")
        
        # Step 4: Remove TRASHPAD trading positions
        print("\n4. Removing TRASHPAD trading positions...")
        
        removed_positions = 0
        for position in trashpad_positions:
            print(f"   Removing position: User {position.user_id}, Entry: {position.entry_price}, Exit: {position.current_price}")
            db.session.delete(position)
            removed_positions += 1
        
        print(f"   Removed {removed_positions} trading positions")
        
        # Step 5: Revert user balances
        print("\n5. Reverting user balances...")
        
        reverted_users = 0
        for user_id, profit_amount in profit_amounts_to_revert.items():
            user = User.query.get(user_id)
            if user and profit_amount > 0:
                old_balance = user.balance
                user.balance = max(0, user.balance - profit_amount)  # Don't go negative
                print(f"   User {user_id}: {old_balance:.4f} → {user.balance:.4f} SOL (reverted {profit_amount:.4f})")
                reverted_users += 1
        
        print(f"   Reverted balances for {reverted_users} users")
        
        # Step 6: Commit all changes
        print("\n6. Committing changes...")
        
        try:
            db.session.commit()
            print("   ✅ All changes committed successfully")
            
            # Final verification
            print("\n7. Verification...")
            remaining_positions = TradingPosition.query.filter_by(token_name='TRASHPAD').count()
            print(f"   Remaining TRASHPAD positions: {remaining_positions}")
            
            if remaining_positions == 0:
                print("   ✅ All TRASHPAD trades completely removed")
                return True
            else:
                print("   ❌ Some TRASHPAD records may still exist")
                return False
                
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Error committing changes: {e}")
            return False

def verify_removal():
    """Verify that all TRASHPAD traces are removed"""
    
    with app.app_context():
        print("\n" + "=" * 60)
        print("VERIFICATION OF TRASHPAD REMOVAL")
        print("=" * 60)
        
        # Check positions
        positions = TradingPosition.query.filter_by(token_name='TRASHPAD').count()
        print(f"TRASHPAD positions remaining: {positions}")
        
        # Check recent profits (today)
        recent_profits = Profit.query.filter(
            Profit.date >= datetime(2025, 6, 21)
        ).count()
        print(f"Recent profit records (today): {recent_profits}")
        
        # Check user balances (show sample)
        users = User.query.filter(User.balance > 0).limit(5).all()
        print(f"\nSample user balances after removal:")
        for user in users:
            print(f"  User {user.id}: {user.balance:.4f} SOL")
        
        if positions == 0:
            print("\n✅ TRASHPAD completely removed from all systems")
        else:
            print("\n❌ TRASHPAD traces still exist")

if __name__ == "__main__":
    success = remove_trashpad_completely()
    
    if success:
        verify_removal()
        print("\n🎯 TRASHPAD trades have been completely removed!")
        print("   - All positions deleted")
        print("   - All profit records removed") 
        print("   - All transaction records deleted")
        print("   - User balances reverted")
        print("   - Live positions will no longer show TRASHPAD")
    else:
        print("\n❌ Removal failed. Check error messages above.")