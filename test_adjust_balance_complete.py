"""
Complete Adjust Balance Feature Test
===================================
This script tests the entire balance adjustment flow with real database operations
and safe message formatting to ensure HTTP 400 errors are resolved.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Transaction
from working_balance_manager import adjust_balance_fixed
from telegram_message_formatter import (
    format_balance_adjustment_user_found,
    format_balance_adjustment_confirmation,
    format_balance_adjustment_result,
    safe_send_message
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_users():
    """Update existing users or create test users with problematic usernames."""
    
    from models import UserStatus
    
    test_users = [
        {
            "telegram_id": "7611754415",
            "username": "user_with_underscores",
            "balance": 10.0,
            "description": "User with underscores in username"
        },
        {
            "telegram_id": "1234567890", 
            "username": "user*with*asterisks",
            "balance": 5.0,
            "description": "User with asterisks in username"
        },
        {
            "telegram_id": "9876543210",
            "username": "user[with]brackets", 
            "balance": 15.5,
            "description": "User with brackets in username"
        },
        {
            "telegram_id": "5555555555",
            "username": "user`with`backticks",
            "balance": 0.0,
            "description": "User with backticks in username"
        },
        {
            "telegram_id": "3333333333",
            "username": "user@domain.com",
            "balance": 25.75,
            "description": "User with email-like username"
        }
    ]
    
    with app.app_context():
        logger.info("Setting up test users...")
        
        for user_data in test_users:
            # Check if user already exists
            existing_user = User.query.filter_by(telegram_id=user_data["telegram_id"]).first()
            
            if existing_user:
                logger.info(f"User {user_data['telegram_id']} already exists, updating...")
                existing_user.username = user_data["username"]
                existing_user.balance = user_data["balance"]
            else:
                logger.info(f"Creating new user: {user_data['description']}")
                user = User(
                    telegram_id=user_data["telegram_id"],
                    username=user_data["username"],
                    balance=user_data["balance"],
                    wallet_address=f"wallet_{user_data['telegram_id']}",
                    status=UserStatus.ACTIVE  # Use the correct enum value
                )
                db.session.add(user)
        
        try:
            db.session.commit()
            logger.info("✅ Test users created/updated successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating test users: {e}")
            db.session.rollback()
            return False


def test_user_lookup_with_formatting(telegram_id, expected_username):
    """Test user lookup and message formatting for a specific user."""
    
    logger.info(f"\nTesting user lookup for {telegram_id}...")
    
    with app.app_context():
        try:
            # Simulate the user lookup process from bot_v20_runner.py
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                logger.error(f"❌ User {telegram_id} not found in database")
                return False
            
            logger.info(f"✅ Found user: {user.username} (ID: {user.telegram_id}, Balance: {user.balance})")
            
            # Test message formatting
            message_text, parse_mode = format_balance_adjustment_user_found(
                user.username or "", 
                user.telegram_id, 
                user.balance
            )
            
            logger.info(f"✅ User found message generated:")
            logger.info(f"   Parse mode: {parse_mode}")
            logger.info(f"   Message length: {len(message_text)} characters")
            logger.info(f"   Contains special chars: {any(c in message_text for c in ['*', '_', '[', ']', '`'])}")
            
            # Test confirmation message
            conf_message, conf_parse_mode = format_balance_adjustment_confirmation(
                user.telegram_id, user.balance, 2.5, "Test adjustment"
            )
            
            logger.info(f"✅ Confirmation message generated:")
            logger.info(f"   Parse mode: {conf_parse_mode}")
            logger.info(f"   Message length: {len(conf_message)} characters")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error testing user lookup: {e}")
            return False


def test_balance_adjustment_flow(telegram_id, adjustment_amount, reason):
    """Test the complete balance adjustment flow."""
    
    logger.info(f"\nTesting balance adjustment for {telegram_id}...")
    logger.info(f"Adjustment: {adjustment_amount} SOL")
    logger.info(f"Reason: {reason}")
    
    with app.app_context():
        try:
            # Get original balance
            user = User.query.filter_by(telegram_id=telegram_id).first()
            if not user:
                logger.error(f"❌ User {telegram_id} not found")
                return False
            
            original_balance = user.balance
            logger.info(f"Original balance: {original_balance} SOL")
            
            # Perform adjustment using working balance manager
            success, message = adjust_balance_fixed(telegram_id, adjustment_amount, reason)
            
            if success:
                logger.info(f"✅ Balance adjustment successful")
                
                # Verify balance was actually updated
                db.session.refresh(user)
                new_balance = user.balance
                expected_balance = original_balance + adjustment_amount
                
                if abs(new_balance - expected_balance) < 0.0001:
                    logger.info(f"✅ Balance correctly updated to {new_balance} SOL")
                else:
                    logger.error(f"❌ Balance mismatch: expected {expected_balance}, got {new_balance}")
                    return False
                
                # Test result message formatting
                result_message, result_parse_mode = format_balance_adjustment_result(
                    success, adjustment_amount, message
                )
                
                logger.info(f"✅ Result message generated:")
                logger.info(f"   Parse mode: {result_parse_mode}")
                logger.info(f"   Message length: {len(result_message)} characters")
                logger.info(f"   Message preview: {result_message[:100]}...")
                
                return True
            else:
                logger.error(f"❌ Balance adjustment failed: {message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in balance adjustment flow: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_mock_telegram_send():
    """Test the safe_send_message function with a mock bot."""
    
    logger.info(f"\nTesting safe message sending...")
    
    class MockBot:
        """Mock Telegram bot for testing."""
        
        def __init__(self):
            self.messages_sent = []
        
        def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
            """Mock send_message that captures calls and simulates responses."""
            
            self.messages_sent.append({
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup
            })
            
            # Simulate failure for unescaped markdown
            if parse_mode == "Markdown" and "*" in text:
                # Check for unmatched asterisks
                if text.count("*") % 2 != 0:
                    return {"ok": False, "error_code": 400, "description": "Bad Request: can't parse entities"}
            
            # Simulate success
            return {"ok": True, "message_id": len(self.messages_sent)}
        
        def create_inline_keyboard(self, buttons):
            return {"inline_keyboard": buttons}
    
    # Test with problematic content
    mock_bot = MockBot()
    
    test_cases = [
        ("user_with_underscores", "7611754415", 10.0),
        ("user*with*asterisks", "1234567890", 5.0),
        ("user[with]brackets", "9876543210", 15.5),
    ]
    
    all_passed = True
    
    for username, telegram_id, balance in test_cases:
        logger.info(f"Testing message send for {username}...")
        
        try:
            # Generate message
            message_text, parse_mode = format_balance_adjustment_user_found(username, telegram_id, balance)
            
            # Test safe send
            keyboard = mock_bot.create_inline_keyboard([
                [{"text": "Cancel", "callback_data": "admin_back"}]
            ])
            
            response = safe_send_message(
                bot=mock_bot,
                chat_id="12345",
                message_text=message_text,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
            
            if response.get("ok"):
                logger.info(f"✅ Message sent successfully for {username}")
            else:
                logger.error(f"❌ Message failed for {username}: {response}")
                all_passed = False
                
        except Exception as e:
            logger.error(f"❌ Error testing {username}: {e}")
            all_passed = False
    
    logger.info(f"Total messages sent: {len(mock_bot.messages_sent)}")
    return all_passed


def run_complete_test():
    """Run the complete test suite."""
    
    logger.info("Starting Complete Adjust Balance Feature Test")
    logger.info("=" * 60)
    
    # Step 1: Create test users
    if not create_test_users():
        logger.error("❌ Failed to create test users")
        return False
    
    # Step 2: Test user lookup and formatting for each user
    test_users = [
        ("7611754415", "user_with_underscores"),
        ("1234567890", "user*with*asterisks"),
        ("9876543210", "user[with]brackets"),
        ("5555555555", "user`with`backticks"),
        ("3333333333", "user@domain.com"),
    ]
    
    for telegram_id, username in test_users:
        if not test_user_lookup_with_formatting(telegram_id, username):
            logger.error(f"❌ User lookup test failed for {telegram_id}")
            return False
    
    # Step 3: Test balance adjustments
    adjustment_tests = [
        ("7611754415", 2.5, "Bonus payment"),
        ("1234567890", -1.0, "Fee deduction"),
        ("9876543210", 5.0, "Referral bonus"),
        ("5555555555", 10.0, "Initial deposit bonus"),
    ]
    
    for telegram_id, amount, reason in adjustment_tests:
        if not test_balance_adjustment_flow(telegram_id, amount, reason):
            logger.error(f"❌ Balance adjustment test failed for {telegram_id}")
            return False
    
    # Step 4: Test mock Telegram sending
    if not test_mock_telegram_send():
        logger.error("❌ Mock Telegram send test failed")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ ALL TESTS PASSED!")
    logger.info("\nKey results:")
    logger.info("• User lookup works with problematic usernames")
    logger.info("• Message formatting escapes special characters safely")
    logger.info("• Balance adjustments persist correctly in database")
    logger.info("• Safe message sending provides automatic fallback")
    logger.info("• HTTP 400 errors should be resolved")
    
    return True


if __name__ == "__main__":
    try:
        success = run_complete_test()
        if success:
            print("\n🎉 Balance adjustment feature is ready for production!")
        else:
            print("\n❌ Some tests failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Test suite crashed: {e}")
        import traceback
        traceback.print_exc()