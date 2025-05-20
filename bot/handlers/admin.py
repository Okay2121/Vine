"""
Admin handler module
Provides administration functionality for bot owners
"""

import logging
import threading
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Import admin-related services
from services.trading_engine import get_system_stats
from utils.config import ADMIN_USER_ID

# Constants for conversation states
WAITING_FOR_USER_ID = 1
WAITING_FOR_AMOUNT = 2
WAITING_FOR_REASON = 3
WAITING_FOR_MESSAGE = 4
WAITING_FOR_ANNOUNCEMENT = 5

logger = logging.getLogger(__name__)

# Global variables for admin operations
admin_target_user_id = None
admin_adjustment_amount = None
admin_adjustment_reason = None

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /admin command - entry point for admin panel"""
    user = update.effective_user
    
    # Check if user is authorized
    if str(user.id) != str(ADMIN_USER_ID):
        await update.message.reply_text("⚠️ You are not authorized to access the admin panel.")
        logger.warning(f"Unauthorized admin access attempt by user {user.id}")
        return
    
    # Create admin panel menu
    message = (
        "🛠️ *ADMIN CONTROL PANEL*\n\n"
        "Select an admin function from the options below:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 User Management", callback_data="admin_user_management")],
        [InlineKeyboardButton("📣 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📩 Direct Message", callback_data="admin_direct_message")],
        [InlineKeyboardButton("📊 View Stats", callback_data="admin_view_stats")],
        [InlineKeyboardButton("💰 Adjust Balance", callback_data="admin_adjust_balance")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_bot_settings")]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def admin_user_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'User Management' button click"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "👤 *USER MANAGEMENT*\n\n"
        "Select a user management function:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find User", callback_data="admin_find_user")],
        [InlineKeyboardButton("📊 User Stats", callback_data="admin_user_stats")],
        [InlineKeyboardButton("❌ Remove User", callback_data="admin_remove_user")],
        [InlineKeyboardButton("🔄 Reset User", callback_data="admin_reset_user")],
        [InlineKeyboardButton("📋 Export Users (CSV)", callback_data="admin_export_csv")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Broadcast Message' button click"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "📣 *BROADCAST MESSAGE*\n\n"
        "Send a message to multiple users at once.\n"
        "Select your target audience:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Announcement to All", callback_data="admin_broadcast_announcement")],
        [InlineKeyboardButton("🟢 Active Users Only", callback_data="admin_broadcast_active")],
        [InlineKeyboardButton("👥 All Users", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def admin_adjust_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Adjust Balance' button click"""
    query = update.callback_query
    await query.answer()
    
    # Reset global variables for a new balance adjustment
    global admin_target_user_id, admin_adjustment_amount, admin_adjustment_reason
    admin_target_user_id = None
    admin_adjustment_amount = None
    admin_adjustment_reason = None
    
    message = (
        "💰 *ADJUST USER BALANCE*\n\n"
        "Enter the Telegram username or ID of the user\n"
        "whose balance you want to adjust:"
    )
    
    # Store that we're waiting for a user ID
    context.user_data['admin_state'] = WAITING_FOR_USER_ID
    
    # Set up listener for next message
    context.bot_data['admin_listener'] = {
        'chat_id': query.message.chat_id,
        'handler': 'admin_balance_user_handler'
    }
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def admin_balance_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the user ID/username for balance adjustment"""
    # Get the user ID or username
    user_input = update.message.text.strip()
    
    try:
        # In a real implementation, this would check the database
        # Mock check for demonstration
        user_exists = True  # Assume user exists
        
        if user_exists:
            # Set the target user ID globally
            global admin_target_user_id
            admin_target_user_id = 123456  # Mock user ID
            
            # Mock user details
            username = "example_user"
            current_balance = 1.5  # SOL
            
            message = (
                f"👤 User: @{username}\n"
                f"💰 Current Balance: {current_balance:.4f} SOL\n\n"
                f"Enter the amount to adjust (positive to add, negative to deduct):\n"
                f"Example: 0.5 or -0.5"
            )
            
            # Update state
            context.user_data['admin_state'] = WAITING_FOR_AMOUNT
            
            # Update listener
            context.bot_data['admin_listener']['handler'] = 'admin_balance_amount_handler'
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]
            ])
            
            await update.message.reply_text(message, reply_markup=keyboard)
        else:
            await update.message.reply_text(
                "❌ User not found. Please check the ID/username and try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_back")]
                ])
            )
    except Exception as e:
        logger.error(f"Error in admin_balance_user_handler: {e}")
        await update.message.reply_text(
            f"Error processing user lookup: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_back")]
            ])
        )

async def admin_balance_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the adjustment amount"""
    try:
        # Parse the amount
        amount_text = update.message.text.strip()
        amount = float(amount_text)
        
        # Set the adjustment amount globally
        global admin_adjustment_amount
        admin_adjustment_amount = amount
        
        message = (
            f"Adjustment amount: {'➕' if amount > 0 else '➖'} {abs(amount):.4f} SOL\n\n"
            f"Please enter a reason for this adjustment\n"
            f"(for audit and tracking purposes):"
        )
        
        # Update state
        context.user_data['admin_state'] = WAITING_FOR_REASON
        
        # Update listener
        context.bot_data['admin_listener']['handler'] = 'admin_balance_reason_handler'
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]
        ])
        
        await update.message.reply_text(message, reply_markup=keyboard)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount format. Please enter a valid number.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_back")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in admin_balance_amount_handler: {e}")
        await update.message.reply_text(
            f"Error processing amount: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_back")]
            ])
        )

