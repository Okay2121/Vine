#!/usr/bin/env python
"""
Fix Deposit Wallet Unique Constraint
====================================
This script removes the unique constraint on the deposit_wallet column
to allow multiple users to share the same global deposit wallet address.
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
import logging

def fix_deposit_wallet_constraint():
    """
    Remove the unique constraint on User.deposit_wallet column.
    """
    print("🔧 Fixing deposit wallet unique constraint...")
    
    with app.app_context():
        try:
            # Drop the existing unique constraint on deposit_wallet
            print("1. Dropping unique constraint on deposit_wallet...")
            
            # Execute the SQL to drop the constraint using proper SQLAlchemy syntax
            with db.engine.connect() as connection:
                connection.execute(db.text("ALTER TABLE \"user\" DROP CONSTRAINT IF EXISTS user_deposit_wallet_key;"))
                connection.commit()
            
            print("   ✅ Unique constraint removed successfully")
            
            # Verify the constraint is gone by checking existing users
            from models import User
            users = User.query.all()
            print(f"2. Found {len(users)} existing users")
            
            # Update all users to use the current global deposit wallet
            from helpers import get_global_deposit_wallet, update_all_user_deposit_wallets
            
            current_wallet = get_global_deposit_wallet()
            print(f"3. Current global wallet: {current_wallet}")
            
            updated_count = update_all_user_deposit_wallets()
            print(f"   ✅ Updated {updated_count} users to use global wallet")
            
            print("\n" + "=" * 50)
            print("🎉 DEPOSIT WALLET CONSTRAINT FIX COMPLETED!")
            print("\nNow all users can share the same global deposit wallet address.")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Fix failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("Deposit Wallet Constraint Fix")
    print("=============================")
    
    success = fix_deposit_wallet_constraint()
    
    if success:
        print("\n✅ Constraint fix completed successfully!")
    else:
        print("\n❌ Constraint fix failed. Please check the implementation.")
        sys.exit(1)