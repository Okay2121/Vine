"""
Referral Program Module for Telegram Bot
This standalone module implements a complete referral system that can be integrated
with any Telegram bot. It handles referral link generation, tracking, and statistics.

Usage:
1. Import this module in your bot
2. Initialize the ReferralManager with your database context
3. Register the needed command handlers
4. Process start commands with referral parameters

All data is stored in the database for persistence across sessions.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ReferralManager:
    """
    Manages the referral program functionality including:
    - Referral link generation
    - Tracking referrals
    - Computing statistics
    - Handling rewards
    """
    
    def __init__(self, app_context, bot_username=None):
        """
        Initialize the ReferralManager.
        
        Args:
            app_context: Flask app context for database access
            bot_username: The username of your bot (optional, can be set later)
        """
        self.app_context = app_context
        self.bot_username = bot_username
        logger.info("Referral Manager initialized")
    
    def set_bot_username(self, username: str) -> None:
        """Set the bot username for generating referral links."""
        self.bot_username = username
        logger.info(f"Bot username set to {username}")
    
    def generate_referral_link(self, user_id: Union[str, int]) -> str:
        """
        Generate a referral link for a user.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            A formatted referral link for the user
        """
        if not self.bot_username:
            logger.warning("Bot username not set, using placeholder")
            bot_name = "YourBot"
        else:
            bot_name = self.bot_username
        
        return f"https://t.me/{bot_name}?start=ref_{user_id}"
    
    def extract_referral_code(self, start_parameter: str) -> Optional[str]:
        """
        Extract the referrer ID from a start parameter.
        
        Args:
            start_parameter: The start parameter from the /start command
            
        Returns:
            The referrer's ID if found, None otherwise
        """
        if not start_parameter:
            return None
        
        # Match 'ref_123456789' pattern
        match = re.match(r'ref_(\d+)', start_parameter)
        if match:
            return match.group(1)
        
        return None
    
    def process_referral(self, referred_user_id: Union[str, int], referrer_id: Union[str, int]) -> bool:
        """
        Process a referral, connecting the referred user to the referrer.
        
        Args:
            referred_user_id: The ID of the user who was referred
            referrer_id: The ID of the user who referred them
            
        Returns:
            Boolean indicating success
        """
        with self.app_context():
            try:
                from app import db
                from models import User, ReferralCode
                
                # Convert IDs to strings for consistent comparison
                referred_user_id = str(referred_user_id)
                referrer_id = str(referrer_id)
                
                # Prevent self-referrals
                if referred_user_id == referrer_id:
                    logger.warning(f"User {referred_user_id} attempted to refer themselves")
                    return False
                
                # Find both users in the database
                referred_user = User.query.filter_by(telegram_id=referred_user_id).first()
                referrer = User.query.filter_by(telegram_id=referrer_id).first()
                
                if not referred_user or not referrer:
                    logger.error(f"Unable to process referral: User not found. Referred: {referred_user_id}, Referrer: {referrer_id}")
                    return False
                
                # Check if the referred user already has a referrer
                if referred_user.referrer_code_id is not None:
                    logger.info(f"User {referred_user_id} already has a referrer")
                    return False
                
                # Get the referrer's referral code
                referral_code = ReferralCode.query.filter_by(user_id=referrer.id, is_active=True).first()
                
                if not referral_code:
                    logger.error(f"No active referral code found for user {referrer_id}")
                    return False
                
                # Link the referred user to the referrer
                referred_user.referrer_code_id = referral_code.id
                
                # Update referral statistics
                referral_code.total_referrals += 1
                
                db.session.commit()
                logger.info(f"Successfully processed referral: {referred_user_id} referred by {referrer_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error processing referral: {e}")
                return False
    
    def get_referral_stats(self, user_id: Union[str, int]) -> Dict[str, Any]:
        """
        Get referral statistics for a user.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            Dictionary with referral statistics:
            - has_code: Boolean indicating if user has a referral code
            - code: The referral code if it exists
            - referral_link: Full referral link if bot_username is set
            - total_referrals: Number of users referred
            - active_referrals: Number of referred users who have deposited
            - total_earnings: Total earnings from referrals
            - referred_users: List of referred users with basic info
        """
        with self.app_context():
            try:
                from models import User, ReferralCode, UserStatus
                
                # Convert ID to string for consistent comparison
                user_id = str(user_id)
                
                # Find the user in the database
                user = User.query.filter_by(telegram_id=user_id).first()
                
                if not user:
                    logger.error(f"User {user_id} not found in database")
                    return {
                        'has_code': False,
                        'code': None,
                        'referral_link': None,
                        'total_referrals': 0,
                        'active_referrals': 0,
                        'total_earnings': 0.0,
                        'referred_users': []
                    }
                
                # Get the user's referral code
                referral_code = ReferralCode.query.filter_by(user_id=user.id, is_active=True).first()
                
                if not referral_code:
                    logger.warning(f"No active referral code found for user {user_id}")
                    return {
                        'has_code': False,
                        'code': None,
                        'referral_link': None,
                        'total_referrals': 0,
                        'active_referrals': 0,
                        'total_earnings': 0.0,
                        'referred_users': []
                    }
                
                # Generate the full referral link if bot username is set
                referral_link = self.generate_referral_link(user_id) if self.bot_username else None
                
                # Get real-time referred users using direct query to avoid relationship conflicts
                from app import db
                referred_users_raw = db.session.execute(
                    db.text("SELECT * FROM user WHERE referrer_code_id = :ref_code_id"),
                    {'ref_code_id': referral_code.id}
                ).fetchall()
                
                # Count active referrals (users with balance > 0) in real-time
                active_referrals = 0
                referred_users = []
                total_referrals_count = len(referred_users_raw)
                
                for row in referred_users_raw:
                    is_active = row.balance > 0  # Real-time active check based on balance
                    if is_active:
                        active_referrals += 1
                    
                    referred_users.append({
                        'id': row.telegram_id,
                        'username': row.username or 'Anonymous',
                        'joined_at': row.joined_at.strftime('%Y-%m-%d %H:%M:%S') if row.joined_at else 'Unknown',
                        'is_active': is_active,
                        'balance': row.balance,
                        'deposited': row.initial_deposit and row.initial_deposit > 0
                    })
                
                # Update referral code with real-time counts
                referral_code.total_referrals = total_referrals_count
                db.session.commit()
                
                return {
                    'has_code': True,
                    'code': referral_code.code,
                    'referral_link': referral_link,
                    'total_referrals': total_referrals_count,
                    'active_referrals': active_referrals,
                    'total_earnings': referral_code.total_earned if hasattr(referral_code, 'total_earned') else 0.0,
                    'referred_users': referred_users
                }
                
            except Exception as e:
                logger.error(f"Error getting referral stats: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return {
                    'has_code': False,
                    'code': None,
                    'referral_link': None,
                    'total_referrals': 0,
                    'active_referrals': 0,
                    'total_earnings': 0.0,
                    'referred_users': [],
                    'error': str(e)
                }
    
    def credit_referral_reward(self, referred_user_id: Union[str, int], amount: float) -> bool:
        """
        Credit a reward to the referrer when the referred user generates profit.
        
        Args:
            referred_user_id: The ID of the user who generated profit
            amount: The amount of profit generated
            
        Returns:
            Boolean indicating success
        """
        with self.app_context():
            try:
                from app import db
                from models import User, ReferralCode
                
                # Convert ID to string for consistent comparison
                referred_user_id = str(referred_user_id)
                
                # Find the referred user
                referred_user = User.query.filter_by(telegram_id=referred_user_id).first()
                
                if not referred_user or not referred_user.referrer_code_id:
                    logger.info(f"User {referred_user_id} has no referrer to credit")
                    return False
                
                # Find the referral code and its owner
                referral_code = ReferralCode.query.filter_by(id=referred_user.referrer_code_id).first()
                
                if not referral_code:
                    logger.error(f"Referral code {referred_user.referrer_code_id} not found")
                    return False
                
                # Calculate the reward (5% of the profit)
                reward_amount = amount * 0.05
                
                # Update the referral code's earnings
                if hasattr(referral_code, 'total_earned'):
                    referral_code.total_earned += reward_amount
                
                # Also update the referrer's bonus
                referrer = User.query.filter_by(id=referral_code.user_id).first()
                if referrer and hasattr(referrer, 'referral_bonus'):
                    referrer.referral_bonus += reward_amount
                
                db.session.commit()
                logger.info(f"Credited {reward_amount:.4f} SOL to user {referrer.telegram_id} for referral {referred_user_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error crediting referral reward: {e}")
                return False
    
    def generate_or_get_referral_code(self, user_id: Union[str, int]) -> Optional[str]:
        """
        Get an existing referral code or generate a new one for a user.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            The referral code as a string, or None if unsuccessful
        """
        with self.app_context():
            try:
                from app import db
                from models import User, ReferralCode
                
                # Convert ID to string for consistent comparison
                user_id = str(user_id)
                
                # Find the user in the database
                user = User.query.filter_by(telegram_id=user_id).first()
                
                if not user:
                    logger.error(f"User {user_id} not found in database")
                    return None
                
                # Check if the user already has a referral code
                existing_code = ReferralCode.query.filter_by(user_id=user.id, is_active=True).first()
                
                if existing_code:
                    return existing_code.code
                
                # Generate a new code
                import uuid
                new_code = str(uuid.uuid4())[:8].upper()
                
                # Create and save the new referral code
                referral_code = ReferralCode(
                    user_id=user.id,
                    code=new_code,
                    created_at=datetime.utcnow(),
                    is_active=True,
                    total_referrals=0
                )
                
                if hasattr(referral_code, 'total_earned'):
                    referral_code.total_earned = 0.0
                
                db.session.add(referral_code)
                db.session.commit()
                
                logger.info(f"Generated new referral code for user {user_id}: {new_code}")
                return new_code
                
            except Exception as e:
                logger.error(f"Error generating referral code: {e}")
                return None