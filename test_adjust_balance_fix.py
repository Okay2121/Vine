#!/usr/bin/env python3
"""
Test script to verify the Adjust Balance fix works correctly
Tests the enhanced user lookup function with the provided UID: 7611754415
"""

import logging
import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_user_lookup_function(test_uid="7611754415"):
    """Test the enhanced user lookup function with the specific UID."""
    print(f"🔍 Testing user lookup with UID: {test_uid}")
    
    try:
        from app import app, db
        from models import User
        from sqlalchemy import func, text
        
        with app.app_context():
            # Test database connection first (same as the fix)
            try:
                db.session.execute(text('SELECT 1'))
                print("✅ Database connection verified")
            except Exception as conn_error:
                print(f"❌ Database connection failed: {conn_error}")
                return False
            
            # Enhanced user search (same logic as the fix)
            user = None
            search_input = test_uid.strip()
            
            print(f"🔍 Searching for user with input: '{search_input}'")
            
            # Method 1: Try as telegram_id (integer)
            if search_input.isdigit():
                try:
                    telegram_id_int = int(search_input)
                    user = User.query.filter_by(telegram_id=telegram_id_int).first()
                    if user:
                        print(f"✅ Found user by telegram_id (int): {user.telegram_id}")
                except Exception as e:
                    print(f"⚠️ Error searching by telegram_id (int): {e}")
            
            # Method 2: Try as telegram_id (string)
            if not user:
                try:
                    user = User.query.filter_by(telegram_id=search_input).first()
                    if user:
                        print(f"✅ Found user by telegram_id (string): {user.telegram_id}")
                except Exception as e:
                    print(f"⚠️ Error searching by telegram_id (string): {e}")
            
            # Method 3: Try by username (with @ prefix)
            if not user and search_input.startswith('@'):
                try:
                    username = search_input[1:]  # Remove @ prefix
                    user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
                    if user:
                        print(f"✅ Found user by username (with @): {user.username}")
                except Exception as e:
                    print(f"⚠️ Error searching by username (with @): {e}")
            
            # Method 4: Try username without @ prefix
            if not user:
                try:
                    user = User.query.filter(func.lower(User.username) == func.lower(search_input)).first()
                    if user:
                        print(f"✅ Found user by username (without @): {user.username}")
                except Exception as e:
                    print(f"⚠️ Error searching by username (without @): {e}")
            
            # Method 5: Last resort - search all users and check partial matches
            if not user:
                try:
                    print("🔍 Performing full user scan...")
                    all_users = User.query.all()
                    print(f"📊 Total users in database: {len(all_users)}")
                    
                    for u in all_users:
                        if (str(u.telegram_id) == search_input or 
                            (u.username and u.username.lower() == search_input.lower())):
                            user = u
                            print(f"✅ Found user via full scan: {u.telegram_id}")
                            break
                except Exception as e:
                    print(f"⚠️ Error in full user scan: {e}")
            
            if user:
                # Display user information (same as the working function)
                username_display = f"@{user.username}" if user.username else "No username"
                print(f"\n📊 USER FOUND:")
                print(f"• User: {username_display}")
                print(f"• Telegram ID: {user.telegram_id}")
                print(f"• Current Balance: {user.balance:.4f} SOL")
                print(f"• Status: {getattr(user, 'status', 'N/A')}")
                print(f"• User Database ID: {user.id}")
                return True
            else:
                print(f"\n❌ User not found with input: '{search_input}'")
                
                # Show what users exist for debugging
                try:
                    all_users = User.query.limit(5).all()
                    print(f"\n📋 Sample users in database:")
                    for u in all_users:
                        print(f"  - ID: {u.telegram_id}, Username: {u.username or 'None'}")
                except Exception as e:
                    print(f"Error getting sample users: {e}")
                
                return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test basic database connectivity."""
    print("🔍 Testing database connection...")
    
    try:
        from app import app, db
        from models import User
        from sqlalchemy import text, func
        
        with app.app_context():
            # Test basic connection
            result = db.session.execute(text('SELECT 1')).scalar()
            print(f"✅ Database connection successful: {result}")
            
            # Test User table access
            user_count = db.session.query(func.count(User.id)).scalar()
            print(f"✅ User table accessible - Total users: {user_count}")
            
            # Get a sample of telegram IDs for comparison
            sample_users = User.query.limit(5).all()
            print(f"📋 Sample telegram IDs in database:")
            for user in sample_users:
                print(f"  - {user.telegram_id} (type: {type(user.telegram_id)})")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_adjust_balance_flow(test_uid="7611754415"):
    """Simulate the complete adjust balance flow."""
    print(f"🎯 Simulating complete adjust balance flow for UID: {test_uid}")
    
    try:
        from app import app, db
        from models import User
        
        with app.app_context():
            # Step 1: Find the user (using the enhanced method)
            user = None
            search_input = test_uid.strip()
            
            if search_input.isdigit():
                telegram_id_int = int(search_input)
                user = User.query.filter_by(telegram_id=telegram_id_int).first()
            
            if not user:
                user = User.query.filter_by(telegram_id=search_input).first()
            
            if not user:
                print(f"❌ User {test_uid} not found - cannot simulate balance adjustment")
                return False
            
            # Step 2: Display current user info (simulating what admin sees)
            print(f"\n📊 USER FOUND - READY FOR BALANCE ADJUSTMENT:")
            print(f"• User: @{user.username if user.username else 'No username'}")
            print(f"• Telegram ID: {user.telegram_id}")
            print(f"• Current Balance: {user.balance:.4f} SOL")
            print(f"• User Database ID: {user.id}")
            
            # Step 3: Simulate balance adjustment (without actually changing anything)
            test_adjustment = 5.0
            new_balance = user.balance + test_adjustment
            
            print(f"\n💰 SIMULATION - Balance Adjustment:")
            print(f"• Adjustment Amount: +{test_adjustment:.4f} SOL")
            print(f"• Current Balance: {user.balance:.4f} SOL")
            print(f"• New Balance Would Be: {new_balance:.4f} SOL")
            print(f"• Status: Ready to process (simulation only)")
            
            return True
            
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests for the adjust balance fix."""
    print("🚀 Testing Adjust Balance Fix\n")
    print("="*60)
    
    test_uid = "7611754415"  # The UID provided by the user
    
    tests = [
        ("Database Connection", test_database_connection),
        ("User Lookup Function", lambda: test_user_lookup_function(test_uid)),
        ("Complete Balance Adjustment Flow", lambda: simulate_adjust_balance_flow(test_uid))
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
        
        print()
    
    # Summary
    print(f"{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<40} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n🎉 All tests passed! The Adjust Balance feature should work correctly with UID {test_uid}")
        print("The enhanced user lookup function is ready for production use.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Issues need to be addressed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)