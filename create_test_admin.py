#!/usr/bin/env python
"""
Create a test admin user in the database to ensure admin panel functionality works properly.
"""
import logging
from app import app, db
from models import User, UserStatus, ReferralCode
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_test_admin():
    """Create a test admin user in the database"""
    with app.app_context():
        # Check if admin user already exists
        admin_id = os.environ.get('ADMIN_USER_ID', '12345678')
        existing_user = User.query.filter_by(telegram_id=admin_id).first()
        
        if existing_user:
            logger.info(f"Admin user already exists: {existing_user.username} (ID: {existing_user.telegram_id})")
            return existing_user
        
        try:
            # Create new admin user
            admin = User()
            admin.telegram_id = admin_id
            admin.username = "admin_test"
            admin.first_name = "Admin"
            admin.last_name = "User"
            admin.joined_at = datetime.utcnow()
            admin.status = UserStatus.ACTIVE
            admin.balance = 5.0
            admin.initial_deposit = 5.0
            admin.wallet_address = "SoL123456789testAdminWallet"
            
            # Add to database
            db.session.add(admin)
            db.session.commit()
            
            # Create referral code for admin
            referral_code = ReferralCode()
            referral_code.user_id = admin.id
            referral_code.code = ReferralCode.generate_code()
            referral_code.created_at = datetime.utcnow()
            referral_code.is_active = True
            
            # Add to database
            db.session.add(referral_code)
            db.session.commit()
            
            logger.info(f"Created test admin user: {admin.username} (ID: {admin.telegram_id})")
            logger.info(f"Created referral code: {referral_code.code}")
            
            return admin
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating test admin user: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

if __name__ == "__main__":
    # Create test admin user
    admin_user = create_test_admin()
    
    if admin_user:
        print(f"✅ Test admin user created successfully: @{admin_user.username}")
        print(f"Telegram ID: {admin_user.telegram_id}")
        print(f"Balance: {admin_user.balance} SOL")
    else:
        print("❌ Failed to create test admin user")