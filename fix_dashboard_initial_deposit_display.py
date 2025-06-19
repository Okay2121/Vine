#!/usr/bin/env python
"""
Fix Dashboard Initial Deposit Display
====================================
Ensures all users show correct cumulative initial deposit values in dashboard
"""

import logging
from app import app, db
from models import User, Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_all_user_initial_deposits():
    """Fix initial_deposit for all users to reflect cumulative behavior"""
    
    with app.app_context():
        try:
            # Get all users
            all_users = User.query.all()
            
            print(f"Checking {len(all_users)} users for initial deposit corrections")
            print("=" * 60)
            
            fixed_count = 0
            
            for user in all_users:
                # Calculate total deposits and admin credits
                total_baseline = db.session.query(db.func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type.in_(['deposit', 'admin_credit']),
                    Transaction.status == 'completed'
                ).scalar() or 0.0
                
                # Check if initial_deposit needs correction
                if abs(user.initial_deposit - total_baseline) > 0.001:
                    old_initial = user.initial_deposit
                    user.initial_deposit = total_baseline
                    
                    print(f"User: {user.username} (TG: {user.telegram_id})")
                    print(f"  Old initial: {old_initial:.6f} SOL")
                    print(f"  New initial: {total_baseline:.6f} SOL")
                    print(f"  Current balance: {user.balance:.6f} SOL")
                    
                    fixed_count += 1
                    
                    # Calculate what dashboard will now show
                    profit_loss = user.balance - total_baseline
                    percentage = (profit_loss / total_baseline * 100) if total_baseline > 0 else 0
                    
                    print(f"  Dashboard will show:")
                    print(f"    Initial: {total_baseline:.2f} SOL")
                    print(f"    Current: {user.balance:.2f} SOL")
                    print(f"    P/L: {profit_loss:+.2f} SOL ({percentage:+.1f}%)")
                    print()
            
            # Commit all changes
            if fixed_count > 0:
                db.session.commit()
                print(f"✅ Fixed initial_deposit for {fixed_count} users")
                print("✅ Dashboard will now show correct cumulative values")
            else:
                print("✅ All users already have correct initial_deposit values")
                
            return fixed_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error fixing initial deposits: {e}")
            import traceback
            traceback.print_exc()
            return 0


def verify_dashboard_calculations():
    """Verify dashboard calculations are correct for all users"""
    
    with app.app_context():
        print("\nVERIFYING DASHBOARD CALCULATIONS:")
        print("=" * 40)
        
        users_with_activity = User.query.filter(User.balance > 0).all()
        
        for user in users_with_activity:
            # Get transaction history
            deposits = Transaction.query.filter_by(
                user_id=user.id,
                transaction_type='deposit'
            ).all()
            
            admin_credits = Transaction.query.filter_by(
                user_id=user.id,
                transaction_type='admin_credit'
            ).all()
            
            total_deposits = sum(d.amount for d in deposits)
            total_credits = sum(c.amount for c in admin_credits)
            total_baseline = total_deposits + total_credits
            
            profit_loss = user.balance - user.initial_deposit
            percentage = (profit_loss / user.initial_deposit * 100) if user.initial_deposit > 0 else 0
            
            print(f"User: {user.username}")
            print(f"  Deposits: {total_deposits:.4f} SOL ({len(deposits)} transactions)")
            print(f"  Admin Credits: {total_credits:.4f} SOL ({len(admin_credits)} transactions)")
            print(f"  Total Baseline: {total_baseline:.4f} SOL")
            print(f"  Current Initial: {user.initial_deposit:.4f} SOL")
            print(f"  Current Balance: {user.balance:.4f} SOL")
            
            if abs(user.initial_deposit - total_baseline) < 0.001:
                print(f"  ✅ Dashboard shows: Initial {user.initial_deposit:.2f} SOL, P/L {profit_loss:+.2f} SOL ({percentage:+.1f}%)")
            else:
                print(f"  ❌ Mismatch detected!")
            print()


if __name__ == "__main__":
    print("FIXING DASHBOARD INITIAL DEPOSIT DISPLAY")
    print("=" * 50)
    
    # Fix all users
    fixed_count = fix_all_user_initial_deposits()
    
    # Verify calculations
    verify_dashboard_calculations()
    
    print("\n🎯 DASHBOARD FIX COMPLETE")
    print("Users will now see correct cumulative initial deposit values")
    print("Performance calculations will be accurate")