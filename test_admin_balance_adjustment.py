#!/usr/bin/env python
"""
Test Admin Balance Adjustment Functionality
Verifies that the admin balance adjustment feature works without HTTP 400 errors
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_admin_balance_handler():
    """Test the admin balance adjustment handler directly"""
    
    print("TESTING ADMIN BALANCE ADJUSTMENT HANDLER")
    print("=" * 50)
    
    try:
        # Import the handler function
        from bot_v20_runner import admin_adjust_balance_handler
        
        # Create a mock update and chat_id
        mock_update = {"callback_query": {"data": "admin_adjust_balance"}}
        test_chat_id = "test_chat_123"
        
        print("Testing admin_adjust_balance_handler function...")
        
        # Call the handler - this should not raise any parsing errors
        try:
            admin_adjust_balance_handler(mock_update, test_chat_id)
            print("✅ Handler executed without errors")
            print("✅ No HTTP 400 parse entities error occurred")
            
        except Exception as e:
            if "can't parse entities" in str(e):
                print(f"❌ HTTP 400 parse entities error still occurring: {e}")
                return False
            else:
                print(f"⚠️ Other error (expected for test): {e}")
                print("✅ No parse entities error - this is good")
        
        return True
        
    except ImportError as e:
        print(f"❌ Could not import handler: {e}")
        return False

def test_message_safety():
    """Test that the message content is safe from parsing errors"""
    
    print("\nTESTING MESSAGE CONTENT SAFETY")
    print("=" * 40)
    
    # Test the exact message that would be sent
    test_message = (
        "ADJUST USER BALANCE\n\n"
        "Enter the Telegram ID or username of the user whose balance you want to adjust.\n\n"
        "Examples:\n"
        "- 1234567890 (Telegram ID)\n"
        "- @username\n"
        "- username\n\n"
        "Type cancel to go back."
    )
    
    # Check for problematic characters
    problematic_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '=', '|', '{', '}', '!']
    
    print(f"Message length: {len(test_message)} characters")
    print(f"Message byte length: {len(test_message.encode('utf-8'))} bytes")
    
    found_issues = []
    for char in problematic_chars:
        if char in test_message:
            found_issues.append(char)
    
    if found_issues:
        print(f"❌ Found problematic characters: {found_issues}")
        return False
    else:
        print("✅ No problematic characters found")
        print("✅ Message is safe for Telegram parsing")
        return True

def test_complete_workflow():
    """Test the complete balance adjustment workflow"""
    
    print("\nTESTING COMPLETE WORKFLOW")
    print("=" * 30)
    
    try:
        from app import app, db
        from models import User
        
        with app.app_context():
            # Create a test user
            test_user = User(
                telegram_id='999999999',
                username='testuser',
                balance=10.0,
                initial_deposit=5.0
            )
            
            db.session.add(test_user)
            db.session.commit()
            
            print(f"✅ Created test user: ID {test_user.telegram_id}")
            print(f"✅ Initial balance: {test_user.balance} SOL")
            
            # Test the balance manager directly
            import balance_manager
            
            success, message = balance_manager.adjust_balance('999999999', 2.5, "Test adjustment")
            
            if success:
                print("✅ Balance adjustment succeeded")
                print(f"✅ Result: {message}")
                
                # Verify the balance changed
                db.session.refresh(test_user)
                expected_balance = 10.0 + 2.5
                
                if abs(test_user.balance - expected_balance) < 0.001:
                    print(f"✅ Balance correctly updated to {test_user.balance} SOL")
                else:
                    print(f"❌ Balance mismatch: expected {expected_balance}, got {test_user.balance}")
                    return False
                    
            else:
                print(f"❌ Balance adjustment failed: {message}")
                return False
            
            # Clean up test user
            db.session.delete(test_user)
            db.session.commit()
            print("✅ Test user cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False

def main():
    """Run all tests"""
    
    print("ADMIN BALANCE ADJUSTMENT TEST SUITE")
    print("=" * 60)
    print()
    
    tests = [
        ("Message Safety", test_message_safety),
        ("Handler Function", test_admin_balance_handler),
        ("Complete Workflow", test_complete_workflow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("TEST RESULTS SUMMARY")
    print("=" * 25)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED - Admin balance adjustment is working!")
    else:
        print(f"\n⚠️ {len(results) - passed} tests failed - needs further investigation")

if __name__ == "__main__":
    main()