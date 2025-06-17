#!/usr/bin/env python
"""
Create Test Referral Data
========================
Creates test users and referral codes to verify the system works properly
"""

from app import app, db
from models import User, ReferralCode, ReferralReward, UserStatus
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_referral_data():
    """Create test users with referral relationships"""
    
    with app.app_context():
        try:
            # Create a test referrer user
            referrer = User.query.filter_by(telegram_id="test_referrer_123").first()
            if not referrer:
                referrer = User(
                    telegram_id="test_referrer_123",
                    username="test_referrer",
                    first_name="Test",
                    last_name="Referrer",
                    balance=100.0,
                    status=UserStatus.ACTIVE
                )
                db.session.add(referrer)
                db.session.flush()  # Get the ID
                
                # Create referral code for the referrer
                ref_code = ReferralCode(
                    user_id=referrer.id,
                    code="SOLTEST123",
                    total_referrals=2,
                    total_earned=5.0,
                    is_active=True
                )
                db.session.add(ref_code)
                db.session.flush()
                
                # Create referred users
                for i in range(2):
                    referred_user = User(
                        telegram_id=f"test_referred_{i+1}",
                        username=f"referred_user_{i+1}",
                        first_name=f"Referred{i+1}",
                        balance=50.0 + (i * 25),  # Different balances
                        referrer_code_id=ref_code.id,
                        status=UserStatus.ACTIVE
                    )
                    db.session.add(referred_user)
                    db.session.flush()
                    
                    # Create referral reward
                    reward = ReferralReward(
                        referrer_id=referrer.id,
                        referred_id=referred_user.id,
                        amount=2.5,
                        source_profit=50.0,
                        percentage=5.0
                    )
                    db.session.add(reward)
                
                db.session.commit()
                print(f"✅ Created test referrer with ID: {referrer.telegram_id}")
                print(f"✅ Created referral code: {ref_code.code}")
                print(f"✅ Created 2 referred users")
                print(f"✅ Created referral rewards")
                
            else:
                print(f"✅ Test referrer already exists: {referrer.telegram_id}")
                
            return referrer.telegram_id
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating test data: {e}")
            return None

if __name__ == "__main__":
    print("🔧 CREATING TEST REFERRAL DATA")
    print("=" * 35)
    
    referrer_id = create_test_referral_data()
    
    if referrer_id:
        print(f"\n✅ TEST DATA CREATED SUCCESSFULLY")
        print(f"Test referrer ID: {referrer_id}")
        print("You can now test the referral system!")
    else:
        print("\n❌ FAILED TO CREATE TEST DATA")
        
    print("=" * 35)