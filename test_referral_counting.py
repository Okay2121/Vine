"""
Test Referral Real-Time Counting Functionality
=============================================
This script tests if the referral system properly counts and updates referrals in real-time.
"""

from app import app, db
from models import User, ReferralCode
import referral_module

def test_referral_counting():
    """Test the referral counting functionality"""
    with app.app_context():
        try:
            # Initialize referral manager
            referral_manager = referral_module.ReferralManager(app.app_context)
            referral_manager.set_bot_username("ThriveQuantbot")
            
            print("🔍 Testing Referral Real-Time Counting System")
            print("=" * 50)
            
            # Get all users with referral codes
            referral_codes = ReferralCode.query.all()
            total_codes = len(referral_codes)
            
            print(f"📊 Found {total_codes} referral codes in database")
            
            if total_codes == 0:
                print("❌ No referral codes found - creating test data")
                return False
            
            # Test each referral code's real-time counting
            working_codes = 0
            total_referrals = 0
            total_active_referrals = 0
            
            for code in referral_codes:
                try:
                    # Get real-time stats for this user
                    user_id = str(code.user_id)
                    stats = referral_manager.get_referral_stats(user_id)
                    
                    if 'error' in stats:
                        print(f"❌ Error getting stats for user {user_id}: {stats['error']}")
                        continue
                    
                    # Count direct database referrals for comparison
                    direct_count = User.query.filter_by(referrer_code_id=code.id).count()
                    active_count = User.query.filter_by(referrer_code_id=code.id).filter(User.balance > 0).count()
                    
                    # Compare real-time stats with direct database query
                    stats_match = (stats['total_referrals'] == direct_count and 
                                 stats['active_referrals'] == active_count)
                    
                    if stats_match:
                        working_codes += 1
                        status = "✅"
                    else:
                        status = "❌"
                    
                    total_referrals += stats['total_referrals']
                    total_active_referrals += stats['active_referrals']
                    
                    print(f"{status} User {user_id}: {stats['total_referrals']} total, {stats['active_referrals']} active")
                    
                    if not stats_match:
                        print(f"    Real-time: {stats['total_referrals']} total, {stats['active_referrals']} active")
                        print(f"    Direct DB: {direct_count} total, {active_count} active")
                
                except Exception as e:
                    print(f"❌ Error testing user {code.user_id}: {str(e)}")
                    continue
            
            print("\n" + "=" * 50)
            print(f"📈 SUMMARY:")
            print(f"   Total Referral Codes: {total_codes}")
            print(f"   Working Correctly: {working_codes}")
            print(f"   Total Referrals: {total_referrals}")
            print(f"   Active Referrals: {total_active_referrals}")
            
            success_rate = (working_codes / total_codes * 100) if total_codes > 0 else 0
            print(f"   Success Rate: {success_rate:.1f}%")
            
            if success_rate >= 95:
                print("\n✅ REFERRAL REAL-TIME COUNTING IS WORKING CORRECTLY")
                return True
            else:
                print("\n❌ REFERRAL COUNTING HAS ISSUES")
                return False
                
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_specific_user_referrals():
    """Test referrals for a specific user to verify functionality"""
    with app.app_context():
        try:
            # Find a user with referrals for testing
            user_with_referrals = db.session.query(User).join(ReferralCode, User.id == ReferralCode.user_id).first()
            
            if not user_with_referrals:
                print("❌ No users with referral codes found")
                return False
            
            referral_manager = referral_module.ReferralManager(app.app_context)
            referral_manager.set_bot_username("ThriveQuantbot")
            
            user_id = str(user_with_referrals.telegram_id)
            print(f"\n🔍 Testing specific user: {user_id}")
            
            # Get stats
            stats = referral_manager.get_referral_stats(user_id)
            
            print(f"📊 Referral Stats:")
            print(f"   Has Code: {stats['has_code']}")
            print(f"   Total Referrals: {stats['total_referrals']}")
            print(f"   Active Referrals: {stats['active_referrals']}")
            print(f"   Total Earnings: {stats['total_earnings']}")
            
            # Show referred users
            if stats['referred_users']:
                print(f"\n👥 Referred Users ({len(stats['referred_users'])}):")
                for user in stats['referred_users'][:5]:  # Show first 5
                    status = "🟢 Active" if user['is_active'] else "🔴 Inactive"
                    print(f"   {status} @{user['username']} (Balance: {user['balance']:.4f})")
            
            return True
            
        except Exception as e:
            print(f"❌ Specific user test failed: {str(e)}")
            return False

if __name__ == "__main__":
    print("🚀 REFERRAL SYSTEM VERIFICATION")
    print("=" * 50)
    
    # Test 1: General counting functionality
    test1_passed = test_referral_counting()
    
    # Test 2: Specific user functionality
    test2_passed = test_specific_user_referrals()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("✅ ALL REFERRAL TESTS PASSED")
        print("The referral real-time counting system is functional")
    else:
        print("❌ SOME TESTS FAILED")
        print("Issues detected in referral counting system")