async def admin_balance_reason_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the adjustment reason"""
    # Get the reason
    reason = update.message.text.strip()
    
    # Set the adjustment reason globally
    global admin_adjustment_reason
    admin_adjustment_reason = reason
    
    try:
        # Mock user details for confirmation
        username = "example_user"
        
        # Create confirmation message
        action = "add to" if admin_adjustment_amount > 0 else "deduct from"
        confirmation_message = (
            "📝 *BALANCE ADJUSTMENT CONFIRMATION*\n\n"
            f"User: @{username}\n"
            f"Action: {action} balance\n"
            f"Amount: {abs(admin_adjustment_amount):.4f} SOL\n"
            f"Reason: {admin_adjustment_reason}\n\n"
            "Please confirm this adjustment:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data="admin_confirm_adjustment"),
                InlineKeyboardButton("❌ Cancel", callback_data="admin_back")
            ]
        ])
        
        await update.message.reply_text(confirmation_message, reply_markup=keyboard, parse_mode="Markdown")
        
        # Remove current listener as we're using callback for confirmation
        if 'admin_listener' in context.bot_data:
            del context.bot_data['admin_listener']
            
    except Exception as e:
        logger.error(f"Error in admin_balance_reason_handler: {e}")
        await update.message.reply_text(
            f"Error processing reason: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_back")]
            ])
        )

async def admin_confirm_adjustment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the confirmation of balance adjustment - non-blocking implementation"""
    query = update.callback_query
    await query.answer()
    
    # Send immediate acknowledgment to prevent UI freeze
    await query.edit_message_text(
        "✅ Processing your balance adjustment request...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Return to Admin Panel", callback_data="admin_back")]
        ])
    )
    
    # Get all values before resetting globals
    global admin_target_user_id, admin_adjustment_amount, admin_adjustment_reason
    user_id = admin_target_user_id
    amount = admin_adjustment_amount
    reason = admin_adjustment_reason or "Admin adjustment"
    
    # Reset globals immediately to prevent issues
    admin_target_user_id = None
    admin_adjustment_amount = None
    admin_adjustment_reason = None
    
    # Process the adjustment in a background thread to prevent bot freezing
    def process_adjustment_in_background():
        try:
            # In real implementation, this would update the database
            # and use the balance_manager module
            logger.info(f"Processing balance adjustment for user {user_id}: {amount} SOL")
            
            # Simulate database update
            success = True
            
            # Send result message to admin
            if success:
                action = "added to" if amount > 0 else "deducted from"
                asyncio.run(context.bot.send_message(
                    query.message.chat_id,
                    f"✅ Successfully {action} balance: {abs(amount):.4f} SOL",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Return to Admin Panel", callback_data="admin_back")]
                    ])
                ))
            else:
                asyncio.run(context.bot.send_message(
                    query.message.chat_id,
                    "❌ Balance adjustment failed. Please try again.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Return to Admin Panel", callback_data="admin_back")]
                    ])
                ))
        except Exception as e:
            logger.error(f"Error in balance adjustment background thread: {e}")
            # Notify admin of error
            try:
                asyncio.run(context.bot.send_message(
                    query.message.chat_id,
                    f"❌ Error during balance adjustment: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Return to Admin Panel", callback_data="admin_back")]
                    ])
                ))
            except:
                logger.error("Failed to send error notification to admin")
    
    # Start background thread
    threading.Thread(target=process_adjustment_in_background).start()

