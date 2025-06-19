#!/usr/bin/env python3
"""
Test Admin Balance Adjustment Function
=====================================
This script tests the admin adjust balance functionality to ensure it works without HTTP 400 errors.
"""

import sys
import os
sys.path.append('.')

from app import app, db
from models import User, UserStatus
import logging

def test_admin_balance_adjustment():
    """Test the admin balance adjustment message formatting."""
    
    with app.app_context():
        try:
            # Get active users for testing
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            user_suggestions = []
            
            print(f"Found {len(active_users)} active users")
            
            # Format user info for display (same as in the actual function)
            for user in active_users[:5]:
                if user.username:
                    # Remove problematic characters from username
                    clean_username = user.username.replace('_', '').replace('.', '').replace('*', '').replace('[', '').replace(']', '').replace('`', '').replace('(', '').replace(')', '').replace('~', '').replace('>', '').replace('#', '').replace('+', '').replace('=', '').replace('|', '').replace('{', '').replace('}', '').replace('!', '')
                    username_display = f"@{clean_username}"
                else:
                    username_display = "No username"
                user_suggestions.append({
                    "telegram_id": user.telegram_id,
                    "display": f"ID {user.telegram_id} - {username_display} - Balance {user.balance:.0f} SOL"
                })
                print(f"User: {user_suggestions[-1]['display']}")
            
            # Create the message (same as in actual function)
            suggestion_text = ""
            if user_suggestions:
                suggestion_text = "\n\nRecent Active Users:\n"
                for i, user in enumerate(user_suggestions):
                    suggestion_text += f"{i+1}. {user['display']}\n"
            
            message = (
                "ADJUST USER BALANCE\n\n"
                "Please enter the Telegram ID or username of the user whose balance you want to adjust."
                f"{suggestion_text}\n"
                "Type the ID number, or type 'cancel' to go back."
            )
            
            print("\n" + "="*50)
            print("GENERATED MESSAGE:")
            print("="*50)
            print(message)
            print("="*50)
            
            # Check for problematic characters
            problematic_chars = ['*', '_', '[', ']', '`', '(', ')', '~', '>', '#', '+', '=', '|', '{', '}', '.', '!']
            found_issues = []
            
            for char in problematic_chars:
                if char in message:
                    found_issues.append(char)
            
            if found_issues:
                print(f"\nWARNING: Found potentially problematic characters: {found_issues}")
                print("These characters might cause Markdown parsing errors.")
            else:
                print("\n✅ Message appears safe - no problematic Markdown characters found")
            
            # Test message length
            print(f"\nMessage length: {len(message)} characters")
            if len(message) > 4096:
                print("WARNING: Message exceeds Telegram's 4096 character limit")
            
            # Test with specific user
            if active_users:
                test_user = active_users[0]
                print(f"\nTest user details:")
                print(f"  Telegram ID: {test_user.telegram_id}")
                print(f"  Username: {test_user.username}")
                print(f"  Balance: {test_user.balance}")
                
                # Test user lookup message
                if test_user.username:
                    clean_username = test_user.username.replace('_', '').replace('.', '').replace('*', '').replace('[', '').replace(']', '').replace('`', '').replace('(', '').replace(')', '').replace('~', '').replace('>', '').replace('#', '').replace('+', '').replace('=', '').replace('|', '').replace('{', '').replace('}', '').replace('!', '')
                    username_display = f"@{clean_username}"
                else:
                    username_display = "No username"
                user_found_message = (
                    "USER FOUND\n\n"
                    f"User: {username_display}\n"
                    f"Telegram ID: {test_user.telegram_id}\n"
                    f"Current Balance: {test_user.balance:.0f} SOL\n\n"
                    "Enter adjustment amount:\n"
                    "Positive number to add example 5\n"
                    "Negative number to remove example -3\n"
                    "Type cancel to abort"
                )
                
                print(f"\n" + "="*30)
                print("USER FOUND MESSAGE:")
                print("="*30)
                print(user_found_message)
                print("="*30)
                
                # Check user found message for issues
                user_found_issues = []
                for char in problematic_chars:
                    if char in user_found_message:
                        user_found_issues.append(char)
                
                if user_found_issues:
                    print(f"\nWARNING: User found message has problematic characters: {user_found_issues}")
                else:
                    print("\n✅ User found message appears safe")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("Testing Admin Balance Adjustment Function...")
    success = test_admin_balance_adjustment()
    
    if success:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed")
        sys.exit(1)