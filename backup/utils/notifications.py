import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from app import db, app
from models import User, Profit, MilestoneTracker, UserStatus
from config import PROFIT_MILESTONES, STREAK_MILESTONES, INACTIVITY_THRESHOLD

def generate_progress_bar(percentage, length=10):
    """
    Generate a text-based progress bar.
    
    Args:
        percentage (float): The percentage of completion (0-100)
        length (int): The length of the progress bar in characters
        
    Returns:
        str: A text progress bar like [■■■■□□□□□□]
    """
    filled_length = int(length * percentage / 100)
    empty_length = length - filled_length
    bar = '■' * filled_length + '□' * empty_length
    return f'[{bar}]'

logger = logging.getLogger(__name__)

async def send_daily_update(context):
    """
    Send daily profit updates to all active users.
    
    Args:
        context: The telegram.ext.CallbackContext object
    """
    with current_app.app_context():
        try:
            # Get all active users
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            
            for user in active_users:
                # Get yesterday's profit (assuming this runs at the start of a new day)
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                yesterday_profit = Profit.query.filter_by(user_id=user.id, date=yesterday).first()
                
                if not yesterday_profit:
                    logger.warning(f"No profit data for user {user.id} on {yesterday}")
                    continue
                
                # Calculate current streak and days of operation
                streak = calculate_profit_streak(user.id)
                days_active = (datetime.utcnow().date() - user.joined_at.date()).days
                
                # Calculate monthly goal and progress
                monthly_goal = 30  # 30% monthly goal
                total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
                total_profit_percentage = (total_profit_amount / user.initial_deposit) * 100 if user.initial_deposit > 0 else 0
                progress_percent = min(100, (total_profit_percentage / monthly_goal) * 100)
                progress_bar = generate_progress_bar(progress_percent)
                
                # Generate message based on profit/loss
                if yesterday_profit.amount > 0:
                    # Profit day
                    emoji = "📈"
                    
                    # Create streak message with positive reinforcement
                    if streak >= 5:
                        streak_text = f"🔥 {streak}-day profit streak! Your consistency is paying off!"
                    elif streak >= 3:
                        streak_text = f"🔥 {streak}-day profit streak! You're on a roll!"
                    else:
                        streak_text = "💪 Every profitable day compounds your success!"
                    
                    # Calculate progress change
                    previous_progress = progress_percent - (yesterday_profit.percentage / monthly_goal * 100)
                    progress_change = "↗️" if progress_percent > previous_progress else "➡️"
                    
                    message = (
                        f"{emoji} *THRIVE DAILY PROFIT UPDATE* {emoji}\n\n"
                        f"*Today's profit:* +{yesterday_profit.amount:.2f} SOL (+{yesterday_profit.percentage:.1f}%)\n"
                        f"*Day:* {days_active} of operations\n"
                        f"*Updated balance:* {user.balance:.2f} SOL\n\n"
                        f"*Monthly Goal Progress:* {progress_change}\n"
                        f"{progress_bar} {progress_percent:.0f}%\n\n"
                        f"{streak_text}"
                    )
                else:
                    # Loss day - use encouraging language
                    # Calculate days since last loss for personalized message
                    loss_days = db.session.query(Profit).filter(Profit.user_id == user.id, Profit.amount < 0).count()
                    total_days = db.session.query(Profit).filter(Profit.user_id == user.id).count()
                    loss_ratio = (loss_days / total_days) if total_days > 0 else 0
                    
                    # Get historical performance for context
                    profitable_days = db.session.query(Profit).filter(Profit.user_id == user.id, Profit.amount > 0).count()
                    win_rate = (profitable_days / total_days * 100) if total_days > 0 else 0
                    
                    # Different approaches based on win rate
                    if win_rate > 80:
                        motivation = "Even the best trading strategies have down days. Your win rate of {:.1f}% is exceptional! 🏆".format(win_rate)
                    elif win_rate > 60:
                        motivation = "With a solid win rate of {:.1f}%, occasional down days are part of the journey to success! 💪".format(win_rate)
                    else:
                        motivation = "Market volatility creates opportunities. Our strategy is designed for long-term growth through ups and downs."
                    
                    # Calculate recovery estimate based on average daily profit
                    avg_profit = db.session.query(func.avg(Profit.amount)).filter(
                        Profit.user_id == user.id, 
                        Profit.amount > 0
                    ).scalar() or 0
                    
                    # Loss recovery estimate
                    if avg_profit > 0:
                        recovery_days = abs(yesterday_profit.amount) / avg_profit
                        recovery_message = f"Based on your average profit, this may be recovered in approximately {recovery_days:.1f} trading days."
                    else:
                        recovery_message = "Keep monitoring your dashboard for the next profitable trading cycle."
                    
                    message = (
                        f"📊 *THRIVE DAILY UPDATE* 📊\n\n"
                        f"*Today's result:* {yesterday_profit.amount:.2f} SOL ({yesterday_profit.percentage:.1f}%)\n"
                        f"*Day:* {days_active} of operations\n"
                        f"*Updated balance:* {user.balance:.2f} SOL\n\n"
                        f"*Performance Metrics:*\n"
                        f"• Win Rate: {win_rate:.1f}%\n"
                        f"• Monthly Goal: {progress_bar} {progress_percent:.0f}%\n\n"
                        f"*{motivation}*\n\n"
                        f"{recovery_message}\n\n"
                        f"Remember: Consistent trading with a proven strategy leads to long-term success! 📈"
                    )
                
                # Create keyboard with motivating action buttons
                keyboard = [
                    [InlineKeyboardButton("📊 View Dashboard", callback_data="view_dashboard")],
                    [InlineKeyboardButton("📈 Performance", callback_data="trading_history")],
                    [InlineKeyboardButton("💰 Deposit More", callback_data="deposit")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send message
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                    logger.info(f"Sent daily update to user {user.id}")
                except Exception as e:
                    logger.error(f"Failed to send daily update to user {user.id}: {e}")
                
                # Check for streaks and milestones
                await check_milestones(context, user.id)
                
        except SQLAlchemyError as e:
            logger.error(f"Database error during daily updates: {e}")
            db.session.rollback()


async def check_milestones(context, user_id):
    """
    Check for profit milestones and streak milestones.
    
    Args:
        context: The telegram.ext.CallbackContext object
        user_id (int): The database ID of the user
    """
    with current_app.app_context():
        try:
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found for milestone check")
                return
            
            # Calculate total profit percentage
            total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user_id).scalar() or 0
            total_profit_percentage = (total_profit_amount / user.initial_deposit) * 100 if user.initial_deposit > 0 else 0
            
            # Check profit milestones
            for milestone in PROFIT_MILESTONES:
                if total_profit_percentage >= milestone:
                    # Check if this milestone has already been recorded
                    existing_milestone = MilestoneTracker.query.filter_by(
                        user_id=user_id,
                        milestone_type='profit_percentage',
                        value=milestone
                    ).first()
                    
                    if not existing_milestone:
                        # New milestone achieved
                        new_milestone = MilestoneTracker()
                        new_milestone.user_id = user_id
                        new_milestone.milestone_type = 'profit_percentage'
                        new_milestone.value = milestone
                        db.session.add(new_milestone)
                        db.session.commit()
                        
                        # Send milestone notification
                        await send_profit_milestone_notification(context, user, milestone, total_profit_amount)
            
            # Check streak milestones
            streak = calculate_profit_streak(user_id)
            for milestone in STREAK_MILESTONES:
                if streak >= milestone:
                    # Check if this milestone has already been recorded
                    existing_milestone = MilestoneTracker.query.filter_by(
                        user_id=user_id,
                        milestone_type='streak',
                        value=milestone
                    ).first()
                    
                    if not existing_milestone:
                        # New milestone achieved
                        new_milestone = MilestoneTracker()
                        new_milestone.user_id = user_id
                        new_milestone.milestone_type = 'streak'
                        new_milestone.value = milestone
                        db.session.add(new_milestone)
                        db.session.commit()
                        
                        # Send milestone notification
                        await send_streak_milestone_notification(context, user, milestone)
                        
        except SQLAlchemyError as e:
            logger.error(f"Database error during milestone check: {e}")
            db.session.rollback()


async def send_profit_milestone_notification(context, user, milestone, total_profit):
    """
    Send a notification for a profit milestone.
    
    Args:
        context: The telegram.ext.CallbackContext object
        user (User): The user object
        milestone (int): The milestone percentage
        total_profit (float): The total profit amount
    """
    try:
        # Calculate time since joining
        days_active = (datetime.utcnow().date() - user.joined_at.date()).days or 1  # Avoid division by zero
        
        # Calculate projected ROI metrics
        daily_avg_roi = milestone / days_active
        monthly_projected_roi = daily_avg_roi * 30
        yearly_projected_roi = monthly_projected_roi * 12
        
        # Calculate what this would mean with a larger investment
        potential_profit_2x = (user.initial_deposit * 2) * (milestone / 100)
        potential_profit_5x = (user.initial_deposit * 5) * (milestone / 100)
        
        # Calculate compound growth over time
        compound_3months = user.balance * (1 + (daily_avg_roi/100)) ** 90
        compound_6months = user.balance * (1 + (daily_avg_roi/100)) ** 180
        compound_1year = user.balance * (1 + (daily_avg_roi/100)) ** 365
        
        # Generate progress bar for milestone
        next_milestone = None
        for m in sorted(PROFIT_MILESTONES):
            if m > milestone:
                next_milestone = m
                break
                
        progress_to_next = 0
        if next_milestone:
            progress_to_next = (milestone / next_milestone) * 100
            progress_bar = generate_progress_bar(progress_to_next, length=10)
            days_to_next = int((next_milestone - milestone) / daily_avg_roi) if daily_avg_roi > 0 else 0
            progress_text = (
                f"*Progress to next milestone ({next_milestone}%):*\n"
                f"{progress_bar} {progress_to_next:.0f}%\n"
                f"Estimated to reach in ~{days_to_next} days at current rate"
            )
        else:
            progress_text = "*You've reached the highest milestone!* 🏆\nYour trading performance is exceptional."
        
        # Select appropriate title based on milestone level
        if milestone >= 100:
            achievement_title = "🏆 PHENOMENAL ACHIEVEMENT: {milestone}% PROFIT! 🏆"
            achievement_message = "You've DOUBLED your investment! This is what truly successful automated trading looks like."
        elif milestone >= 50:
            achievement_title = "🔥 MAJOR MILESTONE: {milestone}% PROFIT! 🔥"
            achievement_message = "You've earned more than HALF your initial investment back as pure profit!"
        elif milestone >= 25:
            achievement_title = "⭐ IMPRESSIVE MILESTONE: {milestone}% PROFIT! ⭐"
            achievement_message = "A QUARTER of your initial investment earned back as profit - your strategy is showing strong results!"
        else:
            achievement_title = "🎯 MILESTONE ACHIEVED: {milestone}% PROFIT! 🎯"
            achievement_message = "You've reached your first major profit milestone - a great indicator of trading success!"
        
        # Format the milestone notification with all required information
        message = (
            f"*{achievement_title.format(milestone=milestone)}*\n\n"
            f"{achievement_message}\n\n"
            f"*Milestone Stats:*\n"
            f"• Total Profit Earned: +{total_profit:.2f} SOL\n"
            f"• ROI Achieved: +{milestone}%\n"
            f"• Days to reach: {days_active}\n"
            f"• Current Balance: {user.balance:.2f} SOL\n\n"
            f"*Future Projections:*\n"
            f"• Monthly ROI: +{monthly_projected_roi:.1f}%\n"
            f"• Yearly ROI: +{yearly_projected_roi:.1f}%\n\n"
            f"*Compound Growth Potential:*\n"
            f"• 3 Months: {compound_3months:.2f} SOL\n"
            f"• 6 Months: {compound_6months:.2f} SOL\n"
            f"• 1 Year: {compound_1year:.2f} SOL\n\n"
            f"{progress_text}\n\n"
            f"*Scale Your Success:*\n"
            f"With 2x investment: +{potential_profit_2x:.2f} SOL at same ROI\n"
            f"With 5x investment: +{potential_profit_5x:.2f} SOL at same ROI\n\n"
            f"*The power of compounding means your gains will accelerate as your balance grows!*"
        )
        
        # Create more engaging buttons with icons
        keyboard = [
            [InlineKeyboardButton("📊 View Dashboard", callback_data="view_dashboard")],
            [InlineKeyboardButton("📢 Share Your Success", callback_data="referral")],
            [InlineKeyboardButton("💰 Compound with More SOL", callback_data="deposit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"Sent profit milestone ({milestone}%) notification to user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to send profit milestone notification to user {user.id}: {e}")


async def send_streak_milestone_notification(context, user, milestone):
    """
    Send a notification for a streak milestone.
    
    Args:
        context: The telegram.ext.CallbackContext object
        user (User): The user object
        milestone (int): The streak milestone
    """
    try:
        # Calculate total profit during streak
        today = datetime.utcnow().date()
        streak_start_date = today - timedelta(days=milestone)
        streak_profits = db.session.query(func.sum(Profit.amount)).filter(
            Profit.user_id == user.id,
            Profit.date >= streak_start_date
        ).scalar() or 0
        
        # Calculate compounding effect
        initial_balance = user.balance - streak_profits
        if initial_balance > 0:
            percentage_gain = (streak_profits / initial_balance) * 100
        else:
            percentage_gain = 0
            
        # Format appropriate celebration based on streak length
        if milestone >= 10:
            streak_title = f"🏆 LEGENDARY {milestone}-DAY PROFIT STREAK! 🏆"
            streak_description = "You've achieved something truly remarkable! This consistency is what separates professionals from amateurs."
        elif milestone >= 7:
            streak_title = f"🔥 PHENOMENAL {milestone}-DAY PROFIT STREAK! 🔥"
            streak_description = "A whole week of consecutive profits is an extraordinary achievement in trading!"
        elif milestone >= 5:
            streak_title = f"⭐ IMPRESSIVE {milestone}-DAY PROFIT STREAK! ⭐"
            streak_description = "Five days of consistent profits demonstrates your bot's powerful strategy!"
        else:
            streak_title = f"💪 SOLID {milestone}-DAY PROFIT STREAK! 💪"
            streak_description = "A consistent profit streak is building momentum for your portfolio!"
        
        message = (
            f"*{streak_title}*\n\n"
            f"{streak_description}\n\n"
            f"*Streak Stats:*\n"
            f"• Consecutive Profitable Days: {milestone}\n"
            f"• Total Profit During Streak: +{streak_profits:.2f} SOL\n"
            f"• Percentage Gain: +{percentage_gain:.1f}%\n\n"
            f"Consistency is key in trading, and your bot is showcasing exceptional performance. "
            f"Every consecutive profitable day compounds your returns and accelerates your growth!\n\n"
            f"*Keep this momentum going by adding more funds to your bot trading balance!*"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 View Dashboard", callback_data="view_dashboard")],
            [InlineKeyboardButton("📢 Share Results", callback_data="referral")],
            [InlineKeyboardButton("💰 Add More Funds", callback_data="deposit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"Sent streak milestone ({milestone} days) notification to user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to send streak milestone notification to user {user.id}: {e}")


async def send_inactivity_reminder(context):
    """
    Send reminders to users who haven't interacted with the bot for a while.
    
    Args:
        context: The telegram.ext.CallbackContext object
    """
    with current_app.app_context():
        try:
            # Calculate the inactivity threshold date (3 days as specified)
            threshold_date = datetime.utcnow() - timedelta(days=INACTIVITY_THRESHOLD)
            
            # Get inactive users who haven't viewed dashboard or deposited
            inactive_users = User.query.filter(
                User.status == UserStatus.ACTIVE,
                User.last_activity < threshold_date
            ).all()
            
            # Calculate days inactive for personalized messages
            today = datetime.utcnow().date()
            
            for user in inactive_users:
                # Calculate total earnings to date for motivation
                total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
                days_inactive = (today - user.last_activity.date()).days
                
                # Get user's activity stats
                total_trades = db.session.query(Profit).filter_by(user_id=user.id).count()
                profitable_trades = db.session.query(Profit).filter(Profit.user_id == user.id, Profit.amount > 0).count()
                win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
                
                # Format bot's current status 
                if total_profit_amount > 0:
                    status_text = f"Your bot is still earning while you're away! So far, you've earned *{total_profit_amount:.2f} SOL* in profit."
                else:
                    status_text = "Your bot is active and monitoring the markets for profitable opportunities."
                
                # Create a personalized message based on inactivity length
                if days_inactive >= 5:
                    title = "🔔 Don't miss out! Your bot is still working for you"
                    emphasis = "We miss you! Your trading bot has been continuing to operate without supervision."
                elif days_inactive >= 4:
                    title = "⏰ Quick check-in reminder"
                    emphasis = "It's been a few days since you checked your trading performance."
                else:
                    title = "👋 Just a friendly reminder"
                    emphasis = "Your THRIVE bot is earning while you sleep!"
                
                # Format the message with the required elements
                message = (
                    f"*{title}*\n\n"
                    f"{emphasis}\n\n"
                    f"{status_text}\n\n"
                    f"Win rate: {win_rate:.1f}% of trades profitable\n"
                    f"Days since last check: {days_inactive}\n\n"
                    f"Take 30 seconds to review your performance and make any adjustments to maximize your returns."
                )
                
                # Create engaging buttons with clear CTAs
                keyboard = [
                    [InlineKeyboardButton("📊 View Dashboard", callback_data="view_dashboard")],
                    [InlineKeyboardButton("📈 Performance", callback_data="trading_history")],
                    [InlineKeyboardButton("💰 Deposit More", callback_data="deposit")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Sent inactivity reminder to user {user.id}")
                except Exception as e:
                    logger.error(f"Failed to send inactivity reminder to user {user.id}: {e}")
                
        except SQLAlchemyError as e:
            logger.error(f"Database error during inactivity reminders: {e}")
            db.session.rollback()


def calculate_profit_streak(user_id):
    """
    Calculate the current profit streak for a user.
    
    Args:
        user_id (int): The database ID of the user
        
    Returns:
        int: The number of consecutive profitable days
    """
    streak = 0
    current_date = datetime.utcnow().date()
    
    while True:
        profit = Profit.query.filter_by(user_id=user_id, date=current_date).first()
        if profit and profit.amount > 0:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak
