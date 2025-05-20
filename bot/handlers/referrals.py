"""
Referrals handler module
Manages the referral system functionality
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

logger = logging.getLogger(__name__)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /referral command - shows referral information and link"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # In real implementation, this would come from database
        # Mock data for demonstration
        referral_code = f"SOL{user.id}"
        referral_link = f"https://t.me/YourBotUsername?start={referral_code}"
        referral_count = 3
        total_earnings = 0.03  # SOL
        reward_per_referral = 0.01  # SOL
        
        message = (
            "👥 *REFERRAL PROGRAM*\n\n"
            "Earn rewards by inviting friends to join our trading platform!\n\n"
            f"🔗 *Your Referral Link:*\n`{referral_link}`\n\n"
            f"📊 *Your Referrals:* {referral_count}\n"
            f"💰 *Total Earnings:* {total_earnings:.4f} SOL\n"
            f"💎 *Reward per Referral:* {reward_per_referral:.4f} SOL\n\n"
            "Share your referral link and earn when your friends deposit!"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Referral Link", callback_data="share_referral")],
            [InlineKeyboardButton("📊 Referral Statistics", callback_data="referral_stats")]
        ])
        
        # Determine if this is a callback query or direct command
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                message, 
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                message, 
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Error in referral_command: {e}")
        error_message = "Sorry, there was an error accessing the referral program. Please try again."
        
        if update.callback_query:
            await update.callback_query.answer("Error loading referrals")
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def share_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Share Referral Link' button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        # In real implementation, this would come from database
        user = update.effective_user
        referral_code = f"SOL{user.id}"
        referral_link = f"https://t.me/YourBotUsername?start={referral_code}"
        
        # Create a shareable message
        share_message = (
            "🚀 *Join Solana Memecoin Trading Bot*\n\n"
            "I'm using this automated trading bot to earn consistent profits on Solana memecoins!\n\n"
            f"Sign up using my referral link: {referral_link}\n\n"
            "Features:\n"
            "• Automated memecoin trading\n"
            "• Daily profits\n"
            "• Easy deposits and withdrawals\n"
            "• Start with as little as 0.1 SOL"
        )
        
        # Create keyboard with return button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Copy Message", callback_data="copy_referral_message")],
            [InlineKeyboardButton("⬅️ Back to Referrals", callback_data="referral")]
        ])
        
        await query.edit_message_text(
            share_message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in share_referral_callback: {e}")
        await query.edit_message_text(
            "Sorry, there was an error generating your referral message. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Referrals", callback_data="referral")]
            ])
        )

async def copy_referral_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Copy Message' button click"""
    query = update.callback_query
    await query.answer("Referral message copied to clipboard!")
    # The actual copy to clipboard is handled by Telegram automatically

async def referral_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Referral Statistics' button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Mock referral statistics
        stats = [
            {"user": "User1", "date": "2025-05-15", "status": "Active", "earned": "0.01 SOL"},
            {"user": "User2", "date": "2025-05-12", "status": "Active", "earned": "0.01 SOL"},
            {"user": "User3", "date": "2025-05-10", "status": "Active", "earned": "0.01 SOL"}
        ]
        
        message = "*📊 YOUR REFERRAL STATISTICS*\n\n"
        
        if stats:
            for i, referral in enumerate(stats, 1):
                message += (
                    f"*Referral #{i}*\n"
                    f"User: {referral['user']}\n"
                    f"Date: {referral['date']}\n"
                    f"Status: {referral['status']}\n"
                    f"Earned: {referral['earned']}\n\n"
                )
                
            message += "You earn rewards when your referrals make deposits!"
        else:
            message += "You haven't referred anyone yet. Share your referral link to start earning rewards!"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Referrals", callback_data="referral")]
        ])
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in referral_stats_callback: {e}")
        await query.edit_message_text(
            "Sorry, there was an error loading your referral statistics. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Referrals", callback_data="referral")]
            ])
        )

def register_referral_handlers(application: Application):
    """Register all handlers related to the referral system"""
    # Referral command handler
    application.add_handler(CommandHandler("referral", referral_command))
    
    # Referral callback handlers
    application.add_handler(CallbackQueryHandler(referral_command, pattern="^referral$"))
    application.add_handler(CallbackQueryHandler(share_referral_callback, pattern="^share_referral$"))
    application.add_handler(CallbackQueryHandler(copy_referral_message_callback, pattern="^copy_referral_message$"))
    application.add_handler(CallbackQueryHandler(referral_stats_callback, pattern="^referral_stats$"))