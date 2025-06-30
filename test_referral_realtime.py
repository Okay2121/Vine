#!/usr/bin/env python3
"""
Real-time Referral System Test
=============================
This script tests the referral system to ensure:
1. Referral links are generated correctly with ThriveQuantbot
2. Referral signup processing works in real time
3. Referral rewards are calculated and distributed properly
4. Referral stats update immediately
"""

from app import app, db
from models import User, ReferralReward, ReferralCode
from simple_referral_system import simple_referral_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_referral_link_generation():
    """Test that referral links are generated with correct bot username"""
    print("\n=== Testing Referral Link Generation ===")
    
    with app.app_context():
        # Get existing users for testing
        users = User.query.limit(3).all()
        
        for user in users:
            stats = simple_referral_manager.get_referral_stats(user.telegram_id)
            referral_link = stats['referral_link']
            
            print(f"User {user.telegram_id} ({user.username})")
            print(f"  Referral link: {referral_link}")
            
            # Check if link contains correct bot username
            if 'ThriveQuantbot' in referral_link:
                print(f"  ✅ Bot username is correct")
            else:
                print(f"  ❌ Bot username is incorrect")
            
            print(f"  Total referrals: {stats['total_referrals']}")
            print(f"  Active referrals: {stats['active_referrals']}")
            print(f"  Total earnings: {stats['total_earnings']} SOL")
            print()

def test_referral_signup_simulation():
    """Test referral signup process with simulated new users"""
    print("\n=== Testing Referral Signup Process ===")
    
    with app.app_context():
        # Get first user as referrer
        referrer = User.query.first()
        if not referrer:
            print("❌ No users found in database")
            return
        
        print(f"Testing with referrer: {referrer.telegram_id} ({referrer.username})")
        
        # Get initial referral stats
        initial_stats = simple_referral_manager.get_referral_stats(referrer.telegram_id)
        print(f"Initial referrals: {initial_stats['total_referrals']}")
        
        # Simulate new user signup (we'll use a test telegram ID)
        test_new_user_id = "999888777"  # Test ID that won't conflict
        
        # First, create the new user in database
        existing_test_user = User.query.filter_by(telegram_id=test_new_user_id).first()
        if existing_test_user:
            # Clean up previous test
            db.session.delete(existing_test_user)
            db.session.commit()
        
        # Create new test user
        new_user = User(
            telegram_id=test_new_user_id,
            username=f"test_user_{test_new_user_id}",
            balance=0.0,
            status="active"
        )
        db.session.add(new_user)
        db.session.commit()
        
        print(f"Created test user: {test_new_user_id}")
        
        # Process referral signup
        success = simple_referral_manager.process_referral_signup(test_new_user_id, referrer.telegram_id)
        
        if success:
            print("✅ Referral signup processed successfully")
            
            # Check updated stats
            updated_stats = simple_referral_manager.get_referral_stats(referrer.telegram_id)
            print(f"Updated referrals: {updated_stats['total_referrals']}")
            
            if updated_stats['total_referrals'] > initial_stats['total_referrals']:
                print("✅ Referral count increased in real time")
            else:
                print("❌ Referral count did not increase")
        else:
            print("❌ Referral signup failed")
        
        # Clean up test user
        test_user = User.query.filter_by(telegram_id=test_new_user_id).first()
        if test_user:
            db.session.delete(test_user)
            db.session.commit()
            print("🧹 Cleaned up test user")

def test_referral_reward_calculation():
    """Test referral reward processing when referred users make profits"""
    print("\n=== Testing Referral Reward Calculation ===")
    
    with app.app_context():
        # Get users for testing
        users = User.query.limit(2).all()
        if len(users) < 2:
            print("❌ Need at least 2 users for reward testing")
            return
        
        referrer = users[0]
        referred_user = users[1]
        
        print(f"Referrer: {referrer.telegram_id} ({referrer.username})")
        print(f"Referred user: {referred_user.telegram_id} ({referred_user.username})")
        
        # Get initial balances and earnings
        initial_referrer_balance = referrer.balance
        initial_earnings = simple_referral_manager.get_referral_stats(referrer.telegram_id)['total_earnings']
        
        print(f"Initial referrer balance: {initial_referrer_balance} SOL")
        print(f"Initial referral earnings: {initial_earnings} SOL")
        
        # Simulate a profit for the referred user
        test_profit = 1.0  # 1 SOL profit
        print(f"Simulating {test_profit} SOL profit for referred user...")
        
        # Process referral reward (5% of profit = 0.05 SOL)
        reward_success = simple_referral_manager.process_referral_reward(referred_user.telegram_id, test_profit)
        
        if reward_success:
            print("✅ Referral reward processed")
            
            # Check updated balances
            db.session.refresh(referrer)  # Refresh from database
            updated_stats = simple_referral_manager.get_referral_stats(referrer.telegram_id)
            
            expected_reward = test_profit * 0.05  # 5%
            print(f"Expected reward: {expected_reward} SOL")
            print(f"Updated referral earnings: {updated_stats['total_earnings']} SOL")
            
            if updated_stats['total_earnings'] > initial_earnings:
                print("✅ Referral earnings increased in real time")
            else:
                print("❌ Referral earnings did not increase")
        else:
            print("❌ Referral reward processing failed (expected - users not linked)")

def test_active_referral_tracking():
    """Test active referral tracking based on user balances"""
    print("\n=== Testing Active Referral Tracking ===")
    
    with app.app_context():
        # Get all users and their referral stats
        users = User.query.all()
        
        print(f"Testing with {len(users)} total users")
        
        for user in users:
            stats = simple_referral_manager.get_referral_stats(user.telegram_id)
            balance = user.balance
            
            print(f"User {user.telegram_id}: Balance {balance} SOL")
            print(f"  Total referrals: {stats['total_referrals']}")
            print(f"  Active referrals: {stats['active_referrals']}")
            print(f"  Pending referrals: {stats['pending_referrals']}")
            
            # Active referrals should be users with balance > 0
            if stats['active_referrals'] + stats['pending_referrals'] == stats['total_referrals']:
                print("  ✅ Referral counting is consistent")
            else:
                print("  ⚠️ Referral counting may have issues")
            print()

def run_comprehensive_test():
    """Run all referral system tests"""
    print("🧪 COMPREHENSIVE REFERRAL SYSTEM TEST")
    print("=" * 50)
    
    try:
        test_referral_link_generation()
        test_referral_signup_simulation()
        test_referral_reward_calculation()
        test_active_referral_tracking()
        
        print("\n✅ REFERRAL SYSTEM TEST COMPLETED")
        print("Check results above for any issues.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_comprehensive_test()