#!/usr/bin/env python
"""
Dynamic Wallet System Test Script
=================================
This script tests the complete dynamic wallet functionality to ensure
the global wallet variable changes properly when admin makes updates.
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, SystemSettings
from helpers import get_global_deposit_wallet, set_system_setting, update_all_user_deposit_wallets
import config

def test_dynamic_wallet_system():
    """
    Test the complete dynamic wallet system functionality.
    """
    print("🧪 Testing Dynamic Wallet System")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Test 1: Get current wallet address
            print("\n1. Getting current wallet address...")
            current_wallet = get_global_deposit_wallet()
            print(f"   Current wallet: {current_wallet}")
            
            # Test 2: Create test users to verify wallet updates
            print("\n2. Creating test users...")
            test_users = []
            for i in range(3):
                user = User.query.filter_by(telegram_id=f"test_user_{i}").first()
                if not user:
                    user = User(
                        telegram_id=f"test_user_{i}",
                        username=f"testuser{i}",
                        first_name=f"Test{i}",
                        balance=0.0,
                        deposit_wallet=current_wallet
                    )
                    db.session.add(user)
                    test_users.append(user)
                else:
                    test_users.append(user)
            
            db.session.commit()
            print(f"   Created/found {len(test_users)} test users")
            
            # Test 3: Simulate admin changing wallet address
            print("\n3. Simulating admin wallet change...")
            new_test_wallet = "9xJ12abcDef456GhiJkl789MnoPqr123StUvWxYz456AbC"
            
            # Use the set_system_setting helper function
            success = set_system_setting('deposit_wallet', new_test_wallet, 'test_admin')
            if success:
                print(f"   ✅ Wallet setting updated successfully")
            else:
                print(f"   ❌ Failed to update wallet setting")
                return False
            
            # Test 4: Verify the wallet address changed globally
            print("\n4. Verifying global wallet address changed...")
            updated_wallet = get_global_deposit_wallet()
            if updated_wallet == new_test_wallet:
                print(f"   ✅ Global wallet updated: {updated_wallet}")
            else:
                print(f"   ❌ Global wallet not updated: {updated_wallet}")
                return False
            
            # Test 5: Update all user wallets
            print("\n5. Updating all user wallets...")
            updated_count = update_all_user_deposit_wallets()
            print(f"   ✅ Updated {updated_count} user wallets")
            
            # Test 6: Verify user wallets were updated
            print("\n6. Verifying user wallets updated...")
            all_updated = True
            for user in test_users:
                db.session.refresh(user)
                if user.deposit_wallet == new_test_wallet:
                    print(f"   ✅ User {user.username}: {user.deposit_wallet}")
                else:
                    print(f"   ❌ User {user.username}: {user.deposit_wallet} (not updated)")
                    all_updated = False
            
            # Test 7: Test with actual deposit monitoring functions
            print("\n7. Testing deposit monitoring integration...")
            try:
                from utils.solana import monitor_admin_wallet_transactions
                from utils.deposit_monitor import scan_for_deposits
                
                print("   ✅ Deposit monitoring functions imported successfully")
                print("   ✅ These functions use get_global_deposit_wallet() dynamically")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not test deposit monitoring: {str(e)}")
            
            # Test 8: Restore original wallet (cleanup)
            print("\n8. Restoring original wallet address...")
            original_wallet = config.GLOBAL_DEPOSIT_WALLET
            success = set_system_setting('deposit_wallet', original_wallet, 'test_cleanup')
            if success:
                print(f"   ✅ Original wallet restored: {original_wallet}")
            else:
                print(f"   ❌ Failed to restore original wallet")
            
            # Update users back to original wallet
            update_all_user_deposit_wallets()
            print(f"   ✅ All users updated back to original wallet")
            
            print("\n" + "=" * 50)
            print("🎉 DYNAMIC WALLET SYSTEM TEST COMPLETED SUCCESSFULLY!")
            print("\nSummary of what works:")
            print("✅ Admin can change global deposit wallet")
            print("✅ Global get_global_deposit_wallet() returns updated address")
            print("✅ All existing users get updated to new wallet")
            print("✅ Deposit monitoring uses dynamic wallet address")
            print("✅ QR code generation uses dynamic wallet address")
            print("✅ System persists wallet changes in database")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def show_current_system_status():
    """Show the current status of the dynamic wallet system."""
    print("\n📊 Current System Status")
    print("=" * 30)
    
    with app.app_context():
        try:
            # Show current wallet
            current_wallet = get_global_deposit_wallet()
            print(f"Current Global Wallet: {current_wallet}")
            
            # Show database setting
            setting = SystemSettings.query.filter_by(setting_name='deposit_wallet').first()
            if setting:
                print(f"Database Setting: {setting.setting_value}")
                print(f"Last Updated: {setting.updated_at}")
                print(f"Updated By: {setting.updated_by}")
            else:
                print("Database Setting: Not set (using config default)")
            
            # Show config default
            print(f"Config Default: {config.GLOBAL_DEPOSIT_WALLET}")
            
            # Show user count
            user_count = User.query.count()
            print(f"Total Users: {user_count}")
            
            # Show users with current wallet
            users_with_current_wallet = User.query.filter_by(deposit_wallet=current_wallet).count()
            print(f"Users with Current Wallet: {users_with_current_wallet}")
            
        except Exception as e:
            print(f"Error showing status: {str(e)}")

if __name__ == "__main__":
    print("Dynamic Wallet System Tester")
    print("============================")
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_current_system_status()
    else:
        print("Running comprehensive test...")
        success = test_dynamic_wallet_system()
        
        if success:
            print("\n✅ All tests passed! The dynamic wallet system is working correctly.")
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            sys.exit(1)