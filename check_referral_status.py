"""
Quick Referral Status Check
==========================
Simple script to verify referral counting functionality
"""

from app import app, db
from models import User, ReferralCode
import referral_module

def check_referral_status():
    """Check current referral system status"""
    with app.app_context():
        try:
            print("Checking Referral System Status...")
            
            # Count referral codes
            total_codes = ReferralCode.query.count()
            print(f"Total referral codes: {total_codes}")
            
            # Count users with referrers
            users_with_referrers = User.query.filter(User.referrer_code_id.isnot(None)).count()
            print(f"Users with referrers: {users_with_referrers}")
            
            # Test real-time counting for one user
            if total_codes > 0:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("ThriveQuantbot")
                
                # Get first referral code
                first_code = ReferralCode.query.first()
                if first_code:
                    # Find the user who owns this code
                    owner = User.query.filter_by(id=first_code.user_id).first()
                    if owner:
                        user_id = str(owner.telegram_id)
                        print(f"Testing user: {user_id}")
                        
                        # Get real-time stats
                        stats = referral_manager.get_referral_stats(user_id)
                        
                        print(f"Real-time stats:")
                        print(f"  Has code: {stats.get('has_code', False)}")
                        print(f"  Total referrals: {stats.get('total_referrals', 0)}")
                        print(f"  Active referrals: {stats.get('active_referrals', 0)}")
                        
                        # Direct database count
                        direct_count = User.query.filter_by(referrer_code_id=first_code.id).count()
                        active_count = User.query.filter_by(referrer_code_id=first_code.id).filter(User.balance > 0).count()
                        
                        print(f"Direct database count:")
                        print(f"  Total referrals: {direct_count}")
                        print(f"  Active referrals: {active_count}")
                        
                        # Check if they match
                        if stats.get('total_referrals', 0) == direct_count and stats.get('active_referrals', 0) == active_count:
                            print("✅ Real-time counting is working correctly")
                            return True
                        else:
                            print("❌ Real-time counting has discrepancies")
                            return False
                    else:
                        print("❌ Could not find owner of referral code")
                        return False
                else:
                    print("❌ No referral codes found")
                    return False
            else:
                print("ℹ️ No referral codes in database to test")
                return True
                
        except Exception as e:
            print(f"❌ Error checking referral status: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = check_referral_status()
    if success:
        print("\n✅ Referral system appears to be functional")
    else:
        print("\n❌ Issues detected in referral system")