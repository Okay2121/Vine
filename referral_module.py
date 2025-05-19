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

# Import telegram dependencies
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ContextTypes
except ImportError:
    # Create placeholders for imports when testing
    class Update:
        pass
    
    class InlineKeyboardButton:
        pass
    
    class InlineKeyboardMarkup:
        pass
    
    class ContextTypes:
        DEFAULT_TYPE = None

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
                from models import User, ReferralCode
                
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
                
                # Count active referrals (users who have deposited)
                from models import UserStatus
                active_referrals = sum(1 for ref_user in referral_code.referred_users if ref_user.status == UserStatus.ACTIVE)
                
                # Format referred users list with relevant info
                referred_users = []
                for ref_user in referral_code.referred_users:
                    referred_users.append({
                        'id': ref_user.telegram_id,
                        'username': ref_user.username,
                        'joined_at': ref_user.joined_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_active': ref_user.status == UserStatus.ACTIVE,
                        'deposited': ref_user.initial_deposit > 0
                    })
                
                return {
                    'has_code': True,
                    'code': referral_code.code,
                    'referral_link': referral_link,
                    'total_referrals': referral_code.total_referrals,
                    'active_referrals': active_referrals,
                    'total_earnings': referral_code.total_earned,
                    'referred_users': referred_users
                }
                
            except Exception as e:
                logger.error(f"Error getting referral stats: {e}")
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
                referral_code.total_earned += reward_amount
                
                # Also update the referrer's bonus
                referrer = User.query.filter_by(id=referral_code.user_id).first()
                if referrer:
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
                
                # Generate a new code if none exists
                from models import ReferralCode
                new_code = ReferralCode.generate_code()
                
                # Create and save the new referral code
                referral_code = ReferralCode(
                    user_id=user.id,
                    code=new_code,
                    created_at=datetime.utcnow(),
                    is_active=True
                )
                
                db.session.add(referral_code)
                db.session.commit()
                
                logger.info(f"Generated new referral code for user {user_id}: {new_code}")
                return new_code
                
            except Exception as e:
                logger.error(f"Error generating referral code: {e}")
                return None


