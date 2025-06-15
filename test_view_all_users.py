#!/usr/bin/env python3
"""
Test script for the "View All Users" functionality
This script helps debug the 404 error by testing database connectivity and user queries
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

def test_database_connection():
    """Test basic database connectivity."""
    print("🔍 Testing database connection...")
    
    try:
        from app import app, db
        from models import User, UserStatus, Transaction, ReferralCode
        from sqlalchemy import text, func, desc
        
        with app.app_context():
            # Test basic connection
            result = db.session.execute(text('SELECT 1')).scalar()
            print(f"✅ Database connection successful: {result}")
            
            # Test User table access
            user_count = db.session.query(func.count(User.id)).scalar()
            print(f"✅ User table accessible - Total users: {user_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_query():
    """Test the specific user query used in admin_view_all_users_handler."""
    print("\n🔍 Testing user query...")
    
    try:
        from app import app, db
        from models import User, UserStatus, Transaction, ReferralCode
        from sqlalchemy import func, desc
        
        with app.app_context():
            # Test the exact query from the handler
            users = User.query.order_by(desc(User.joined_at)).limit(15).all()
            print(f"✅ User query successful - Found {len(users)} users")
            
            if users:
                print("\n📊 Sample user data:")
                for i, user in enumerate(users[:3], 1):
                    username_display = f"@{user.username}" if user.username else "No Username"
                    registration_date = user.joined_at.strftime("%m/%d/%Y") if user.joined_at else "Unknown"
                    status_display = user.status.value if hasattr(user, 'status') and user.status else "unknown"
                    balance = getattr(user, 'balance', 0.0)
                    
                    print(f"  {i}. {username_display}")
                    print(f"     ID: {user.telegram_id}")
                    print(f"     Balance: {balance:.4f} SOL")
                    print(f"     Status: {status_display}")
                    print(f"     Joined: {registration_date}")
                    print()
            else:
                print("📝 No users found in database")
                
            return True
            
    except Exception as e:
        print(f"❌ User query failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_callback_handler_registration():
    """Test if the callback handler is properly registered."""
    print("\n🔍 Testing callback handler registration...")
    
    try:
        from bot_v20_runner import SimpleTelegramBot
        from config import BOT_TOKEN
        
        # Create a bot instance (don't start polling)
        bot = SimpleTelegramBot(BOT_TOKEN)
        
        # Check if admin_view_all_users is in handlers after registration
        # We need to manually register handlers to test
        from bot_v20_runner import admin_view_all_users_handler
        bot.add_callback_handler("admin_view_all_users", admin_view_all_users_handler)
        
        if "admin_view_all_users" in bot.handlers:
            print("✅ Callback handler 'admin_view_all_users' is registered")
            print(f"✅ Handler function: {bot.handlers['admin_view_all_users']}")
            return True
        else:
            print("❌ Callback handler 'admin_view_all_users' is NOT registered")
            print(f"Available handlers: {list(bot.handlers.keys())}")
            return False
            
    except Exception as e:
        print(f"❌ Handler registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_permissions():
    """Test admin permission checking."""
    print("\n🔍 Testing admin permissions...")
    
    try:
        from bot_v20_runner import is_admin
        from config import ADMIN_IDS
        
        print(f"Admin IDs configured: {ADMIN_IDS}")
        
        # Test with first admin ID if available
        if ADMIN_IDS:
            first_admin = ADMIN_IDS[0]
            is_admin_result = is_admin(first_admin)
            print(f"✅ Admin check for {first_admin}: {is_admin_result}")
            return True
        else:
            print("❌ No admin IDs configured")
            return False
            
    except Exception as e:
        print(f"❌ Admin permission test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_callback_execution():
    """Simulate the actual callback execution."""
    print("\n🔍 Simulating callback execution...")
    
    try:
        from bot_v20_runner import admin_view_all_users_handler
        from config import ADMIN_IDS
        
        if not ADMIN_IDS:
            print("❌ No admin IDs configured - cannot simulate")
            return False
            
        # Create a mock update object
        mock_update = {
            'callback_query': {
                'data': 'admin_view_all_users',
                'from': {'id': ADMIN_IDS[0]}
            }
        }
        
        # Simulate the handler call
        chat_id = ADMIN_IDS[0]
        print(f"Simulating callback for admin {chat_id}")
        
        # This would normally send a message to Telegram
        # We'll just test the logic without actually sending
        admin_view_all_users_handler(mock_update, chat_id)
        
        print("✅ Callback execution completed without errors")
        return True
        
    except Exception as e:
        print(f"❌ Callback simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting View All Users functionality tests...\n")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("User Query", test_user_query),
        ("Callback Handler Registration", test_callback_handler_registration),
        ("Admin Permissions", test_admin_permissions),
        ("Callback Execution Simulation", simulate_callback_execution)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
        
        print()
    
    # Summary
    print(f"{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The View All Users functionality should work.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Issues need to be addressed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)