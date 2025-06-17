"""
Test Referral Real-Time Counting System
=====================================
Simple test script to verify referral functionality works correctly
"""

from app import app, db
from models import User, ReferralCode
import referral_module

def test_referral_system_functionality():
    """Test the referral system with a real user"""
    
    with app.app_context():
        # Get a user who has referrals
        user_with_refs = db.session.execute(
            db.text("""
                SELECT u.telegram_id, u.id, rc.code, rc.total_referrals 
                FROM user u 
                JOIN referral_code rc ON u.id = rc.user_id 
                WHERE rc.total_referrals > 0 
                LIMIT 1
            """)
        ).fetchone()
        
        if not user_with_refs:
            print("❌ No users with referrals found for testing")
            return
        
        print(f"🧪 Testing referral system for user: {user_with_refs.telegram_id}")
        print(f"📊 Current stored referrals: {user_with_refs.total_referrals}")
        
        # Initialize referral manager
        manager = referral_module.ReferralManager(app.app_context)
        manager.set_bot_username("ThriveQuantbot")
        
        # Get real-time stats
        stats = manager.get_referral_stats(user_with_refs.telegram_id)
        
        print("\n📈 REAL-TIME REFERRAL STATS:")
        print(f"   Has Code: {stats['has_code']}")
        print(f"   Referral Code: {stats['code']}")
        print(f"   Total Referrals: {stats['total_referrals']}")
        print(f"   Active Referrals: {stats['active_referrals']}")
        print(f"   Total Earnings: {stats['total_earnings']:.4f} SOL")
        print(f"   Referral Link: {stats['referral_link']}")
        
        if stats['referred_users']:
            print(f"\n👥 REFERRED USERS ({len(stats['referred_users'])}):")
            for i, user in enumerate(stats['referred_users'][:3], 1):  # Show first 3
                status = "✅ Active" if user['is_active'] else "⏳ Pending"
                print(f"   {i}. {user['username']} - {status} - {user['balance']:.2f} SOL")
        
        # Verify the referral link works
        referral_link = stats['referral_link']
        if referral_link:
            print(f"\n🔗 REFERRAL LINK TEST:")
            print(f"   Link: {referral_link}")
            print(f"   ✅ Link generated successfully")
        
        return True

if __name__ == "__main__":
    print("🔧 TESTING REFERRAL REAL-TIME COUNTING")
    print("=" * 45)
    
    success = test_referral_system_functionality()
    
    if success:
        print("\n✅ REFERRAL SYSTEM TEST COMPLETED")
        print("The referral system should now show real-time counts")
    else:
        print("\n❌ REFERRAL SYSTEM TEST FAILED")
        
    print("=" * 45)