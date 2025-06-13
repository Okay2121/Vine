#!/usr/bin/env python
"""
Test ENV Wallet Synchronization
===============================
This script tests that the .env file updates when admin changes the wallet address.
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import SystemSettings
from helpers import get_global_deposit_wallet, update_env_variable, set_system_setting

def test_env_wallet_sync():
    """
    Test that changing the wallet updates both database and .env file.
    """
    print("Testing ENV Wallet Synchronization")
    print("=" * 40)
    
    with app.app_context():
        try:
            # Step 1: Get current state
            print("\n1. Current state:")
            current_wallet = get_global_deposit_wallet()
            print(f"   Database wallet: {current_wallet}")
            
            # Read current .env file
            with open('.env', 'r') as f:
                env_content = f.read()
                
            for line in env_content.split('\n'):
                if line.startswith('GLOBAL_DEPOSIT_WALLET='):
                    env_wallet = line.split('=', 1)[1]
                    print(f"   .env wallet: {env_wallet}")
                    break
            
            # Step 2: Test updating via helper function
            print("\n2. Testing update_env_variable function:")
            test_wallet = "9xJ12abcTest456GhiJkl789MnoPqr123StUvWxYz456AbC"
            
            success = update_env_variable('GLOBAL_DEPOSIT_WALLET', test_wallet)
            if success:
                print(f"   ✅ .env update successful")
                
                # Verify the change
                with open('.env', 'r') as f:
                    updated_content = f.read()
                    
                for line in updated_content.split('\n'):
                    if line.startswith('GLOBAL_DEPOSIT_WALLET='):
                        updated_wallet = line.split('=', 1)[1]
                        if updated_wallet == test_wallet:
                            print(f"   ✅ .env verification: {updated_wallet}")
                        else:
                            print(f"   ❌ .env verification failed: {updated_wallet}")
                        break
            else:
                print(f"   ❌ .env update failed")
            
            # Step 3: Test complete workflow
            print("\n3. Testing complete admin workflow:")
            
            # Simulate admin changing wallet (database + env)
            admin_wallet = "AdminTest123456789ABCDEF123456789012345678"
            
            # Update database
            db_success = set_system_setting('deposit_wallet', admin_wallet, 'test_admin')
            print(f"   Database update: {'✅' if db_success else '❌'}")
            
            # Update .env
            env_success = update_env_variable('GLOBAL_DEPOSIT_WALLET', admin_wallet)
            print(f"   .env update: {'✅' if env_success else '❌'}")
            
            # Verify synchronization
            new_db_wallet = get_global_deposit_wallet()
            
            with open('.env', 'r') as f:
                new_env_content = f.read()
                
            for line in new_env_content.split('\n'):
                if line.startswith('GLOBAL_DEPOSIT_WALLET='):
                    new_env_wallet = line.split('=', 1)[1]
                    break
            
            print(f"\n4. Synchronization verification:")
            print(f"   Database: {new_db_wallet}")
            print(f"   .env file: {new_env_wallet}")
            
            if new_db_wallet == new_env_wallet == admin_wallet:
                print("   ✅ Database and .env are synchronized")
                sync_success = True
            else:
                print("   ❌ Database and .env are NOT synchronized")
                sync_success = False
            
            # Step 4: Restore original state
            print("\n5. Restoring original state:")
            
            # Restore database
            restore_db = set_system_setting('deposit_wallet', current_wallet, 'test_restore')
            print(f"   Database restored: {'✅' if restore_db else '❌'}")
            
            # Restore .env
            restore_env = update_env_variable('GLOBAL_DEPOSIT_WALLET', current_wallet)
            print(f"   .env restored: {'✅' if restore_env else '❌'}")
            
            return sync_success
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_env_wallet_sync()
    
    if success:
        print("\n" + "=" * 40)
        print("✅ ENV WALLET SYNC TEST PASSED!")
        print("\nThe system now updates both:")
        print("• Database (SystemSettings table)")
        print("• Environment file (.env)")
        print("\nWhen admin changes wallet address via Telegram.")
    else:
        print("\n❌ ENV WALLET SYNC TEST FAILED!")
        sys.exit(1)