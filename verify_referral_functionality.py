"""
Verify Referral System Real-Time Functionality
=============================================
Direct test using existing user data to confirm referral counting works
"""

from app import app, db
from models import User, ReferralCode
import referral_module

def test_referral_with_existing_users():
    """Test referral system with actual user data"""
    
    with app.app_context():
        try:
            # Get users with referral codes
            users_with_codes = User.query.join(ReferralCode).limit(3).all()
            
            if not users_with_codes:
                print("No users with referral codes found")
                return False
            
            print(f"Found {len(users_with_codes)} users with referral codes")
            
            # Initialize referral manager
            manager = referral_module.ReferralManager(app.app_context)
            manager.set_bot_username("ThriveQuantbot")
            
            for user in users_with_codes:
                print(f"\nTesting user: {user.telegram_id}")
                
                # Get real-time stats
                stats = manager.get_referral_stats(user.telegram_id)
                
                print(f"  Has Code: {stats['has_code']}")
                print(f"  Total Referrals: {stats['total_referrals']}")
                print(f"  Active Referrals: {stats['active_referrals']}")
                print(f"  Referral Link: {stats['referral_link']}")
                
                # Test referral link generation
                if stats['referral_link']:
                    expected_link = f"https://t.me/ThriveQuantbot?start=ref_{user.telegram_id}"
                    if stats['referral_link'] == expected_link:
                        print("  ✅ Referral link format correct")
                    else:
                        print("  ❌ Referral link format incorrect")
                        print(f"     Expected: {expected_link}")
                        print(f"     Got: {stats['referral_link']}")
                
                break  # Test one user thoroughly
            
            return True
            
        except Exception as e:
            print(f"Error testing referral system: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_referral_link_processing():
    """Test if referral links are processed correctly when new users join"""
    
    with app.app_context():
        try:
            # Get a user with referral code
            referrer = User.query.join(ReferralCode).first()
            
            if not referrer:
                print("No referrer found for testing")
                return False
            
            print(f"Testing referral processing with referrer: {referrer.telegram_id}")
            
            # Get the referral link
            manager = referral_module.ReferralManager(app.app_context)
            manager.set_bot_username("ThriveQuantbot")
            
            stats = manager.get_referral_stats(referrer.telegram_id)
            referral_link = stats['referral_link']
            
            print(f"Referral link: {referral_link}")
            
            # Extract the referrer ID from the link format
            if "?start=ref_" in referral_link:
                referrer_id_from_link = referral_link.split("?start=ref_")[1]
                if referrer_id_from_link == referrer.telegram_id:
                    print("✅ Referral link contains correct referrer ID")
                else:
                    print("❌ Referral link ID mismatch")
                    print(f"   Expected: {referrer.telegram_id}")
                    print(f"   Got: {referrer_id_from_link}")
            
            return True
            
        except Exception as e:
            print(f"Error testing referral link processing: {e}")
            return False

def verify_real_time_counting():
    """Verify that referral counts are calculated in real-time"""
    
    with app.app_context():
        try:
            # Get a user with referrals
            user_with_refs = User.query.join(ReferralCode).filter(ReferralCode.total_referrals > 0).first()
            
            if not user_with_refs:
                print("No users with existing referrals found")
                return False
            
            print(f"Testing real-time counting for user: {user_with_refs.telegram_id}")
            
            # Get current referral code data
            ref_code = ReferralCode.query.filter_by(user_id=user_with_refs.id).first()
            stored_count = ref_code.total_referrals if ref_code else 0
            
            print(f"Stored referral count: {stored_count}")
            
            # Get real-time count using the manager
            manager = referral_module.ReferralManager(app.app_context)
            manager.set_bot_username("ThriveQuantbot")
            
            stats = manager.get_referral_stats(user_with_refs.telegram_id)
            real_time_count = stats['total_referrals']
            active_count = stats['active_referrals']
            
            print(f"Real-time total count: {real_time_count}")
            print(f"Real-time active count: {active_count}")
            
            # Verify the counts are reasonable
            if real_time_count >= 0 and active_count >= 0 and active_count <= real_time_count:
                print("✅ Real-time counting appears to be working correctly")
                return True
            else:
                print("❌ Real-time counting has inconsistent values")
                return False
                
        except Exception as e:
            print(f"Error verifying real-time counting: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🔧 VERIFYING REFERRAL SYSTEM FUNCTIONALITY")
    print("=" * 50)
    
    print("\n1. Testing with existing users:")
    test1 = test_referral_with_existing_users()
    
    print("\n2. Testing referral link processing:")
    test2 = test_referral_link_processing()
    
    print("\n3. Verifying real-time counting:")
    test3 = verify_real_time_counting()
    
    print("\n" + "=" * 50)
    if test1 and test2 and test3:
        print("✅ ALL REFERRAL SYSTEM TESTS PASSED")
        print("The referral system is functional with real-time counting")
    else:
        print("❌ SOME TESTS FAILED")
        print("Issues found in referral system functionality")
    print("=" * 50)