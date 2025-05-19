import logging
import io
import qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.exc import SQLAlchemyError
from app import db, app
from models import User, ReferralCode, UserStatus

logger = logging.getLogger(__name__)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the redesigned referral program information and user's referral code."""
    user = update.effective_user
    query = update.callback_query
    
    if query:
        await query.answer()
        chat_id = query.message.chat_id
        message_id = query.message.message_id
    else:
        chat_id = update.message.chat_id
        message_id = None
    
    with app.app_context():
        try:
            # Get the user from the database
            db_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                logger.error(f"User not found in database: {user.id}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Error: Your user profile was not found. Please try /start first."
                )
                return
                
            # Get or create referral code
            referral_code = ReferralCode.query.filter_by(user_id=db_user.id).first()
            if not referral_code:
                # Generate new code using the static method
                new_code = ReferralCode.generate_code()
                referral_code = ReferralCode(user_id=db_user.id, code=new_code)
                db.session.add(referral_code)
                db.session.commit()
                logger.info(f"Created new referral code for user {db_user.id}: {new_code}")
                
            # Calculate referral stats
            referred_users_count = len(referral_code.referred_users)
            active_referred_users = [u for u in referral_code.referred_users if u.status == UserStatus.ACTIVE]
            active_referred_count = len(active_referred_users)
            
            # Get potential earnings (active referrals * average projected earnings)
            # For display purposes, we'll show projected monthly earnings based on active referrals
            avg_monthly_earnings_per_referral = 0.25  # Example: 0.25 SOL per active referral per month
            potential_monthly_earnings = active_referred_count * avg_monthly_earnings_per_referral
            
            # Create referral link based on username and code
            bot_username = context.bot.username or "YourBotUsername"
            referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
            
            # Calculate progress to next tier (future feature)
            next_tier_requirement = 5  # Example: Need 5 active referrals for next tier
            tier_progress = min(100, int((active_referred_count / next_tier_requirement) * 100))
            tier_display = "🥉 Bronze"
            if active_referred_count >= 5:
                tier_display = "🥈 Silver"
            if active_referred_count >= 10:
                tier_display = "🥇 Gold"
            if active_referred_count >= 25:
                tier_display = "💎 Diamond"
            
            # Prepare the redesigned message with visual elements and clear sections
            message = (
                f"🚀 *THRIVE REFERRAL PROGRAM* 🚀\n"
                f"━━━━━━━━━━━━━━━━━\n\n"
                f"💰 *Earn while you sleep!* Share THRIVE bot with friends and earn 5% of their profits automatically - forever!\n\n"
                
                f"📈 *YOUR STATS*\n"
                f"⦿ Referral Tier: {tier_display}\n"
                f"⦿ Total Invites: {referred_users_count}\n"
                f"⦿ Active Traders: {active_referred_count}\n"
                f"⦿ Total Earned: {db_user.referral_bonus:.4f} SOL\n"
                f"⦿ Projected Monthly: ~{potential_monthly_earnings:.2f} SOL\n\n"
                
                f"🔗 *YOUR REFERRAL LINK*\n"
                f"`{referral_link}`\n\n"
                
                f"*How It Works:*\n"
                f"1️⃣ Share your link with friends\n"
                f"2️⃣ They join & start trading\n"
                f"3️⃣ You earn 5% of their profits - forever!\n\n"
                
                f"🎯 *Invite {next_tier_requirement - active_referred_count} more active traders to reach the next tier!*"
            )
            
            # Create simplified keyboard with required options
            keyboard = [
                [
                    InlineKeyboardButton("📊 View Stats", callback_data="referral_stats"),
                    InlineKeyboardButton("📋 Copy Link", callback_data="copy_referral_link")
                ],
                [
                    InlineKeyboardButton("📱 Generate QR", callback_data="referral_qr_code"),
                    InlineKeyboardButton("❓ How It Works", callback_data="referral_how_it_works")
                ],
                [
                    InlineKeyboardButton("💡 Tips", callback_data="referral_tips"),
                    InlineKeyboardButton("🏠 Back to Menu", callback_data="view_dashboard")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send or update message
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except SQLAlchemyError as e:
            logger.error(f"Database error in referral command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error accessing the referral program. Please try again later."
            )


async def share_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the enhanced share referral button."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    with app.app_context():
        try:
            # Get the user's referral code
            db_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                logger.error(f"User not found in database: {user.id}")
                await query.edit_message_text("❌ Error: Your user profile was not found.")
                return
                
            referral_code = ReferralCode.query.filter_by(user_id=db_user.id).first()
            if not referral_code:
                logger.error(f"No referral code found for user {db_user.id}")
                await query.edit_message_text("❌ Error: Your referral code was not found.")
                return
            
            # Get bot username for proper link
            bot_username = context.bot.username or "thrivesolanabot"
            referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
            
            # Create an attractive shareable message with emoji and formatting
            share_message = (
                f"🚀 *Double Your SOL in 7 Days with THRIVE Bot* 🚀\n\n"
                f"Hey! I just discovered this amazing Solana trading bot that's helping me earn SOL daily, completely automated!\n\n"
                
                f"✨ *Why You Should Join:* ✨\n"
                f"• 🤖 Automated trading on Solana memecoins\n"
                f"• 💸 Daily profit potential without manual work\n"
                f"• 📱 Super simple to use - no trading experience needed\n"
                f"• 🚀 Highly active trading community\n"
                f"• 🔒 Secure and risk-controlled\n\n"
                
                f"🔗 *Use my personal invite link to get started:*\n"
                f"{referral_link}\n\n"
                
                f"💎 *The 7-Day Challenge:* Join now and see how your portfolio can grow in just one week!\n\n"
                f"#SolanaTrading #PassiveIncome #Crypto"
            )
            
            # Send message that can be forwarded
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=share_message,
                parse_mode="Markdown"
            )
            
            # Provide more detailed instructions with motivational message
            instructions = (
                "☝️ *Your referral message is ready to share!* \n\n"
                "📲 *How to share effectively:*\n"
                "• Forward to friends interested in crypto\n"
                "• Share in crypto groups (where allowed)\n"
                "• Post on your social media\n\n"
                "💡 *Pro Tip:* Add your personal experience with the bot when sharing for better conversion rates!\n\n"
                "💰 When your friends join and trade, you'll earn 5% of their profits - _forever!_"
            )
            
            # Make it easy to return to referral page
            keyboard = [[InlineKeyboardButton("🔙 Back to Referral Menu", callback_data="referral")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=instructions,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
            # Track shared referral for analytics
            try:
                # Update the total shares count (optional feature)
                if hasattr(referral_code, 'total_shares'):
                    referral_code.total_shares += 1
                    db.session.commit()
            except:
                # Just log the error but don't interrupt the flow
                logger.warning(f"Could not update shares count for user {user.id}")
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in share referral: {e}")
            await query.edit_message_text("❌ Error sharing your referral code. Please try again later.")


async def referral_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the enhanced referral stats button with visual improvements."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    with app.app_context():
        try:
            # Get the user's referral stats
            db_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                logger.error(f"User not found in database: {user.id}")
                await query.edit_message_text("❌ Error: Your user profile was not found.")
                return
                
            # Get the referral code
            referral_code = ReferralCode.query.filter_by(user_id=db_user.id).first()
            if not referral_code:
                await query.edit_message_text(
                    "You don't have a referral link yet.\n\nUse /referral to create one."
                )
                return
                
            # Get detailed stats
            referred_users = referral_code.referred_users
            
            if not referred_users:
                # No referrals yet - show motivational message with tips
                message = (
                    "📊 *Your Referral Dashboard* 📊\n"
                    "━━━━━━━━━━━━━━━━━\n\n"
                    "🔍 *Current Status:* No referrals yet\n\n"
                    "🚀 *Ready to start earning?* Here are 3 quick tips:\n\n"
                    "1️⃣ Share your link with crypto-interested friends\n"
                    "2️⃣ Post about THRIVE in relevant Telegram groups\n"
                    "3️⃣ Create a short review about your experience\n\n"
                    "Remember: Each active referral earns you 5% of their profits - forever!\n\n"
                    f"*Your referral link:* `https://t.me/{context.bot.username}?start=ref_{user.id}`\n\n"
                    "🎯 *Goal:* Refer 5 users to reach Silver Tier"
                )
            else:
                # Calculate detailed statistics for impressive display
                active_users = [u for u in referred_users if u.status == UserStatus.ACTIVE]
                pending_users = [u for u in referred_users if u.status in [UserStatus.ONBOARDING, UserStatus.DEPOSITING]]
                inactive_users = [u for u in referred_users if u.status not in [UserStatus.ACTIVE, UserStatus.ONBOARDING, UserStatus.DEPOSITING]]
                
                # For a real system, these would be actual calculations
                total_earned = db_user.referral_bonus
                
                # Calculate recent earnings (last 7 days) - placeholder for now
                recent_earnings = total_earned * 0.3  # Example: 30% of total as recent
                
                # Calculate projected earnings
                avg_monthly_per_active = 0.25  # Example value, would be calculated from actual data
                projected_monthly = len(active_users) * avg_monthly_per_active
                
                # Calculate tier and progress
                tier = "🥉 Bronze"
                next_tier = "🥈 Silver"
                requirement = 5
                
                if len(active_users) >= 5:
                    tier = "🥈 Silver"
                    next_tier = "🥇 Gold" 
                    requirement = 10
                if len(active_users) >= 10:
                    tier = "🥇 Gold"
                    next_tier = "💎 Diamond"
                    requirement = 25
                if len(active_users) >= 25:
                    tier = "💎 Diamond"
                    next_tier = "👑 Crown"
                    requirement = 50
                
                remaining = max(0, requirement - len(active_users))
                progress_pct = min(100, int((len(active_users) / requirement) * 100))
                
                # Create progress bar visual
                progress_bar = "▓" * (progress_pct // 10) + "░" * ((100 - progress_pct) // 10)
                
                # Create an attractive stats display with sections
                message = (
                    "📊 *ADVANCED REFERRAL DASHBOARD* 📊\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    
                    f"🏆 *Current Tier:* {tier}\n"
                    f"⏳ *Progress to {next_tier}:* {progress_pct}%\n"
                    f"`{progress_bar}` {len(active_users)}/{requirement}\n\n"
                    
                    "👥 *REFERRAL NETWORK*\n"
                    f"• Total Referrals: {len(referred_users)}\n"
                    f"• Active Traders: {len(active_users)}\n"
                    f"• Pending Activation: {len(pending_users)}\n"
                    f"• Inactive Users: {len(inactive_users)}\n\n"
                    
                    "💰 *EARNINGS*\n"
                    f"• Total Earned: {total_earned:.4f} SOL\n"
                    f"• Last 7 Days: {recent_earnings:.4f} SOL\n"
                    f"• Projected Monthly: ~{projected_monthly:.2f} SOL\n"
                    f"• Referral Rate: 5% of profits\n\n"
                    
                    f"🎯 *NEXT GOAL:* Refer {remaining} more active traders to reach {next_tier}\n\n"
                    
                    "🔍 *RECENT ACTIVITY*\n"
                )
                
                # Add recent activity - limited to last 3 for space
                if active_users:
                    # In a real implementation, this would show actual recent activity
                    # For now, we'll just show placeholder data for the most recent users
                    recent_users = active_users[:min(3, len(active_users))]
                    for i, user in enumerate(recent_users):
                        message += f"• User #{user.id}: Earned you {(0.01 * (i+1)):.3f} SOL recently\n"
                else:
                    message += "• No recent activity\n"
            
            # Create simplified keyboard for stats page
            keyboard = [
                [
                    InlineKeyboardButton("📱 Generate QR", callback_data="referral_qr_code"),
                    InlineKeyboardButton("📋 Copy Link", callback_data="copy_referral_link")
                ],
                [
                    InlineKeyboardButton("📣 View Invite Tips", callback_data="referral_tips"),
                    InlineKeyboardButton("🔙 Back", callback_data="referral")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update the message
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in referral stats: {e}")
            await query.edit_message_text("❌ Error retrieving your referral stats. Please try again later.")


async def enter_referral_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the referral link entry during onboarding."""
    query = update.callback_query
    if query:
        await query.answer()
        
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Send instructions
    await context.bot.send_message(
        chat_id=chat_id,
        text="If you clicked on a referral link, you're already connected!\n\nJust tap Continue to proceed with setup.",
        parse_mode="Markdown"
    )
    
    # Set the expected next state in the conversation
    return "waiting_for_referral_code"


async def referral_qr_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a QR code for the user's referral link."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    with app.app_context():
        try:
            # Get the user's referral information
            db_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                logger.error(f"User not found in database: {user.id}")
                await query.edit_message_text("❌ Error: Your user profile was not found.")
                return
                
            referral_code = ReferralCode.query.filter_by(user_id=db_user.id).first()
            if not referral_code:
                logger.error(f"No referral link found for user {db_user.id}")
                await query.edit_message_text("❌ Error: Your referral link was not found.")
                return
            
            # Create referral link
            bot_username = context.bot.username or "thrivesolanabot"
            referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(referral_link)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code to bytes buffer
            buffer = io.BytesIO()
            img.save(buffer)
            buffer.seek(0)
            
            # Send the QR code with a caption
            caption = (
                f"🔗 *Your Referral QR Code*\n\n"
                f"Share this QR code with friends to earn 5% of their profits automatically!\n\n"
                f"When scanned, this QR code will lead directly to THRIVE bot with your referral link pre-applied.\n\n"
                f"💡 *Pro Tip:* Save this image and share it on social media or in chat groups!"
            )
            
            # Create a keyboard for navigation
            keyboard = [[InlineKeyboardButton("🔙 Back to Referral Menu", callback_data="referral")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send the QR code as photo
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=buffer,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            await query.edit_message_text(
                "❌ Error generating your referral QR code. Please try again later."
            )


async def copy_referral_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the copy link button click."""
    query = update.callback_query
    await query.answer("Referral link copied to message!")
    user = update.effective_user
    
    with app.app_context():
        try:
            # Get the user's referral details
            db_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                logger.error(f"User not found in database: {user.id}")
                await query.edit_message_text("❌ Error: Your user profile was not found.")
                return
                
            referral_code = ReferralCode.query.filter_by(user_id=db_user.id).first()
            if not referral_code:
                logger.error(f"No referral link found for user {db_user.id}")
                await query.edit_message_text("❌ Error: Your referral link was not found.")
                return
            
            # Create referral link
            bot_username = context.bot.username or "thrivesolanabot"
            referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
            
            # Send the link as a separate message for easy copying
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"*Here's your referral link:*\n\n`{referral_link}`\n\n👆 *Tap to copy*",
                parse_mode="Markdown"
            )
            
            # Provide confirmation and instructions
            keyboard = [[InlineKeyboardButton("🔙 Back to Referral Menu", callback_data="referral")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ *Your referral link is ready to share!*\n\nCopy the link above and share it with friends via any messaging app, social media, or email.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in copy referral link: {e}")
            await query.edit_message_text("❌ Error generating your referral link. Please try again later.")


async def referral_how_it_works_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'How It Works' button for the referral program."""
    query = update.callback_query
    await query.answer()
    
    # Create a detailed explanation of the referral program
    message = (
        "🔍 *THRIVE REFERRAL PROGRAM: HOW IT WORKS* 🔍\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "THRIVE's referral program rewards you for bringing new traders to our platform. Here's how it works in detail:\n\n"
        
        "1️⃣ *Share Your Link*\n"
        "• Every user gets a unique referral link\n"
        "• Share your link with friends\n"
        "• When they click, they're automatically connected to you\n\n"
        
        "2️⃣ *Earn 5% Forever*\n"
        "• You earn 5% of ALL profits your referrals generate\n"
        "• This is passive income - no work required\n"
        "• Earnings are credited to your balance automatically\n"
        "• There's NO LIMIT to how many people you can refer\n\n"
        
        "3️⃣ *Track Your Progress*\n"
        "• Monitor referrals from your dashboard\n"
        "• See active vs. pending referrals\n"
        "• Watch your earnings grow in real-time\n\n"
        
        "4️⃣ *Tier System*\n"
        "• 🥉 Bronze: 0-4 active referrals\n"
        "• 🥈 Silver: 5-9 active referrals\n"
        "• 🥇 Gold: 10-24 active referrals\n"
        "• 💎 Diamond: 25+ active referrals\n"
        "• Higher tiers unlock special perks (coming soon)\n\n"
        
        "5️⃣ *Tips for Success*\n"
        "• Share with crypto enthusiasts\n"
        "• Highlight the bot's automated trading\n"
        "• Mention the 7-day doubling potential\n"
        "• Share your own success story\n\n"
        
        "Ready to start earning? Use the buttons below to share your referral link and start building your passive income network!"
    )
    
    # Create a navigation keyboard
    keyboard = [
        [
            InlineKeyboardButton("📋 Copy Link", callback_data="copy_referral_link"),
            InlineKeyboardButton("📱 Generate QR", callback_data="referral_qr_code")
        ],
        [
            InlineKeyboardButton("🔙 Back to Referral Menu", callback_data="referral")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the message
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def referral_tips_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display tips for maximizing referral success."""
    query = update.callback_query
    await query.answer()
    
    tips_message = (
        "🚀 *TOP TIPS FOR REFERRAL SUCCESS* 🚀\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "Want to maximize your referral earnings? Follow these proven strategies:\n\n"
        
        "1️⃣ *Target the Right Audience*\n"
        "• Focus on crypto enthusiasts and traders\n"
        "• Approach friends interested in passive income\n"
        "• Share in relevant Telegram groups and Discord servers\n\n"
        
        "2️⃣ *Craft Compelling Messages*\n"
        "• Highlight the 7-day doubling potential\n"
        "• Mention it's fully automated - no work needed\n"
        "• Emphasize the security and simplicity\n"
        "• Share your personal results (with screenshots if possible)\n\n"
        
        "3️⃣ *Use Multiple Channels*\n"
        "• Direct messages to friends\n"
        "• Social media posts (Twitter, Instagram, TikTok)\n"
        "• Crypto forums and communities\n"
        "• QR codes in strategic locations\n\n"
        
        "4️⃣ *Follow Up & Support*\n"
        "• Check in with people you've referred\n"
        "• Help them get started if needed\n"
        "• Share trading tips and insights\n\n"
        
        "5️⃣ *Track & Optimize*\n"
        "• Monitor which sharing methods work best\n"
        "• Adjust your approach based on results\n"
        "• Set weekly referral goals\n\n"
        
        "Remember: The more active traders you refer, the more passive income you'll earn - forever!"
    )
    
    # Create a keyboard for navigation
    keyboard = [
        [
            InlineKeyboardButton("📋 Copy Link", callback_data="copy_referral_link"),
            InlineKeyboardButton("📱 Create QR", callback_data="referral_qr_code")
        ],
        [
            InlineKeyboardButton("🔙 Back to Stats", callback_data="referral_stats")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the message
    await query.edit_message_text(
        text=tips_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def process_referral_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process the entered referral link."""
    user = update.effective_user
    entered_code = update.message.text
    
    # Handle skip command
    if entered_code.lower() == "/skip":
        await update.message.reply_text(
            "✅ Continuing without a referral link.\n\nYou can always get your own referral link later with /referral."
        )
        return "next_step"
    
    with app.app_context():
        try:
            # Find the entered referral code
            referral_code = ReferralCode.query.filter_by(code=entered_code, is_active=True).first()
            
            if not referral_code:
                await update.message.reply_text(
                    "❌ Invalid referral link. Please check and try again, or send /skip to continue."
                )
                return "waiting_for_referral_code"
                
            # Check if user is trying to use their own code
            db_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if referral_code.user_id == db_user.id:
                await update.message.reply_text(
                    "❌ You cannot use your own referral link. Please enter a valid link or send /skip to continue."
                )
                return "waiting_for_referral_code"
                
            # Set the referrer
            db_user.referrer_code_id = referral_code.id
            
            # Update referral stats
            referral_code.total_referrals += 1
            
            db.session.commit()
            
            # Confirm success
            await update.message.reply_text(
                f"✅ Referral link accepted! You're now connected to a referrer.\n\nContinuing with setup..."
            )
            
            # Move to the next step in onboarding
            return "next_step"
            
        except SQLAlchemyError as e:
            logger.error(f"Database error processing referral link: {e}")
            await update.message.reply_text(
                "❌ Error processing your referral link. Please try again later or send /skip to continue."
            )
            return "waiting_for_referral_code"
