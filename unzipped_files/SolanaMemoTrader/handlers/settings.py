import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.exc import SQLAlchemyError
from app import db, app
from models import User, UserStatus

logger = logging.getLogger(__name__)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show settings menu."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        
        # Edit the existing message
        await show_settings(context, chat_id, message_id, user_id)
    else:
        # Handle direct command
        user_id = update.effective_user.id
        await show_settings(context, update.effective_chat.id, None, user_id)


async def show_settings(context, chat_id, message_id=None, user_id=None):
    """Show the settings menu."""
    with app.app_context():
        try:
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                # If somehow the user doesn't exist in the database
                error_text = "Please start the bot with /start first."
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
            
            # Format settings message
            settings_message = (
                "⚙️ *Settings*\n\n"
                "Configure your trading bot preferences and account settings."
            )
            
            # Create keyboard based on user status
            keyboard = []
            
            # Only show toggle trading if user is active
            if user.status == UserStatus.ACTIVE:
                keyboard.append([InlineKeyboardButton("Toggle Trading (Currently ON)", callback_data="toggle_trading")])
            elif user.status == UserStatus.INACTIVE:
                keyboard.append([InlineKeyboardButton("Toggle Trading (Currently OFF)", callback_data="toggle_trading")])
            
            keyboard.extend([
                [InlineKeyboardButton("Notification Settings", callback_data="notification_settings")],
                [InlineKeyboardButton("Account Information", callback_data="account_info")],
                [InlineKeyboardButton("Help & Support", callback_data="how_it_works")],
                [InlineKeyboardButton("Back to Dashboard", callback_data="view_dashboard")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Either edit existing message or send new one
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=settings_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=settings_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except SQLAlchemyError as e:
            logger.error(f"Database error during settings display: {e}")
            db.session.rollback()
            
            error_text = "Sorry, there was an error retrieving your settings. Please try again later."
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
