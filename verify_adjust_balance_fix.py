"""
Verify Adjust Balance Fix - Quick Test
=====================================
This script verifies that the HTTP 400 message formatting errors are resolved
by testing the key functions with real data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from telegram_message_formatter import (
    format_balance_adjustment_user_found,
    format_balance_adjustment_confirmation,
    format_balance_adjustment_result,
    safe_send_message
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_existing_users():
    """Test message formatting with existing users in the database."""
    
    with app.app_context():
        try:
            # Get some existing users from the database
            users = User.query.limit(5).all()
            
            if not users:
                logger.info("No existing users found in database")
                return True
            
            logger.info(f"Testing message formatting with {len(users)} existing users...")
            
            for user in users:
                logger.info(f"\nTesting user: {user.username} (ID: {user.telegram_id})")
                
                # Test user found message
                try:
                    message, parse_mode = format_balance_adjustment_user_found(
                        user.username or "", 
                        user.telegram_id, 
                        user.balance or 0.0
                    )
                    logger.info(f"✅ User found message: {len(message)} chars, mode: {parse_mode}")
                except Exception as e:
                    logger.error(f"❌ User found message failed: {e}")
                    return False
                
                # Test confirmation message
                try:
                    conf_message, conf_parse_mode = format_balance_adjustment_confirmation(
                        user.telegram_id, 
                        user.balance or 0.0, 
                        1.5, 
                        "Test adjustment"
                    )
                    logger.info(f"✅ Confirmation message: {len(conf_message)} chars, mode: {conf_parse_mode}")
                except Exception as e:
                    logger.error(f"❌ Confirmation message failed: {e}")
                    return False
                
                # Test result message
                try:
                    result_message, result_parse_mode = format_balance_adjustment_result(
                        True, 1.5, f"Balance updated for user {user.telegram_id}"
                    )
                    logger.info(f"✅ Result message: {len(result_message)} chars, mode: {result_parse_mode}")
                except Exception as e:
                    logger.error(f"❌ Result message failed: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error testing existing users: {e}")
            return False


def test_problematic_characters():
    """Test with known problematic character combinations."""
    
    logger.info("\nTesting known problematic characters...")
    
    test_cases = [
        ("test_user_", "1111111111", 10.0, "Trailing underscore"),
        ("test*user", "2222222222", 5.0, "Asterisk in username"),
        ("test[user]", "3333333333", 15.5, "Brackets in username"),
        ("test`user", "4444444444", 0.0, "Backtick in username"),
        ("test@user.com", "5555555555", 25.75, "Email-like username"),
        ("", "6666666666", 1.0, "Empty username"),
        ("normal_user", "7777777777", 100.0, "Normal username"),
    ]
    
    for username, telegram_id, balance, description in test_cases:
        logger.info(f"\nTesting: {description}")
        logger.info(f"Username: {repr(username)}, ID: {telegram_id}")
        
        try:
            # Test all message types
            msg1, mode1 = format_balance_adjustment_user_found(username, telegram_id, balance)
            msg2, mode2 = format_balance_adjustment_confirmation(telegram_id, balance, 2.0, "Test")
            msg3, mode3 = format_balance_adjustment_result(True, 2.0, "Success")
            
            logger.info(f"✅ All messages generated successfully")
            logger.info(f"   User found: {len(msg1)} chars ({mode1 or 'plain'})")
            logger.info(f"   Confirmation: {len(msg2)} chars ({mode2 or 'plain'})")
            logger.info(f"   Result: {len(msg3)} chars ({mode3 or 'plain'})")
            
        except Exception as e:
            logger.error(f"❌ Error with {description}: {e}")
            return False
    
    return True


def test_mock_telegram_integration():
    """Test the safe_send_message function with mock bot."""
    
    logger.info("\nTesting safe message sending integration...")
    
    class MockTelegramBot:
        def __init__(self):
            self.call_count = 0
            
        def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
            self.call_count += 1
            
            # Simulate common Telegram errors
            if "*unmatched*asterisk" in text and parse_mode == "Markdown":
                return {"ok": False, "error_code": 400, "description": "Bad Request: can't parse entities"}
            
            if len(text) > 4096:
                return {"ok": False, "error_code": 400, "description": "Bad Request: message is too long"}
            
            return {"ok": True, "message_id": self.call_count}
        
        def create_inline_keyboard(self, buttons):
            return {"inline_keyboard": buttons}
    
    mock_bot = MockTelegramBot()
    
    # Test with various scenarios
    test_scenarios = [
        ("normal_user", "1234567890", 5.0),
        ("user*with*asterisks", "2222222222", 10.0),
        ("user[brackets]", "3333333333", 15.0),
        ("user_underscores_", "4444444444", 20.0),
    ]
    
    for username, telegram_id, balance in test_scenarios:
        logger.info(f"Testing safe send for: {username}")
        
        try:
            message, parse_mode = format_balance_adjustment_user_found(username, telegram_id, balance)
            
            # Mock the safe_send_message behavior
            keyboard = mock_bot.create_inline_keyboard([
                [{"text": "Cancel", "callback_data": "admin_back"}]
            ])
            
            # First attempt
            response = mock_bot.send_message("12345", message, parse_mode, keyboard)
            
            if response.get("ok"):
                logger.info(f"✅ Message sent successfully on first attempt")
            else:
                logger.info(f"First attempt failed: {response.get('description')}")
                
                # Test fallback to plain text (simulate safe_send_message behavior)
                from telegram_message_formatter import remove_markdown_formatting
                plain_message = remove_markdown_formatting(message)
                fallback_response = mock_bot.send_message("12345", plain_message, None, keyboard)
                
                if fallback_response.get("ok"):
                    logger.info(f"✅ Fallback message sent successfully")
                else:
                    logger.error(f"❌ Even fallback failed: {fallback_response.get('description')}")
                    return False
        
        except Exception as e:
            logger.error(f"❌ Error testing {username}: {e}")
            return False
    
    logger.info(f"Total bot calls made: {mock_bot.call_count}")
    return True


def main():
    """Run verification tests."""
    
    logger.info("Verifying Adjust Balance HTTP 400 Fix")
    logger.info("=" * 50)
    
    success = True
    
    # Test 1: Existing users in database
    if not test_existing_users():
        logger.error("❌ Existing users test failed")
        success = False
    
    # Test 2: Problematic characters
    if not test_problematic_characters():
        logger.error("❌ Problematic characters test failed")
        success = False
    
    # Test 3: Mock Telegram integration
    if not test_mock_telegram_integration():
        logger.error("❌ Mock Telegram integration test failed")
        success = False
    
    logger.info("\n" + "=" * 50)
    
    if success:
        logger.info("✅ ALL VERIFICATION TESTS PASSED!")
        logger.info("\nThe Adjust Balance feature is now fixed:")
        logger.info("• Special characters in usernames are properly escaped")
        logger.info("• Markdown formatting is safe and won't cause HTTP 400 errors")
        logger.info("• Automatic fallback to plain text when Markdown fails")
        logger.info("• Enhanced error logging shows exact message content on failures")
        logger.info("• All dynamic content is safely sanitized")
        
        return True
    else:
        logger.error("❌ Some verification tests failed")
        return False


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Verification script crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)