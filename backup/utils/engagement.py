import logging
import random
from datetime import datetime, timedelta
from flask import current_app
from app import db, app
from models import User, UserStatus, ReferralCode
from config import MIN_DEPOSIT

logger = logging.getLogger(__name__)

# Engagement message templates - Specific day by day messages for each user group

# 1. For Users Who Onboarded But Haven't Deposited
NON_DEPOSITOR_MESSAGES = {
    0: "⏳ Don't sit on the sidelines—your THRIVE bot is ready!\nDeposit just <b>0.5 SOL</b> and start seeing results.",
    3: "⚡️ Still watching? You're missing gains you could've claimed already.\nFund your bot and let it go to work for you.",
    6: "🔔 Your THRIVE bot is idle. It only needs <b>0.5 SOL</b> to activate.\nTake control of your daily ROI now."
}

# 2. For Users Who Dropped Off Mid-Onboarding
DROPOFF_MESSAGES = {
    0: "👋 Let's finish your setup—drop your Solana wallet to unlock the dashboard.",
    3: "🚀 Your bot is waiting. Just add your wallet and drop <b>0.5 SOL</b> to activate it.",
    6: "📲 THRIVE can't earn for you without your wallet.\nAdd it now to launch your memecoin strategy."
}

# 3. For Idle Existing Users
UPGRADE_MESSAGES = {
    3: "💼 Your bot's working—but topping up boosts returns.\nAdd <b>0.5+ SOL</b> to compound your gains faster.",
    6: "📈 Your bot's potential is capped. Want more results? Scale your stake.",
    9: "🔔 Extra SOL = extra returns. Let THRIVE scale your stack."
}

REFERRAL_MESSAGES = [
    "🔗 <b>Share the wealth!</b> Send your unique referral link to friends and earn 5% of their profits!",
    "👥 <b>Better together:</b> Each friend who joins using your code helps improve our trading algorithm for everyone!",
    "🎁 <b>Exclusive referral bonus:</b> Get {bonus_amount} SOL added to your trading balance when 3 friends join and deposit!",
    "🌐 <b>Build your network:</b> Your referral link is ready to share! Grow your passive income by inviting serious Solana traders.",
    "💼 <b>Partnership opportunity:</b> High-volume referrers get access to our premium signals and advanced strategy options!"
]

