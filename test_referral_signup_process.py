#!/usr/bin/env python3
"""
Test Referral Signup Process
============================
This script tests the /start command with referral parameters to ensure
real-time referral counting works when new users join via referral links.
"""

from app import app, db
from models import User, ReferralCode
from simple_referral_system import simple_referral_manager
from bot_v20_runner import start_command
import json

def simulate_telegram_update(user_id, username, message_text):
    """Create a simulated Telegram update object"""
    return {
        'message': {
            'from': {
                'id': user_id,
                'username': username,
                'first_name': 'Test',
                'last_name': 'User'
            },
            'text': message_text,
            'chat': {
                'id': user_id
            }
        }
    }

def test_referral_signup_realtime():
    """Test the complete referral signup process"""
    print("=== TESTING REFERRAL SIGNUP REAL-TIME ===")
    
    with app.app_context():
        # Get an existing user to be the referrer
        referrer = User.query.first()
        if not referrer:
            print("❌ No existing users found")
            return
        
        print(f"Using referrer: {referrer.telegram_id} ({referrer.username})")
        
        # Get initial referral stats
        initial_stats = simple_referral_manager.get_referral_stats(referrer.telegram_id)
        print(f"Initial referrals: {initial_stats['total_referrals']}")
        print(f"Initial active: {initial_stats['active_referrals']}")
        
        # Create test user ID (make sure it doesn't exist)
        test_user_id = 888777666
        test_username = "test_referral_user"
        
        # Clean up any existing test user
        existing = User.query.filter_by(telegram_id=str(test_user_id)).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            print("Cleaned up existing test user")
        
        # Test 1: Simulate new user clicking referral link
        print(f"\n1. Simulating new user {test_user_id} clicking referral link...")
        referral_message = f"/start ref_{referrer.telegram_id}"
        
        # Create the Telegram update
        update = simulate_telegram_update(test_user_id, test_username, referral_message)
        
        # Process the start command (this should create user and link referral)
        print("Processing /start command with referral...")
        try:
            # Mock bot object for the test
            class MockBot:
                def send_message(self, chat_id, text, **kwargs):
                    print(f"Bot would send to {chat_id}: {text[:100]}...")
                    return True
                
                def create_inline_keyboard(self, buttons):
                    return {"inline_keyboard": buttons}
            
            mock_bot = MockBot()
            
            # Import and call the start command directly
            from bot_v20_runner import start_command
            
            # We need to set the global bot variable temporarily
            import bot_v20_runner
            original_bot = getattr(bot_v20_runner, 'bot', None)
            bot_v20_runner.bot = mock_bot
            
            # Call start command
            start_command(update, str(test_user_id))
            
            # Restore original bot
            if original_bot:
                bot_v20_runner.bot = original_bot
            
            print("✅ Start command processed")
            
        except Exception as e:
            print(f"❌ Error processing start command: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test 2: Check if user was created and linked
        print("\n2. Checking if user was created and linked...")
        new_user = User.query.filter_by(telegram_id=str(test_user_id)).first()
        
        if new_user:
            print(f"✅ New user created: {new_user.telegram_id}")
            
            # Check if referral link was established
            if hasattr(new_user, 'referrer_code_id') and new_user.referrer_code_id:
                ref_code = ReferralCode.query.get(new_user.referrer_code_id)
                if ref_code and ref_code.user_id == referrer.id:
                    print("✅ Referral link established correctly")
                else:
                    print("❌ Referral link not established correctly")
            else:
                print("⚠️ User created but referral link may not be established")
        else:
            print("❌ New user was not created")
            return
        
        # Test 3: Check updated referral stats
        print("\n3. Checking updated referral stats...")
        updated_stats = simple_referral_manager.get_referral_stats(referrer.telegram_id)
        
        print(f"Updated referrals: {updated_stats['total_referrals']}")
        print(f"Updated active: {updated_stats['active_referrals']}")
        
        if updated_stats['total_referrals'] > initial_stats['total_referrals']:
            print("✅ Total referrals increased in real-time!")
        else:
            print("❌ Total referrals did not increase")
        
        # Test 4: Test active referral counting by giving the new user a balance
        print("\n4. Testing active referral counting...")
        new_user.balance = 1.0  # Give them a balance to make them "active"
        db.session.commit()
        
        # Check stats again
        final_stats = simple_referral_manager.get_referral_stats(referrer.telegram_id)
        print(f"Final active referrals: {final_stats['active_referrals']}")
        
        if final_stats['active_referrals'] > updated_stats['active_referrals']:
            print("✅ Active referrals updated when user got balance!")
        else:
            print("⚠️ Active referrals may not have updated")
        
        # Cleanup
        print("\n5. Cleaning up test data...")
        if new_user:
            db.session.delete(new_user)
            db.session.commit()
            print("✅ Test user cleaned up")
        
        print("\n=== REFERRAL SIGNUP TEST COMPLETED ===")

if __name__ == "__main__":
    test_referral_signup_realtime()