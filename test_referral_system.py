#!/usr/bin/env python
"""
Test Referral System Functionality
----------------------------------
Tests the simplified referral system to ensure referral links work properly
and rewards are processed when referred users make profits.
"""

from app import app, db
from models import User, UserStatus, ReferralReward
from simple_referral_system import simple_referral_manager
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_referral_link_functionality():
    """Test that referral links properly track new users"""
    
    with app.app_context():
        # Create test users if they don't exist
        referrer_id = "test_referrer_123"
        new_user_id = "test_newuser_456"
        
        # Clean up any existing test users
        User.query.filter_by(telegram_id=referrer_id).delete()
        User.query.filter_by(telegram_id=new_user_id).delete()
        db.session.commit()
        
        # Create referrer user
        referrer = User(
            telegram_id=referrer_id,
            username="test_referrer",
            first_name="Test",
            last_name="Referrer",
            joined_at=datetime.utcnow(),
            status=UserStatus.ACTIVE,
            balance=10.0
        )
        db.session.add(referrer)
        db.session.commit()
        
        # Create new user
        new_user = User(
            telegram_id=new_user_id,
            username="test_newuser",
            first_name="New",
            last_name="User",
            joined_at=datetime.utcnow(),
            status=UserStatus.ONBOARDING,
            balance=0.0
        )
        db.session.add(new_user)
        db.session.commit()
        
        logger.info("Created test users")
        
        # Test 1: Process referral signup
        success = simple_referral_manager.process_referral_signup(new_user_id, referrer_id)
        logger.info(f"Referral signup processed: {success}")
        
        # Test 2: Get referrer stats
        stats = simple_referral_manager.get_referral_stats(referrer_id)
        logger.info(f"Referrer stats: {stats}")
        
        # Test 3: Verify referral link format
        expected_link = f"https://t.me/thrivesolanabot?start=ref_{referrer_id}"
        actual_link = stats['referral_link']
        logger.info(f"Expected link: {expected_link}")
        logger.info(f"Actual link: {actual_link}")
        logger.info(f"Link format correct: {expected_link == actual_link}")
        
        # Test 4: Give new user some balance and test referral reward
        new_user.balance = 5.0
        db.session.commit()
        
        # Simulate profit for new user
        profit_amount = 2.0
        reward_success = simple_referral_manager.process_referral_reward(new_user_id, profit_amount)
        logger.info(f"Referral reward processed: {reward_success}")
        
        # Check if referrer received reward
        db.session.refresh(referrer)
        expected_reward = profit_amount * 0.05  # 5%
        logger.info(f"Expected reward: {expected_reward} SOL")
        logger.info(f"Referrer new balance: {referrer.balance} SOL")
        
        # Clean up
        User.query.filter_by(telegram_id=referrer_id).delete()
        User.query.filter_by(telegram_id=new_user_id).delete()
        ReferralReward.query.filter_by(referrer_id=referrer.id).delete()
        db.session.commit()
        
        logger.info("Test completed and cleaned up")
        
        return {
            'referral_signup': success,
            'stats_retrieved': bool(stats['referral_link']),
            'link_format_correct': expected_link == actual_link,
            'reward_processed': reward_success
        }

if __name__ == "__main__":
    results = test_referral_link_functionality()
    logger.info(f"Test results: {results}")
    
    all_passed = all(results.values())
    logger.info(f"All tests passed: {all_passed}")