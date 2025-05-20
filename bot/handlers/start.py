"""
Start handler module
Handles the /start command and onboarding process
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Constants for ConversationHandler states
WAITING_FOR_WALLET_ADDRESS = 1
WAITING_FOR_CONFIRMATION = 2

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command - entry point for new users"""
    user = update.effective_user
    
    # Create welcome message with greeting and bot introduction
    message = (
        f"👋 Welcome, {user.first_name}!\n\n"
        f"I'm your Solana Memecoin Trading Bot. I help you earn profits "
        f"through automated Solana memecoin trading.\n\n"
        f"📈 Features:\n"
        f"• Automated trading\n"
        f"• Consistent ROI tracking\n"
        f"• Secure deposits and withdrawals\n"
        f"• Referral rewards\n\n"
        f"🚀 Let's get started!"
    )
    
    # Create keyboard with get started button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ How it Works", callback_data="how_it_works")],
        [InlineKeyboardButton("💰 Get Started", callback_data="get_started")]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard)
    return ConversationHandler.END

async def how_it_works_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'How it Works' button click"""
    query = update.callback_query
    await query.answer()
    
    # Create explanation message
    message = (
        "🤖 *How the Trading Bot Works*\n\n"
        "1️⃣ *Deposit SOL* to your trading account\n\n"
        "2️⃣ Our bot *automatically trades* Solana memecoins using advanced algorithms\n\n"
        "3️⃣ *Profits are added* to your balance regularly\n\n"
        "4️⃣ *Withdraw anytime* or reinvest for compound growth\n\n"
        "5️⃣ Track performance in your dashboard\n\n"
        "Ready to start trading?"
    )
    
    # Create keyboard with onboarding options
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("👥 Referrals", callback_data="referral")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
    return ConversationHandler.END

async def get_started_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Get Started' button click - start onboarding process"""
    query = update.callback_query
    await query.answer()
    
    # Ask for wallet address
    message = (
        "To start trading, I need your Solana wallet address for withdrawals.\n\n"
        "Please enter your Solana wallet address (starts with a SOL address):"
    )
    
    await query.edit_message_text(message)
    return WAITING_FOR_WALLET_ADDRESS

async def process_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the user's submitted wallet address"""
    wallet_address = update.message.text.strip()
    
    # Basic validation - should be enhanced with actual Solana address validation
    if len(wallet_address) < 30 or not wallet_address.startswith(('So', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
        await update.message.reply_text(
            "❌ That doesn't look like a valid Solana wallet address. Please provide a valid Solana address."
        )
        return WAITING_FOR_WALLET_ADDRESS
    
    # Store wallet address in user context
    context.user_data['wallet_address'] = wallet_address
    
    # Ask for confirmation
    message = (
        f"Please confirm your Solana wallet address:\n\n"
        f"`{wallet_address}`\n\n"
        f"Is this correct? Type 'yes' to confirm or enter a different address."
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")
    return WAITING_FOR_CONFIRMATION

def register_start_handlers(application: Application):
    """Register all handlers related to the start command"""
    # Add the conversation handler for onboarding
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CallbackQueryHandler(get_started_callback, pattern="^get_started$")
        ],
        states={
            WAITING_FOR_WALLET_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet_address)
            ],
            WAITING_FOR_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet_address)
            ]
        },
        fallbacks=[CommandHandler("start", start_command)]
    )
    
    # Register the conversation handler
    application.add_handler(conv_handler)
    
    # Register callback query handler for "how it works"
    application.add_handler(
        CallbackQueryHandler(how_it_works_callback, pattern="^how_it_works$")
    )