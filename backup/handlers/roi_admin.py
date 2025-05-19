import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.exc import SQLAlchemyError
from app import db, app
from models import User, CycleStatus, TradingCycle
from utils.roi_system import admin_start_new_cycle, admin_adjust_roi, admin_pause_cycle, admin_resume_cycle

logger = logging.getLogger(__name__)

# Define conversation states
WAITING_FOR_ROI_PERCENTAGE = 1

async def admin_start_roi_cycle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a new 7-Day 2x ROI cycle for a user"""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('admin_target_user_id')
    if not user_id:
        await query.edit_message_text("Error: User data not found. Please restart from the admin panel.")
        return
    
    with app.app_context():
        try:
            # Get user details
            user = User.query.get(user_id)
            if not user:
                await query.edit_message_text("Error: User not found in database.")
                return
            
            # Check if user has sufficient balance
            if user.balance <= 0:
                await query.edit_message_text(
                    f"Error: User has insufficient balance ({user.balance:.2f} SOL). " 
                    f"A positive balance is required to start a ROI cycle."
                )
                return
            
            # Start a new cycle
            success = admin_start_new_cycle(user_id)
            
            if success:
                # Get the new cycle
                cycle = TradingCycle.query.filter_by(user_id=user_id, status=CycleStatus.IN_PROGRESS).first()
                
                success_message = (
                    f"✅ New 7-Day 2x ROI cycle started for user {user.username or user.telegram_id}\n\n"
                    f"Initial Balance: {cycle.initial_balance:.2f} SOL\n"
                    f"Target Balance: {cycle.target_balance:.2f} SOL\n"
                    f"Daily ROI: {cycle.daily_roi_percentage:.2f}%\n"
                    f"Start Date: {cycle.start_date.strftime('%Y-%m-%d')}\n\n"
                    f"The user will now earn {cycle.daily_roi_percentage:.2f}% daily, " 
                    f"targeting a 2x return in 7 days."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Return to User Management", callback_data="admin_user_management")],
                    [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=success_message,
                    reply_markup=reply_markup
                )
            else:
                error_message = (
                    f"❌ Failed to start ROI cycle for user {user.username or user.telegram_id}.\n"
                    f"This could be due to an existing active cycle or database error."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Back", callback_data="admin_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=error_message,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error starting ROI cycle: {e}")
            await query.edit_message_text(f"Error starting ROI cycle: {str(e)}")

async def admin_pause_roi_cycle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pause an active 7-Day 2x ROI cycle"""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('admin_target_user_id')
    if not user_id:
        await query.edit_message_text("Error: User data not found. Please restart from the admin panel.")
        return
    
    with app.app_context():
        try:
            # Pause the cycle
            success = admin_pause_cycle(user_id)
            
            # Get user details
            user = User.query.get(user_id)
            username = user.username or user.telegram_id if user else user_id
            
            if success:
                success_message = (
                    f"⏸️ ROI cycle paused for user {username}\n\n"
                    "The cycle has been paused and daily profits will not be calculated until resumed."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Return to User Management", callback_data="admin_user_management")],
                    [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=success_message,
                    reply_markup=reply_markup
                )
            else:
                error_message = (
                    f"❌ Failed to pause ROI cycle for user {username}.\n"
                    f"The user might not have an active cycle or there might be a database error."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Back", callback_data="admin_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=error_message,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error pausing ROI cycle: {e}")
            await query.edit_message_text(f"Error pausing ROI cycle: {str(e)}")

async def admin_resume_roi_cycle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resume a paused 7-Day 2x ROI cycle"""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('admin_target_user_id')
    if not user_id:
        await query.edit_message_text("Error: User data not found. Please restart from the admin panel.")
        return
    
    with app.app_context():
        try:
            # Resume the cycle
            success = admin_resume_cycle(user_id)
            
            # Get user details
            user = User.query.get(user_id)
            username = user.username or user.telegram_id if user else user_id
            
            if success:
                success_message = (
                    f"▶️ ROI cycle resumed for user {username}\n\n"
                    "The cycle has been resumed and daily profits will now be calculated."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Return to User Management", callback_data="admin_user_management")],
                    [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=success_message,
                    reply_markup=reply_markup
                )
            else:
                error_message = (
                    f"❌ Failed to resume ROI cycle for user {username}.\n"
                    f"The user might not have a paused cycle or there might be a database error."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Back", callback_data="admin_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=error_message,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error resuming ROI cycle: {e}")
            await query.edit_message_text(f"Error resuming ROI cycle: {str(e)}")

async def admin_adjust_roi_percentage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Adjust the daily ROI percentage for a user's active cycle"""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('admin_target_user_id')
    if not user_id:
        await query.edit_message_text("Error: User data not found. Please restart from the admin panel.")
        return ConversationHandler.END
    
    with app.app_context():
        try:
            # Get user and cycle details
            user = User.query.get(user_id)
            if not user:
                await query.edit_message_text("Error: User not found in database.")
                return ConversationHandler.END
                
            cycle = TradingCycle.query.filter_by(user_id=user_id, status=CycleStatus.IN_PROGRESS).first()
            if not cycle:
                await query.edit_message_text(
                    f"Error: User {user.username or user.telegram_id} doesn't have an active ROI cycle."
                )
                return ConversationHandler.END
            
            message = (
                f"Current daily ROI percentage for {user.username or user.telegram_id}: {cycle.daily_roi_percentage:.2f}%\n\n"
                "Please enter a new daily ROI percentage (e.g., 25.0 for 25%):"
            )
            
            await query.edit_message_text(text=message)
            
            # Store user_id for later use
            context.user_data['roi_adjustment_user_id'] = user_id
            
            return WAITING_FOR_ROI_PERCENTAGE
                
        except Exception as e:
            logger.error(f"Error in ROI percentage adjustment: {e}")
            await query.edit_message_text(f"Error in ROI percentage adjustment: {str(e)}")
            return ConversationHandler.END

async def admin_process_roi_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the entered ROI percentage"""
    try:
        # Get new percentage from message
        new_percentage = float(update.message.text.strip())
        
        # Validate percentage range
        if new_percentage <= 0 or new_percentage > 100:
            await update.message.reply_text(
                "Invalid percentage. Please enter a value between 0 and 100."
            )
            return WAITING_FOR_ROI_PERCENTAGE
        
        # Get user_id from context
        user_id = context.user_data.get('roi_adjustment_user_id')
        if not user_id:
            await update.message.reply_text("Error: User data not found. Please restart from the admin panel.")
            return ConversationHandler.END
        
        with app.app_context():
            # Adjust ROI percentage
            success = admin_adjust_roi(user_id, new_percentage)
            
            # Get user details
            user = User.query.get(user_id)
            username = user.username or user.telegram_id if user else user_id
            
            if success:
                success_message = (
                    f"✅ Daily ROI percentage updated for user {username}\n\n"
                    f"New Daily ROI: {new_percentage:.2f}%\n\n"
                    "This change will apply to all future daily profit calculations."
                )
                
                keyboard = [
                    [InlineKeyboardButton("Return to User Management", callback_data="admin_user_management")],
                    [InlineKeyboardButton("Back to Admin Panel", callback_data="admin_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    text=success_message,
                    reply_markup=reply_markup
                )
            else:
                error_message = (
                    f"❌ Failed to update ROI percentage for user {username}.\n"
                    f"The user might not have an active cycle or there might be a database error."
                )
                
                await update.message.reply_text(text=error_message)
            
            return ConversationHandler.END
                
    except ValueError:
        await update.message.reply_text(
            "Invalid input. Please enter a numeric value for the ROI percentage."
        )
        return WAITING_FOR_ROI_PERCENTAGE
        
    except Exception as e:
        logger.error(f"Error processing ROI percentage: {e}")
        await update.message.reply_text(f"Error processing ROI percentage: {str(e)}")
        return ConversationHandler.END

# Note: Conversation handler is created in bot_polling_runner.py instead
