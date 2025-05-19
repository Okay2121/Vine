import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from app import db
from models import User, UserStatus
from utils.solana import generate_wallet_address

# Define conversation states
(WAITING_FOR_WALLET_ADDRESS,
 WAITING_FOR_CONFIRMATION) = range(2)

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message when the command /start is issued."""
    user = update.effective_user
    
    logger.info(f"User {user.id} ({user.username}) initiated /start command")
    
    welcome_message = (
        f"👋 Welcome to SolanaMemobot, {user.first_name}! I'm your automated Solana memecoin trading assistant. \n\n"
        "We help grow your SOL by buying/selling trending memecoins with safe, automated strategies. "
        "You retain control of your funds at all times.\n\n"
        "Use /deposit to add funds and start trading!\n"
        "Use /help to see all available commands.\n"
    )
    
    # Create a keyboard with basic options
    keyboard = [
        [InlineKeyboardButton("How It Works", callback_data="how_it_works")],
        [InlineKeyboardButton("Deposit SOL", callback_data="deposit")],
        [InlineKeyboardButton("Referral Program 💰", callback_data="referral")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    return ConversationHandler.END

async def process_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the wallet address provided by the user."""
    user = update.effective_user
    wallet_address = update.message.text.strip()
    
    # Simple validation for Solana wallet address
    if len(wallet_address) < 20 or not any(prefix in wallet_address for prefix in ["So", "so", "So1", "De", "Mem"]):
        await update.message.reply_text(
            "This doesn't look like a valid Solana wallet address. \n"
            "Please provide a valid Solana wallet address."
        )
        return WAITING_FOR_WALLET_ADDRESS
    
    logger.info(f"Received wallet address from user {user.id}")
    
    confirmation_message = (
        f"✅ Thank you! Your wallet address {wallet_address[:6]}...{wallet_address[-4:]} has been saved. \n\n"
        "This address will be used for all future withdrawals."
    )
    
    await update.message.reply_text(confirmation_message)
    
    # Show the main menu
    await show_main_menu(update, context, user)
    return ConversationHandler.END

async def show_main_menu(update, context, user):
    """Show the main menu with buttons."""
    welcome_message = (
        f"👋 Welcome to SolanaMemobot, {user.first_name}! I'm your automated Solana memecoin trading assistant. "
        "We help grow your SOL by buying/selling trending memecoins with safe, automated strategies. "
        "You retain control of your funds at all times."
    )
    
    keyboard = [
        [InlineKeyboardButton("How It Works", callback_data="how_it_works")],
        [InlineKeyboardButton("Deposit SOL", callback_data="deposit")],
        [InlineKeyboardButton("Referral Program 💰", callback_data="referral")],
        [InlineKeyboardButton("Settings", callback_data="settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def how_it_works_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain how the bot works."""
    query = update.callback_query
    await query.answer()
    
    explanation = (
        "🤖 *How SolanaMemobot Works*\n\n"
        "1️⃣ Deposit SOL to activate the bot\n"
        "2️⃣ The bot simulates trades on trending Solana memecoins\n"
        "3️⃣ Our algorithms target 1% daily profit (simulated)\n"
        "4️⃣ You'll receive daily updates on your performance\n"
        "5️⃣ Track your profits and withdraw anytime\n\n"
        "💰 *Earn More*: Refer friends and earn 5% of their profits!\n\n"
        "*Our Strategy*: We analyze market trends, trading volume, and social media sentiment "
        "to identify promising memecoin opportunities before they go viral.\n\n"
        "⚠️ *Disclaimer*: Past performance is not indicative of future results. Cryptocurrency "
        "trading involves risk."
    )
    
    keyboard = [
        [InlineKeyboardButton("Deposit SOL", callback_data="deposit")],
        [InlineKeyboardButton("Referral Program", callback_data="referral")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=explanation,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
