import logging
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.exc import SQLAlchemyError
from app import db, app
from models import User, UserStatus, ReferralCode
from utils.solana import generate_wallet_address

# Define conversation states
(WAITING_FOR_WALLET_ADDRESS,
 WAITING_FOR_CONFIRMATION) = range(2)

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message when the command /start is issued."""
    user = update.effective_user
    
    # Add typing animation for a more engaging experience
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1)  # Short delay to simulate typing
    
    # Try to import the message cleanup handlers
    try:
        from utils.message_handlers import send_start_message, cleanup_previous_messages
        # Clean up any welcome messages as we're moving to the start state
        await cleanup_previous_messages(update, context, ['welcome_message'])
    except ImportError:
        logger.debug("Message cleanup module not available")
    
    # Store user in database if not exists
    with app.app_context():
        try:
            existing_user = User.query.filter_by(telegram_id=str(user.id)).first()
            if not existing_user:
                # Create a new user record
                new_user = User(
                    telegram_id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    joined_at=datetime.utcnow(),
                    status=UserStatus.ONBOARDING
                )
                
                # Generate a referral code for the new user
                new_referral_code = ReferralCode(
                    user_id=None,  # Temporary placeholder, will update after user is committed
                    code=ReferralCode.generate_code(),
                    created_at=datetime.utcnow(),
                    is_active=True
                )
                
                db.session.add(new_user)
                db.session.flush()  # Flush to get the user ID
                
                # Update the referral code with the new user ID
                new_referral_code.user_id = new_user.id
                db.session.add(new_referral_code)
                db.session.commit()
                
                logger.info(f"New user registered: {user.id} - {user.username}")
                
                # Trust-building welcome message with clear language and benefit statements
                welcome_message = (
                    f"👋 *Welcome to THRIVE Bot*, {user.first_name}!\n\n"
                    "I'm your automated Solana memecoin trading assistant. I help grow your SOL by buying and selling "
                    "trending memecoins with safe, proven strategies. You retain full control of your funds at all times.\n\n"
                    "💰 No hidden fees, no hidden risks\n"
                    "⚡ Real-time trading 24/7\n"
                    "🔒 Your SOL stays under your control\n\n"
                    "To get started, please enter your *Solana wallet address* below.\n"
                    "This is where your profits will be sent when you withdraw."
                )
                
                # Try to use message cleanup system if available
                try:
                    from utils.message_handlers import send_start_message
                    await send_start_message(update, context, welcome_message)
                except ImportError:
                    # Fallback to standard message sending
                    await update.message.reply_text(
                        welcome_message,
                        parse_mode="Markdown"
                    )
                return WAITING_FOR_WALLET_ADDRESS
            else:
                logger.info(f"Returning user: {user.id} - {user.username}")
                # For existing users, show main menu
                await show_main_menu(update, context, user)
                return ConversationHandler.END
        except SQLAlchemyError as e:
            logger.error(f"Database error during user registration: {e}")
            db.session.rollback()
            
            error_message = "⚠️ Sorry, we encountered a database error. Please try again later."
            await update.message.reply_text(error_message)
            return ConversationHandler.END


async def process_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the wallet address provided by the user during onboarding."""
    user = update.effective_user
    
    # No skip option - wallet address is required
    
    # Normal wallet address processing
    wallet_address = update.message.text.strip()
    
    # Use the utility function for consistent wallet validation
    from utils.solana import is_valid_solana_address
    
    if not is_valid_solana_address(wallet_address):
        await update.message.reply_text(
            "⚠️ This doesn't look like a valid Solana wallet address.\n"
            "Please provide a valid Solana wallet address.\n\n"
            "Valid example: `rAg2CtT591ow7x7eXomCc4aEXyuu4At3sn92wrwygjj`",
            parse_mode="Markdown"
        )
        return WAITING_FOR_WALLET_ADDRESS
    
    # Store the wallet address in the database
    with app.app_context():
        try:
            user_record = User.query.filter_by(telegram_id=str(user.id)).first()
            if user_record:
                user_record.wallet_address = wallet_address
                db.session.commit()
                logger.info(f"Wallet address stored for user {user.id}")
                
                # Add typing animation
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                await asyncio.sleep(0.5)  # Short delay to simulate typing
                
                # First message - confirmation of wallet update
                wallet_updated_message = (
                    f"Payout wallet address updated to {wallet_address[:6]}..."
                    f"{wallet_address[-6:]}.\n\n"
                    f"It will be used for all future deposit payouts."
                )
                
                # Send the first confirmation message
                await update.message.reply_text(
                    wallet_updated_message,
                    parse_mode="Markdown"
                )
                
                # Add a slight delay to simulate real conversation flow
                await asyncio.sleep(0.8)
                
                # Second message - deposit instructions with exact design from the image
                deposit_instructions = (
                    f"Please send a minimum of *0.05 SOL (Solana)*\n"
                    f"and maximum *5000 SOL* to the following\n"
                    f"address.\n\n"
                    f"Once your deposit is received, it will be\n"
                    f"processed, and you'll be on your way to\n"
                    f"doubling your Solana in just 168 hours! The\n"
                    f"following wallet address is your deposit wallet:"
                )
                
                await update.message.reply_text(
                    deposit_instructions,
                    parse_mode="Markdown"
                )
                
                # Third message - Display the deposit wallet address
                deposit_wallet = generate_wallet_address()  # Generate a unique deposit wallet
                
                # Update user record with the deposit wallet
                user_record.deposit_wallet = deposit_wallet  # Make sure this field exists in your DB model
                db.session.commit()
                
                await update.message.reply_text(
                    f"`{deposit_wallet}`",
                    parse_mode="Markdown"
                )
                
                # Final message - Buttons arranged in a 2x2 grid
                keyboard = [
                    [InlineKeyboardButton("📋 Copy Address", callback_data="copy_address"), 
                     InlineKeyboardButton("✅ Deposit Done", callback_data="deposit_confirmed")],
                    [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start"), 
                     InlineKeyboardButton("❓ Help", callback_data="help")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "...",  # Empty text, just showing buttons
                    reply_markup=reply_markup
                )
                
                # We don't immediately show the main menu here - let user complete the deposit process
                return ConversationHandler.END
            else:
                logger.error(f"User {user.id} not found in database during wallet address processing")
                await update.message.reply_text("Sorry, we couldn't find your user record. Please try /start again.")
                return ConversationHandler.END
        except SQLAlchemyError as e:
            logger.error(f"Database error storing wallet address: {e}")
            db.session.rollback()
            
            error_message = "⚠️ Sorry, we encountered a database error. Please try again later."
            await update.message.reply_text(error_message)
            return ConversationHandler.END


async def show_main_menu(update, context, user):
    """Show the main menu with buttons."""
    # Add typing animation for a more engaging experience
    if update.message:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(0.7)  # Short delay to simulate typing
    
    welcome_message = (
        f"👋 *Welcome to THRIVE*, {user.first_name}!\n\n"
        "I'm your automated Solana memecoin trading assistant. I help grow your SOL by buying and selling "
        "trending memecoins with safe, proven strategies. You retain full control of your funds at all times.\n\n"
        "✅ *Current Status*: Ready to help you trade\n"
        "⏰ *Trading Hours*: 24/7 automated monitoring\n"
        "🔒 *Security*: Your SOL stays under your control\n\n"
        "Choose an option below to get started on your trading journey!"
    )
    
    # Improved button layout with better organization and emojis
    keyboard = [
        # First row - primary actions
        [
            InlineKeyboardButton("💰 Deposit SOL", callback_data="deposit"),
            InlineKeyboardButton("📊 Dashboard", callback_data="view_dashboard")
        ],
        # Second row - information and features
        [
            InlineKeyboardButton("ℹ️ How It Works", callback_data="how_it_works"),
            InlineKeyboardButton("🔗 Referral Program", callback_data="referral")
        ],
        # Third row - settings and help
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Try to use message cleanup system if available
    try:
        from utils.message_handlers import send_or_edit_message
        await send_or_edit_message(
            update, 
            context, 
            welcome_message, 
            'main_menu', 
            'main_menu',
            reply_markup,
            "Markdown"
        )
    except ImportError:
        # Fallback to standard message methods
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=welcome_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=welcome_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )


async def how_it_works_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain how the bot works."""
    query = update.callback_query
    await query.answer()
    
    explanation = (
        "🚀 *How THRIVE Works*\n\n"
        "1️⃣ *Deposit SOL* to activate your trading account\n"
        "2️⃣ Our algorithms *automatically trade* trending Solana memecoins like BONK, WIF, and BOME\n"
        "3️⃣ Advanced market analysis and timing helps *maximize your profits*\n"
        "4️⃣ Receive *real-time updates* on your dashboard\n"
        "5️⃣ *Withdraw your profits* anytime with zero lock-up periods\n\n"
        "💰 *Boost Your Earnings*: Invite friends and earn 5% of their profits through our referral program!\n\n"
        "*Our Strategy*: THRIVE analyzes social media sentiment, trading volume, and market momentum "
        "to catch promising memecoins before they explode in value. We use sophisticated entry and exit "
        "strategies based on real-time market conditions.\n\n"
        "⚠️ *Disclaimer*: Trading cryptocurrency involves risk. Past performance is not indicative of future results."
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Deposit SOL", callback_data="deposit")],
        [InlineKeyboardButton("🔗 Referral Program", callback_data="referral")],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Try to use message cleanup system if available
    try:
        from utils.message_handlers import send_or_edit_message
        await send_or_edit_message(
            update, 
            context, 
            explanation, 
            'how_it_works', 
            'how_it_works',
            reply_markup,
            "Markdown"
        )
    except ImportError:
        # Fallback to standard edit message
        await query.edit_message_text(
            text=explanation,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def skip_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the skip wallet button press."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    with app.app_context():
        try:
            user_record = User.query.filter_by(telegram_id=str(user.id)).first()
            if user_record:
                logger.info(f"User {user.id} skipped wallet address entry via button")
                
                # Generate a temporary address
                temp_address = f"temp_{user.id}_{int(datetime.utcnow().timestamp())}"
                user_record.wallet_address = temp_address
                db.session.commit()
                
                # Add typing animation
                await context.bot.send_chat_action(chat_id=query.message.chat_id, action="typing")
                await asyncio.sleep(0.5)  # Short delay to simulate typing
                
                skip_message = (
                    "✅ *Wallet setup skipped!*\n\n"
                    "You can always add your wallet address later in the Settings menu.\n\n"
                    "🎉 *Your THRIVE bot is ready to go!*\n\n"
                    "• Make a deposit to start growing your SOL\n"
                    "• Explore your real-time trading dashboard\n"
                    "• Invite friends to earn bonus profits\n\n"
                    "We're excited to help you discover the potential of Solana memecoins trading!"
                )
                
                keyboard = [
                    [InlineKeyboardButton("💰 Deposit SOL", callback_data="deposit")],
                    [InlineKeyboardButton("📊 View Dashboard", callback_data="view_dashboard")],
                    [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=skip_message,
                    reply_markup=reply_markup
                )
            else:
                logger.error(f"User {user.id} not found in database during skip processing")
                await query.edit_message_text("Sorry, we couldn't find your user record. Please try /start again.")
        except SQLAlchemyError as e:
            logger.error(f"Database error during skip processing: {e}")
            db.session.rollback()
            
            error_message = "⚠️ Sorry, we encountered a database error. Please try again later."
            await query.edit_message_text(error_message)