async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Back' button click - return to main admin panel"""
    query = update.callback_query
    await query.answer()
    
    # Clear any admin operation state
    if 'admin_state' in context.user_data:
        del context.user_data['admin_state']
    
    # Clear any active listeners
    if 'admin_listener' in context.bot_data:
        del context.bot_data['admin_listener']
    
    # Return to main admin panel
    await admin_command(update, context)

async def admin_view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'View Stats' button click"""
    query = update.callback_query
    await query.answer()
    
    # In real implementation, these would be fetched from the database
    # Mock statistics for demonstration
    total_users = 152
    active_users = 87
    total_deposits = 253.45  # SOL
    total_withdrawals = 78.32  # SOL
    total_profit = 42.67  # SOL
    
    message = (
        "📊 *SYSTEM STATISTICS*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🟢 Active Users: {active_users}\n"
        f"📥 Total Deposits: {total_deposits:.2f} SOL\n"
        f"📤 Total Withdrawals: {total_withdrawals:.2f} SOL\n"
        f"💰 Total Profit Generated: {total_profit:.2f} SOL\n\n"
        f"System Status: ✅ Operational"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 ROI Stats", callback_data="admin_roi_stats")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_view_stats")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

def register_admin_handlers(application: Application):
    """Register all handlers related to admin functionality"""
    # Admin command handler
    application.add_handler(CommandHandler("admin", admin_command))
    
    # Admin callback handlers
    application.add_handler(CallbackQueryHandler(admin_user_management_callback, pattern="^admin_user_management$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(admin_adjust_balance_callback, pattern="^admin_adjust_balance$"))
    application.add_handler(CallbackQueryHandler(admin_view_stats_callback, pattern="^admin_view_stats$"))
    application.add_handler(CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"))
    application.add_handler(CallbackQueryHandler(admin_confirm_adjustment_handler, pattern="^admin_confirm_adjustment$"))
    
    # Set up a message handler for admin operations that require text input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_message_handler))

async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """General handler for admin text messages based on current state"""
    # Check if we have an active admin listener
    if 'admin_listener' not in context.bot_data:
        return
    
    # Check if this message is for the active listener
    if context.bot_data['admin_listener'].get('chat_id') != update.effective_chat.id:
        return
    
    # Get the handler function name
    handler_name = context.bot_data['admin_listener'].get('handler')
    
    if not handler_name:
        return
    
    # Map handler names to functions
    handlers = {
        'admin_balance_user_handler': admin_balance_user_handler,
        'admin_balance_amount_handler': admin_balance_amount_handler,
        'admin_balance_reason_handler': admin_balance_reason_handler,
        # Add other handlers as needed
    }
    
    # Call the appropriate handler
    if handler_name in handlers:
        await handlers[handler_name](update, context)
    else:
        logger.error(f"Unknown admin handler: {handler_name}")
        await update.message.reply_text("Error: Unknown operation.")