# Command handlers for telegram-python-bot integration
def register_referral_handlers(application, referral_manager):
    """
    Register the referral system handlers with the bot application.
    
    Args:
        application: The python-telegram-bot Application instance
        referral_manager: The ReferralManager instance
    """
    from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    
    # Register the referral command handler
    application.add_handler(CommandHandler("referral", lambda update, context: referral_command(update, context, referral_manager)))
    
    # Register callback handlers for referral buttons
    application.add_handler(CallbackQueryHandler(
        lambda update, context: share_referral_callback(update, context, referral_manager),
        pattern="^share_referral$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        lambda update, context: referral_stats_callback(update, context, referral_manager),
        pattern="^referral_stats$"
    ))


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE, referral_manager: ReferralManager) -> None:
    """
    Handle the /referral command to show referral program information.
    
    Args:
        update: The update object from Telegram
        context: The context object from python-telegram-bot
        referral_manager: The ReferralManager instance
    """
    user = update.effective_user
    query = update.callback_query
    
    if query:
        await query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
    else:
        chat_id = update.message.chat_id
        message_id = None
    
    # Get the user's referral stats
    stats = referral_manager.get_referral_stats(user.id)
    
    # Generate the referral code if needed
    if not stats['has_code']:
        code = referral_manager.generate_or_get_referral_code(user.id)
        if code:
            stats['code'] = code
            stats['has_code'] = True
            stats['referral_link'] = referral_manager.generate_referral_link(user.id)
    
    # Create the referral message
    referral_message = (
        "🔗 *THRIVE Referral Program*\n\n"
        "Earn by sharing THRIVE bot with your friends! When they start trading, you'll earn 5% of their profits automatically.\n\n"
        f"👥 *Your Referrals:* {stats['total_referrals']}\n"
        f"💰 *Total Earnings:* {stats['total_earnings']:.2f} SOL\n\n"
        "*Your Personal Referral Link:*\n"
    )
    
    if stats['referral_link']:
        referral_message += f"{stats['referral_link']}\n\n"
    else:
        referral_message += f"https://t.me/thrivesolanabot?start=ref_{user.id}\n\n"
    
    referral_message += (
        "*How It Works:*\n"
        "1. Share your link with friends\n"
        "2. When they deposit and start trading, you're connected\n"
        "3. Earn 5% of their profits with no limit!\n\n"
        "The more friends you refer, the more you earn."
    )
    
    # Create keyboard with referral options
    keyboard = [
        [InlineKeyboardButton("📋 Copy Referral Link", callback_data="copy_referral")],
        [InlineKeyboardButton("📊 View Earnings", callback_data="referral_stats")],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit the message
    if query and message_id:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=referral_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=referral_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def share_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, referral_manager: ReferralManager) -> None:
    """
    Handle the share referral button click.
    
    Args:
        update: The update object from Telegram
        context: The context object from python-telegram-bot
        referral_manager: The ReferralManager instance
    """
    query = update.callback_query
    await query.answer("Your referral link is ready to share!")
    
    user = update.effective_user
    
    # Get the user's referral code
    stats = referral_manager.get_referral_stats(user.id)
    
    # Generate the referral message
    share_message = (
        "👋 *Invite Your Friends*\n\n"
        "Share this message to invite friends to THRIVE Bot:\n\n"
        "───────────────\n"
        "🚀 Join me on THRIVE Bot - an automated Solana memecoin trading bot!\n\n"
        "✅ Automated trading\n"
        "✅ Daily profit potential\n"
        "✅ No trading experience needed\n\n"
    )
    
    if stats['has_code']:
        share_message += f"Use my referral link: {stats['referral_link']}\n"
    else:
        code = referral_manager.generate_or_get_referral_code(user.id)
        share_message += f"Use my referral link: https://t.me/thrivesolanabot?start=ref_{user.id}\n"
    
    share_message += "───────────────\n\n"
    share_message += "Forward this message or copy the link above."
    
    # Create keyboard with back button
    keyboard = [
        [InlineKeyboardButton("◀️ Back to Referrals", callback_data="referral")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=share_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def referral_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, referral_manager: ReferralManager) -> None:
    """
    Handle the view earnings/stats button click.
    
    Args:
        update: The update object from Telegram
        context: The context object from python-telegram-bot
        referral_manager: The ReferralManager instance
    """
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Get detailed referral stats
    stats = referral_manager.get_referral_stats(user.id)
    
    if not stats['has_code'] or stats['total_referrals'] == 0:
        # No referrals yet
        stats_message = (
            "📊 *Your Referral Stats*\n\n"
            "You haven't referred anyone yet.\n\n"
            "Share your referral link to start earning!\n\n"
        )
        
        if stats['has_code']:
            stats_message += f"Your code: `{stats['code']}`"
        else:
            code = referral_manager.generate_or_get_referral_code(user.id)
            stats_message += f"Your code: `{code}`"
    else:
        # Show detailed stats with referred users
        stats_message = (
            "📊 *Your Referral Stats*\n\n"
            f"Total Referrals: {stats['total_referrals']}\n"
            f"Active Referrals: {stats['active_referrals']}\n"
            f"Total Earnings: {stats['total_earnings']:.4f} SOL\n\n"
            "───────────────\n"
            "*Recent Referrals:*\n"
        )
        
        # Show up to 5 most recent referrals
        for i, user_info in enumerate(stats['referred_users'][:5]):
            status = "✅ Active" if user_info['is_active'] else "⏳ Pending"
            username = f"@{user_info['username']}" if user_info['username'] else "Anonymous"
            stats_message += f"{i+1}. {username} - {status}\n"
        
        stats_message += "───────────────\n\n"
        stats_message += "Earn 5% of the profits from each referred user!"
    
    # Create keyboard with back button
    keyboard = [
        [InlineKeyboardButton("💸 Invite More Friends", callback_data="share_referral")],
        [InlineKeyboardButton("◀️ Back to Referrals", callback_data="referral")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=stats_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


# For the bot_v20_runner.py version (direct API calls)
def register_referral_handlers_simple(bot, referral_manager):
    """
    Register the referral system handlers with the SimpleTelegramBot instance.
    
    Args:
        bot: The SimpleTelegramBot instance
        referral_manager: The ReferralManager instance
    """
    # Register the referral command handler
    bot.add_command_handler("/referral", lambda update, chat_id: referral_command_simple(update, chat_id, bot, referral_manager))
    
    # Register callback handlers for referral buttons
    bot.add_callback_handler("copy_referral", lambda update, chat_id: copy_referral_callback(update, chat_id, bot, referral_manager))
    bot.add_callback_handler("referral_stats", lambda update, chat_id: referral_stats_callback_simple(update, chat_id, bot, referral_manager))
    bot.add_callback_handler("share_referral", lambda update, chat_id: share_referral_callback_simple(update, chat_id, bot, referral_manager))
    bot.add_callback_handler("referral", lambda update, chat_id: referral_command_simple(update, chat_id, bot, referral_manager))


def referral_command_simple(update, chat_id, bot, referral_manager):
    """
    Handle the /referral command for the SimpleTelegramBot version.
    
    Args:
        update: The update dictionary from Telegram
        chat_id: The chat ID
        bot: The SimpleTelegramBot instance
        referral_manager: The ReferralManager instance
    """
    try:
        # Get user ID from the update
        user_id = str(update['message']['from']['id']) if 'message' in update else str(update['callback_query']['from']['id'])
        
        # Get the user's referral stats
        stats = referral_manager.get_referral_stats(user_id)
        
        # Generate the referral code if needed
        if not stats['has_code']:
            code = referral_manager.generate_or_get_referral_code(user_id)
            if code:
                stats['code'] = code
                stats['has_code'] = True
                stats['referral_link'] = referral_manager.generate_referral_link(user_id)
        
        # Create the referral message
        referral_message = (
            "🔗 *THRIVE Referral Program*\n\n"
            "Earn by sharing THRIVE bot with your friends! When they start trading, you'll earn 5% of their profits automatically.\n\n"
            f"👥 *Your Referrals:* {stats['total_referrals']}\n"
            f"💰 *Total Earnings:* {stats['total_earnings']:.2f} SOL\n\n"
            "*Your Personal Referral Link:*\n"
        )
        
        if stats['referral_link']:
            referral_message += f"{stats['referral_link']}\n\n"
        else:
            referral_message += f"https://t.me/thrivesolanabot?start=ref_{user_id}\n\n"
        
        referral_message += (
            "*How It Works:*\n"
            "1. Share your link with friends\n"
            "2. When they deposit and start trading, you're connected\n"
            "3. Earn 5% of their profits with no limit!\n\n"
            "The more friends you refer, the more you earn."
        )
        
        # Create keyboard with referral options
        keyboard = bot.create_inline_keyboard([
            [{"text": "📋 Copy Referral Link", "callback_data": "copy_referral"}],
            [{"text": "📊 View Earnings", "callback_data": "referral_stats"}],
            [{"text": "🏠 Back to Main Menu", "callback_data": "start"}]
        ])
        
        bot.send_message(chat_id, referral_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in referral_command_simple: {e}")
        bot.send_message(chat_id, "Error accessing referral program. Please try again later.")


def copy_referral_callback(update, chat_id, bot, referral_manager):
    """
    Handle the copy referral link button.
    
    Args:
        update: The update dictionary from Telegram
        chat_id: The chat ID
        bot: The SimpleTelegramBot instance
        referral_manager: The ReferralManager instance
    """
    try:
        # Get user ID from the update
        user_id = str(update['callback_query']['from']['id'])
        
        # Get the user's referral stats
        stats = referral_manager.get_referral_stats(user_id)
        
        # Generate the referral link
        if stats['has_code']:
            referral_link = stats['referral_link'] or f"https://t.me/thrivesolanabot?start=ref_{user_id}"
        else:
            code = referral_manager.generate_or_get_referral_code(user_id)
            referral_link = f"https://t.me/thrivesolanabot?start=ref_{user_id}"
        
        # Send confirmation message
        bot.send_message(
            chat_id,
            "✅ *Referral Link Copied!*\n\nShare this link with your friends:",
            parse_mode="Markdown"
        )
        
        # Send the link in a separate message for easy copying
        keyboard = bot.create_inline_keyboard([
            [{"text": "📊 View Stats", "callback_data": "referral_stats"}],
            [{"text": "◀️ Back to Referrals", "callback_data": "referral"}]
        ])
        
        bot.send_message(
            chat_id,
            f"`{referral_link}`",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in copy_referral_callback: {e}")
        bot.send_message(chat_id, "Error copying referral link. Please try again later.")


def share_referral_callback_simple(update, chat_id, bot, referral_manager):
    """
    Handle the share referral button for the SimpleTelegramBot version.
    
    Args:
        update: The update dictionary from Telegram
        chat_id: The chat ID
        bot: The SimpleTelegramBot instance
        referral_manager: The ReferralManager instance
    """
    try:
        # Get user ID from the update
        user_id = str(update['callback_query']['from']['id'])
        
        # Get the user's referral stats
        stats = referral_manager.get_referral_stats(user_id)
        
        # Generate the referral message
        share_message = (
            "👋 *Invite Your Friends*\n\n"
            "Share this message to invite friends to THRIVE Bot:\n\n"
            "───────────────\n"
            "🚀 Join me on THRIVE Bot - an automated Solana memecoin trading bot!\n\n"
            "✅ Automated trading\n"
            "✅ Daily profit potential\n"
            "✅ No trading experience needed\n\n"
        )
        
        if stats['has_code']:
            share_message += f"Use my referral link: {stats['referral_link']}\n"
        else:
            code = referral_manager.generate_or_get_referral_code(user_id)
            share_message += f"Use my referral link: https://t.me/thrivesolanabot?start=ref_{user_id}\n"
        
        share_message += "───────────────\n\n"
        share_message += "Forward this message or copy the link above."
        
        # Create keyboard with back button
        keyboard = bot.create_inline_keyboard([
            [{"text": "◀️ Back to Referrals", "callback_data": "referral"}]
        ])
        
        bot.send_message(chat_id, share_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in share_referral_callback_simple: {e}")
        bot.send_message(chat_id, "Error creating share message. Please try again later.")


def referral_stats_callback_simple(update, chat_id, bot, referral_manager):
    """
    Handle the view earnings/stats button for the SimpleTelegramBot version.
    
    Args:
        update: The update dictionary from Telegram
        chat_id: The chat ID
        bot: The SimpleTelegramBot instance
        referral_manager: The ReferralManager instance
    """
    try:
        # Get user ID from the update
        user_id = str(update['callback_query']['from']['id'])
        
        # Get detailed referral stats
        stats = referral_manager.get_referral_stats(user_id)
        
        if not stats['has_code'] or stats['total_referrals'] == 0:
            # No referrals yet
            stats_message = (
                "📊 *Your Referral Stats*\n\n"
                "You haven't referred anyone yet.\n\n"
                "Share your referral link to start earning!\n\n"
            )
            
            if stats['has_code']:
                stats_message += f"Your code: `{stats['code']}`"
            else:
                code = referral_manager.generate_or_get_referral_code(user_id)
                stats_message += f"Your code: `{code}`"
        else:
            # Show detailed stats with referred users
            stats_message = (
                "📊 *Your Referral Stats*\n\n"
                f"Total Referrals: {stats['total_referrals']}\n"
                f"Active Referrals: {stats['active_referrals']}\n"
                f"Total Earnings: {stats['total_earnings']:.4f} SOL\n\n"
                "───────────────\n"
                "*Recent Referrals:*\n"
            )
            
            # Show up to 5 most recent referrals
            for i, user_info in enumerate(stats['referred_users'][:5]):
                status = "✅ Active" if user_info['is_active'] else "⏳ Pending"
                username = f"@{user_info['username']}" if user_info['username'] else "Anonymous"
                stats_message += f"{i+1}. {username} - {status}\n"
            
            stats_message += "───────────────\n\n"
            stats_message += "Earn 5% of the profits from each referred user!"
        
        # Create keyboard with back button
        keyboard = bot.create_inline_keyboard([
            [{"text": "💸 Invite More Friends", "callback_data": "share_referral"}],
            [{"text": "◀️ Back to Referrals", "callback_data": "referral"}]
        ])
        
        bot.send_message(chat_id, stats_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in referral_stats_callback_simple: {e}")
        bot.send_message(chat_id, "Error retrieving referral stats. Please try again later.")


# Function to process referral links in start commands
def process_start_command_referral(start_parameter, user_id, referral_manager):
    """
    Process a start command with a potential referral parameter.
    
    Args:
        start_parameter: The start parameter from /start (e.g. 'ref_123456789')
        user_id: The Telegram ID of the user who started the bot
        referral_manager: The ReferralManager instance
        
    Returns:
        Tuple of (was_referred, referrer_id) if referral was processed
    """
    # Extract referral code from start parameter
    referrer_id = referral_manager.extract_referral_code(start_parameter)
    
    if not referrer_id:
        return False, None
    
    # Process the referral
    success = referral_manager.process_referral(user_id, referrer_id)
    
    return success, referrer_id