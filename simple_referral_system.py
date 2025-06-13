#!/usr/bin/env python
"""
Simple Referral System
----------------------
A streamlined referral system that tracks referrals directly by Telegram ID
without requiring referral codes. When users click referral links, they are
automatically linked to their referrer.
"""

from app import app, db
from models import User, ReferralReward
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SimpleReferralManager:
    """Manages referrals using direct Telegram ID tracking"""
    
    def __init__(self):
        self.referral_percentage = 5.0  # 5% of profits
    
    def process_referral_signup(self, new_user_id, referrer_id):
        """
        Process a new user signup through a referral link
        
        Args:
            new_user_id (str): Telegram ID of the new user
            referrer_id (str): Telegram ID of the referring user
            
        Returns:
            bool: True if referral was successfully processed
        """
        try:
            with app.app_context():
                # Find both users
                new_user = User.query.filter_by(telegram_id=new_user_id).first()
                referrer = User.query.filter_by(telegram_id=referrer_id).first()
                
                if not new_user or not referrer:
                    logger.error(f"Users not found - New: {new_user_id}, Referrer: {referrer_id}")
                    return False
                
                # Check if user is already referred
                if hasattr(new_user, 'referrer_id') and new_user.referrer_id:
                    logger.info(f"User {new_user_id} already has a referrer")
                    return False
                
                # Create referral link - store referrer's ID directly in user record
                if not hasattr(User, 'referrer_id'):
                    # If referrer_id column doesn't exist, use the existing referrer_code_id system
                    # Find or create a referral code for the referrer
                    from models import ReferralCode
                    ref_code = ReferralCode.query.filter_by(user_id=referrer.id, is_active=True).first()
                    if not ref_code:
                        ref_code = ReferralCode(
                            user_id=referrer.id,
                            code=ReferralCode.generate_code(),
                            created_at=datetime.utcnow(),
                            is_active=True
                        )
                        db.session.add(ref_code)
                    
                    new_user.referrer_code_id = ref_code.id
                    ref_code.total_referrals += 1
                else:
                    # Use direct referrer_id if column exists
                    new_user.referrer_id = referrer.id
                
                db.session.commit()
                logger.info(f"Successfully linked {new_user_id} as referral of {referrer_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing referral signup: {e}")
            return False
    
    def get_referrer_for_user(self, user_id):
        """
        Get the referrer for a given user
        
        Args:
            user_id (str): Telegram ID of the user
            
        Returns:
            User: Referrer user object or None
        """
        try:
            with app.app_context():
                user = User.query.filter_by(telegram_id=user_id).first()
                if not user:
                    return None
                
                # Check for direct referrer_id first
                if hasattr(user, 'referrer_id') and user.referrer_id:
                    return User.query.get(user.referrer_id)
                
                # Fallback to referral code system
                if user.referrer_code_id:
                    from models import ReferralCode
                    ref_code = ReferralCode.query.get(user.referrer_code_id)
                    if ref_code:
                        return User.query.get(ref_code.user_id)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting referrer for user {user_id}: {e}")
            return None
    
    def get_referral_stats(self, user_id):
        """
        Get referral statistics for a user
        
        Args:
            user_id (str): Telegram ID of the user
            
        Returns:
            dict: Referral statistics
        """
        try:
            with app.app_context():
                user = User.query.filter_by(telegram_id=user_id).first()
                if not user:
                    return self._empty_stats()
                
                # Count referrals using both methods
                direct_referrals = 0
                code_referrals = 0
                total_earnings = 0.0
                
                # Count direct referrals if column exists
                if hasattr(User, 'referrer_id'):
                    direct_referrals = User.query.filter_by(referrer_id=user.id).count()
                
                # Count code-based referrals
                from models import ReferralCode
                ref_codes = ReferralCode.query.filter_by(user_id=user.id, is_active=True).all()
                for code in ref_codes:
                    code_referrals += code.total_referrals
                    total_earnings += code.total_earned
                
                # Count earnings from ReferralReward table
                rewards = ReferralReward.query.filter_by(referrer_id=user.id).all()
                reward_earnings = sum(reward.amount for reward in rewards)
                total_earnings = max(total_earnings, reward_earnings)
                
                total_referrals = direct_referrals + code_referrals
                
                # Count active referrals (users with balance > 0)
                active_referrals = 0
                if hasattr(User, 'referrer_id'):
                    active_referrals += User.query.filter_by(referrer_id=user.id).filter(User.balance > 0).count()
                
                for code in ref_codes:
                    active_referrals += User.query.filter_by(referrer_code_id=code.id).filter(User.balance > 0).count()
                
                return {
                    'total_referrals': total_referrals,
                    'active_referrals': active_referrals,
                    'pending_referrals': max(0, total_referrals - active_referrals),
                    'total_earnings': total_earnings,
                    'referral_link': f"https://t.me/ThriveQuantbot?start=ref_{user_id}",
                    'has_code': True,  # Always true for simplified system
                    'code': f"REF{user_id[-6:]}"  # Simple code for display
                }
                
        except Exception as e:
            logger.error(f"Error getting referral stats for {user_id}: {e}")
            return self._empty_stats()
    
    def process_referral_reward(self, user_id, profit_amount):
        """
        Process a referral reward when a referred user makes profit
        
        Args:
            user_id (str): Telegram ID of the user who made profit
            profit_amount (float): Amount of profit made
            
        Returns:
            bool: True if reward was processed
        """
        try:
            with app.app_context():
                # Find the referrer for this user
                referrer = self.get_referrer_for_user(user_id)
                if not referrer:
                    return False
                
                # Calculate reward (5% of profit)
                reward_amount = profit_amount * (self.referral_percentage / 100)
                if reward_amount <= 0:
                    return False
                
                # Add reward to referrer's balance
                referrer.balance += reward_amount
                referrer.referral_bonus += reward_amount
                
                # Create reward record
                reward = ReferralReward(
                    referrer_id=referrer.id,
                    referred_id=User.query.filter_by(telegram_id=user_id).first().id,
                    amount=reward_amount,
                    source_profit=profit_amount,
                    percentage=self.referral_percentage,
                    timestamp=datetime.utcnow()
                )
                db.session.add(reward)
                
                # Update referral code earnings if using code system
                if hasattr(User.query.filter_by(telegram_id=user_id).first(), 'referrer_code_id'):
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if user.referrer_code_id:
                        from models import ReferralCode
                        ref_code = ReferralCode.query.get(user.referrer_code_id)
                        if ref_code:
                            ref_code.total_earned += reward_amount
                
                db.session.commit()
                logger.info(f"Processed referral reward: {reward_amount} SOL to {referrer.telegram_id} from {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing referral reward: {e}")
            return False
    
    def _empty_stats(self):
        """Return empty stats structure"""
        return {
            'total_referrals': 0,
            'active_referrals': 0,
            'pending_referrals': 0,
            'total_earnings': 0.0,
            'referral_link': '',
            'has_code': False,
            'code': 'GENERATING...'
        }

# Global instance
simple_referral_manager = SimpleReferralManager()