async def send_engagement_message(context, user, message_type="non_depositor", message_number=0):
    """
    Send a targeted engagement message based on user status.
    
    Args:
        context: Telegram context for sending messages
        user: The user object from the database
        message_type: Type of engagement message to send
        message_number: Which message in the sequence to send (0, 3, 6, or 9 days)
    
    Returns:
        bool: Success status of message sending
    """
    try:
        chat_id = user.telegram_id
        
        # Select appropriate message template based on type and day
        if message_type == "non_depositor":
            # For users who onboarded but haven't deposited yet
            if message_number in NON_DEPOSITOR_MESSAGES:
                message = NON_DEPOSITOR_MESSAGES[message_number]
            else:
                logger.error(f"No message found for non_depositor day {message_number}")
                return False
                
        elif message_type == "dropoff":
            # For users who dropped off mid-onboarding
            if message_number in DROPOFF_MESSAGES:
                message = DROPOFF_MESSAGES[message_number]
            else:
                logger.error(f"No message found for dropoff day {message_number}")
                return False
                
        elif message_type == "upgrade":
            # For idle existing users
            if message_number in UPGRADE_MESSAGES:
                message = UPGRADE_MESSAGES[message_number]
            else:
                logger.error(f"No message found for upgrade day {message_number}")
                return False
                
        elif message_type == "referral":
            # Keep the original random selection for referral messages
            bonus_amount = 0.5  # Default bonus amount
            referral_code = ReferralCode.query.filter_by(user_id=user.id).first()
            if not referral_code:
                # Generate new referral code if doesn't exist
                new_code = f"SOL{user.id}{random.randint(1000, 9999)}"
                referral_code = ReferralCode(user_id=user.id, code=new_code)
                db.session.add(referral_code)
                db.session.commit()
            
            message = random.choice(REFERRAL_MESSAGES).format(bonus_amount=bonus_amount)
            # Add referral link to message
            message += f"\n\n🔗 <b>Your referral code:</b> {referral_code.code}"
        else:
            logger.error(f"Unknown message type: {message_type}")
            return False
        
        # Add call to action buttons based on message type and day
        keyboard = []
        
        if message_type == "non_depositor":
            # Buttons for users who onboarded but haven't deposited
            if message_number == 0:
                keyboard = [
                    [{"text": "💰 Deposit Now", "callback_data": "deposit"}],
                    [{"text": "⏭️ Skip", "callback_data": "skip_engagement"}]
                ]
            elif message_number == 3:
                keyboard = [
                    [{"text": "💰 Deposit Now", "callback_data": "deposit"}],
                    [{"text": "How It Works", "callback_data": "how_it_works"}]
                ]
            elif message_number == 6:
                keyboard = [
                    [{"text": "💰 Deposit Now", "callback_data": "deposit"}],
                    [{"text": "⏭️ Skip", "callback_data": "skip_engagement"}]
                ]
                
        elif message_type == "dropoff":
            # Buttons for users who dropped off mid-onboarding
            if message_number == 0:
                keyboard = [
                    [{"text": "🪙 Add Wallet", "callback_data": "settings"}],
                    [{"text": "⏭️ Skip", "callback_data": "skip_engagement"}]
                ]
            elif message_number == 3 or message_number == 6:
                keyboard = [
                    [{"text": "🪙 Add Wallet", "callback_data": "settings"}],
                    [{"text": "💰 Deposit Now", "callback_data": "deposit"}]
                ]
                
        elif message_type == "upgrade":
            # Buttons for idle existing users
            if message_number == 3:
                keyboard = [
                    [{"text": "💰 Deposit More", "callback_data": "deposit"}],
                    [{"text": "View Dashboard", "callback_data": "view_dashboard"}]
                ]
            elif message_number == 6:
                keyboard = [
                    [{"text": "💰 Deposit More", "callback_data": "deposit"}],
                    [{"text": "Check Stats", "callback_data": "trading_history"}]
                ]
            elif message_number == 9:
                keyboard = [
                    [{"text": "💰 Deposit More", "callback_data": "deposit"}],
                    [{"text": "My Wallet", "callback_data": "my_wallet"}]
                ]
                
        elif message_type == "referral":
            keyboard = [
                [{"text": "Share Referral", "callback_data": "share_referral"}],
                [{"text": "Referral Stats", "callback_data": "referral_stats"}]
            ]
        
        # Send message with keyboard
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML",
            reply_markup={"inline_keyboard": keyboard} if keyboard else None
        )
        
        # Update last activity timestamp
        user.last_activity = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Sent {message_type} engagement message to user {user.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending engagement message: {e}")
        return False


def should_send_engagement_message(user, message_type):
    """
    Determine if we should send an engagement message based on user activity and status.
    Also determines which message in the sequence to send (0, 3, 6, or 9 days).
    
    Args:
        user: The user object from the database
        message_type: Type of engagement message to check
    
    Returns:
        Tuple: (bool, int) - Whether to send an engagement message and which message number to send
    """
    now = datetime.utcnow()
    last_activity = user.last_activity or user.joined_at
    days_since_activity = (now - last_activity).days
    
    # Different timing rules based on message type
    if message_type == "non_depositor":
        # For users who onboarded but haven't deposited
        # Check required status
        if user.status != UserStatus.ONBOARDING:
            return False, 0
            
        # First message: 6 hours after wallet saved
        if days_since_activity == 0:
            hours_since_activity = (now - last_activity).total_seconds() / 3600
            if hours_since_activity >= 6:
                return True, 0
                
        # Second message: Day 3
        elif days_since_activity == 3:
            return True, 3
            
        # Third message: Day 6 (final ping)
        elif days_since_activity == 6:
            return True, 6
            
        return False, 0
    
    elif message_type == "dropoff":
        # For users who dropped off mid-onboarding without adding wallet
        # Check required status
        if user.status != UserStatus.DEPOSITING:
            return False, 0
            
        # First message: 2 hours after signup
        if days_since_activity == 0:
            hours_since_activity = (now - last_activity).total_seconds() / 3600
            if hours_since_activity >= 2:
                return True, 0
                
        # Second message: Day 3
        elif days_since_activity == 3:
            return True, 3
            
        # Third message: Day 6 (final ping)
        elif days_since_activity == 6:
            return True, 6
            
        return False, 0
    
    elif message_type == "upgrade":
        # For idle existing users who have funded but no new deposit for 3+ days
        # Check required status
        if user.status != UserStatus.ACTIVE:
            return False, 0
            
        # First message: Day 3 after inactivity
        if days_since_activity == 3:
            return True, 3
            
        # Second message: Day 6
        elif days_since_activity == 6:
            return True, 6
            
        # Third message: Day 9 (final ping)
        elif days_since_activity == 9:
            return True, 9
            
        return False, 0
    
    elif message_type == "referral":
        # Keep the original referral logic but adapt to return the tuple format
        if user.status != UserStatus.ACTIVE or days_since_activity < 5:
            return False, 0
            
        # Check if user has already referred someone
        referral_count = ReferralCode.query.filter_by(
            user_id=user.id
        ).join(User, User.referrer_code_id == ReferralCode.id).count()
        
        if referral_count == 0:
            return True, 0
            
        return False, 0
    
    return False, 0


async def schedule_engagement_messages(context):
    """
    Schedule and send engagement messages to users based on their status and activity.
    To be run as a daily scheduled job.
    
    Args:
        context: The telegram.ext.CallbackContext object
    """
    logger.info("Running scheduled engagement messages job")
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            engagement_count = 0
            
            for user in users:
                # Track if we've sent a message to this user
                message_sent = False
                
                # Check each message type and send if appropriate
                for message_type in ["non_depositor", "dropoff", "upgrade", "referral"]:
                    # Get both the should_send flag and the message_number
                    should_send, message_number = should_send_engagement_message(user, message_type)
                    
                    if should_send:
                        success = await send_engagement_message(context, user, message_type, message_number)
                        if success:
                            engagement_count += 1
                            message_sent = True
                            logger.info(f"Sent {message_type} message #{message_number} to user {user.id}")
                        # Only send one type of message per user per day
                        break
            
            logger.info(f"Sent {engagement_count} engagement messages")
            
        except Exception as e:
            logger.error(f"Error in scheduled engagement messages job: {e}")
