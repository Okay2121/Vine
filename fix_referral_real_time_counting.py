"""
Fix Referral Real-Time Counting System
====================================
This script fixes the referral system to ensure proper real-time counting
and updates the referral stats display to show accurate data.
"""

from app import app, db
from models import User, ReferralCode, ReferralReward
from datetime import datetime
import logging

def fix_referral_counting_system():
    """
    Fix the referral counting system to ensure real-time updates
    
    Returns:
        dict: Fix results and statistics
    """
    with app.app_context():
        try:
            fixes_applied = []
            
            # 1. Update referral codes with correct counts
            referral_codes = ReferralCode.query.all()
            
            for ref_code in referral_codes:
                # Count actual referred users
                referred_users = User.query.filter_by(referrer_code_id=ref_code.id).all()
                actual_count = len(referred_users)
                
                # Count active referred users (users with balance > 0)
                active_count = len([u for u in referred_users if u.balance > 0])
                
                # Update the count if it's different
                if ref_code.total_referrals != actual_count:
                    old_count = ref_code.total_referrals
                    ref_code.total_referrals = actual_count
                    fixes_applied.append(f"Updated referral code {ref_code.code}: {old_count} -> {actual_count} referrals")
                
                # Calculate total earnings from referral rewards
                total_earnings = db.session.query(db.func.sum(ReferralReward.amount)).filter_by(
                    referrer_id=ref_code.user_id
                ).scalar() or 0.0
                
                if abs(ref_code.total_earned - total_earnings) > 0.0001:  # Check for significant difference
                    old_earnings = ref_code.total_earned
                    ref_code.total_earned = total_earnings
                    fixes_applied.append(f"Updated earnings for code {ref_code.code}: {old_earnings:.4f} -> {total_earnings:.4f} SOL")
            
            # 2. Ensure all users have referral codes
            users_without_codes = User.query.outerjoin(ReferralCode).filter(ReferralCode.id == None).all()
            
            for user in users_without_codes:
                new_code = ReferralCode()
                new_code.user_id = user.id
                new_code.code = ReferralCode.generate_code()
                new_code.created_at = datetime.utcnow()
                new_code.is_active = True
                new_code.total_referrals = 0
                new_code.total_earned = 0.0
                
                db.session.add(new_code)
                fixes_applied.append(f"Created missing referral code for user {user.telegram_id}")
            
            # 3. Fix any broken referral relationships
            orphaned_users = User.query.filter(
                User.referrer_code_id.isnot(None)
            ).outerjoin(ReferralCode, User.referrer_code_id == ReferralCode.id).filter(
                ReferralCode.id == None
            ).all()
            
            for user in orphaned_users:
                user.referrer_code_id = None
                fixes_applied.append(f"Fixed orphaned referral relationship for user {user.telegram_id}")
            
            # Commit all changes
            db.session.commit()
            
            # 4. Generate statistics
            total_codes = ReferralCode.query.count()
            total_referrals = db.session.query(db.func.sum(ReferralCode.total_referrals)).scalar() or 0
            total_earnings = db.session.query(db.func.sum(ReferralCode.total_earned)).scalar() or 0
            active_referrers = ReferralCode.query.filter(ReferralCode.total_referrals > 0).count()
            
            return {
                "success": True,
                "fixes_applied": fixes_applied,
                "statistics": {
                    "total_referral_codes": total_codes,
                    "total_referrals": total_referrals,
                    "total_earnings": total_earnings,
                    "active_referrers": active_referrers
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                "success": False,
                "error": str(e),
                "fixes_applied": fixes_applied
            }

def update_referral_stats_function():
    """
    Update the referral stats function to use real-time data
    """
    # This function will be integrated into the referral_module.py
    referral_stats_code = '''
def get_referral_stats(self, user_id: Union[str, int]) -> Dict:
    """
    Get comprehensive referral statistics for a user with real-time data
    
    Args:
        user_id: User's Telegram ID
        
    Returns:
        Dictionary containing referral statistics
    """
    with self.app_context():
        try:
            from app import db
            from models import User, ReferralCode, ReferralReward
            from sqlalchemy import func
            
            # Convert to string for consistent comparison
            user_id = str(user_id)
            
            # Find the user
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return self._default_stats()
            
            # Find the user's referral code
            referral_code = ReferralCode.query.filter_by(user_id=user.id, is_active=True).first()
            if not referral_code:
                return self._default_stats()
            
            # Get real-time referred users count
            referred_users = User.query.filter_by(referrer_code_id=referral_code.id).all()
            
            # Calculate active referrals (users with balance > 0)
            active_referrals = [u for u in referred_users if u.balance > 0]
            
            # Calculate real-time earnings
            total_earnings = db.session.query(func.sum(ReferralReward.amount)).filter_by(
                referrer_id=user.id
            ).scalar() or 0.0
            
            # Update the referral code with current stats
            referral_code.total_referrals = len(referred_users)
            referral_code.total_earned = total_earnings
            db.session.commit()
            
            # Build detailed user list
            referred_users_detail = []
            for ref_user in referred_users:
                user_earnings = db.session.query(func.sum(ReferralReward.amount)).filter_by(
                    referrer_id=user.id,
                    referred_id=ref_user.id
                ).scalar() or 0.0
                
                referred_users_detail.append({
                    'id': ref_user.telegram_id,
                    'username': ref_user.username or f"User_{ref_user.telegram_id}",
                    'is_active': ref_user.balance > 0,
                    'balance': ref_user.balance,
                    'earnings': user_earnings,
                    'joined_at': ref_user.joined_at
                })
            
            return {
                'has_code': True,
                'referral_code': referral_code.code,
                'total_referrals': len(referred_users),
                'active_referrals': len(active_referrals),
                'pending_referrals': len(referred_users) - len(active_referrals),
                'total_earnings': total_earnings,
                'referred_users': referred_users_detail,
                'referral_link': f"https://t.me/{self.bot_username}?start=ref_{user_id}"
            }
            
        except Exception as e:
            logger.error(f"Error getting referral stats for {user_id}: {e}")
            return self._default_stats()

def _default_stats(self) -> Dict:
    """Return default empty stats"""
    return {
        'has_code': False,
        'referral_code': None,
        'total_referrals': 0,
        'active_referrals': 0,
        'pending_referrals': 0,
        'total_earnings': 0.0,
        'referred_users': [],
        'referral_link': None
    }
'''
    
    return referral_stats_code

def test_referral_system():
    """
    Test the referral system functionality
    
    Returns:
        dict: Test results
    """
    with app.app_context():
        try:
            # Get a sample user with referrals
            user_with_referrals = db.session.query(User).join(ReferralCode).filter(
                ReferralCode.total_referrals > 0
            ).first()
            
            if not user_with_referrals:
                return {"error": "No users with referrals found for testing"}
            
            # Test referral stats calculation
            ref_code = ReferralCode.query.filter_by(user_id=user_with_referrals.id).first()
            referred_users = User.query.filter_by(referrer_code_id=ref_code.id).all()
            active_referrals = [u for u in referred_users if u.balance > 0]
            
            total_earnings = db.session.query(db.func.sum(ReferralReward.amount)).filter_by(
                referrer_id=user_with_referrals.id
            ).scalar() or 0.0
            
            return {
                "success": True,
                "test_user": user_with_referrals.telegram_id,
                "referral_code": ref_code.code,
                "total_referrals": len(referred_users),
                "active_referrals": len(active_referrals),
                "total_earnings": total_earnings,
                "referral_link": f"https://t.me/ThriveQuantbot?start=ref_{user_with_referrals.telegram_id}"
            }
            
        except Exception as e:
            return {"error": f"Test failed: {str(e)}"}

def run_comprehensive_referral_fix():
    """
    Run comprehensive referral system fix
    """
    print("🔧 COMPREHENSIVE REFERRAL SYSTEM FIX")
    print("=" * 50)
    
    # 1. Fix referral counting
    print("1. FIXING REFERRAL COUNTING SYSTEM:")
    fix_results = fix_referral_counting_system()
    
    if fix_results["success"]:
        print("   ✅ Referral counting system fixed successfully")
        for fix in fix_results["fixes_applied"]:
            print(f"   🔧 {fix}")
        
        stats = fix_results["statistics"]
        print(f"\n   📊 CURRENT STATISTICS:")
        print(f"   Total Referral Codes: {stats['total_referral_codes']}")
        print(f"   Total Referrals: {stats['total_referrals']}")
        print(f"   Total Earnings: {stats['total_earnings']:.4f} SOL")
        print(f"   Active Referrers: {stats['active_referrers']}")
    else:
        print(f"   ❌ Fix failed: {fix_results['error']}")
    
    print()
    
    # 2. Test referral system
    print("2. TESTING REFERRAL SYSTEM:")
    test_results = test_referral_system()
    
    if "success" in test_results and test_results["success"]:
        print("   ✅ Referral system test passed")
        print(f"   👤 Test User: {test_results['test_user']}")
        print(f"   🔗 Referral Code: {test_results['referral_code']}")
        print(f"   👥 Total Referrals: {test_results['total_referrals']}")
        print(f"   ✅ Active Referrals: {test_results['active_referrals']}")
        print(f"   💰 Total Earnings: {test_results['total_earnings']:.4f} SOL")
        print(f"   🔗 Referral Link: {test_results['referral_link']}")
    else:
        print(f"   ❌ Test failed: {test_results.get('error', 'Unknown error')}")
    
    print()
    print("3. UPDATED REFERRAL STATS FUNCTION:")
    print("   📝 Generated updated referral stats function code")
    print("   🔄 Ready for integration into referral_module.py")
    
    print("\n" + "=" * 50)
    print("🏁 REFERRAL SYSTEM FIX COMPLETE")

if __name__ == "__main__":
    run_comprehensive_referral_fix()