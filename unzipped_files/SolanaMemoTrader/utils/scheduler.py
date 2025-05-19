import logging
from datetime import time, datetime
from telegram.ext import CallbackContext
from utils.notifications import send_daily_update, send_inactivity_reminder
from utils.trading import execute_daily_trading
from utils.roi_system import process_daily_roi, create_or_get_active_cycle
from utils.engagement import schedule_engagement_messages
from models import User, UserStatus
from app import app, db
from helpers import get_notification_time, are_daily_updates_enabled

logger = logging.getLogger(__name__)

def setup_schedulers(application):
    """
    Set up scheduled jobs for the bot.
    
    Args:
        application: The telegram.ext.Application object
    """
    # Check if job_queue is available
    if not hasattr(application, 'job_queue') or application.job_queue is None:
        logger.warning("Job queue is not available. Scheduled jobs will not be set up.")
        return
        
    try:
        # Get dynamic settings for notification hour
        notification_hour = get_notification_time()
        daily_updates_enabled = are_daily_updates_enabled()
        
        # Only schedule if daily updates are enabled
        if daily_updates_enabled:
            # Schedule daily trading simulation (1 hour before notification)
            application.job_queue.run_daily(
                run_daily_trading_simulation,
                time=time(hour=max(0, notification_hour-1), minute=0),  # Run 1 hour before the daily update
                name="daily_trading_simulation"
            )
            
            # Schedule daily update notifications
            application.job_queue.run_daily(
                lambda context: send_daily_update(context),
                time=time(hour=notification_hour, minute=0),
                name="daily_update_notifications"
            )
            
            logger.info(f"Scheduled daily trading at {max(0, notification_hour-1)}:00 UTC and notifications at {notification_hour}:00 UTC")
        else:
            logger.info("Daily updates are disabled - not scheduling trading simulations or notifications")
        
        # Schedule inactivity reminders (run every day at 3:00 PM UTC)
        application.job_queue.run_daily(
            lambda context: send_inactivity_reminder(context),
            time=time(hour=15, minute=0),
            name="inactivity_reminders"
        )
        
        # Schedule engagement messages (run every day at 12:00 PM UTC)
        application.job_queue.run_daily(
            lambda context: schedule_engagement_messages(context),
            time=time(hour=12, minute=0),
            name="engagement_messages"
        )
        
        logger.info("Scheduled jobs set up successfully")
    except Exception as e:
        logger.error(f"Error setting up scheduled jobs: {e}")


async def run_daily_trading_simulation(context: CallbackContext):
    """
    Run real-time trading and 7-Day 2x ROI processing for all active users.
    
    Args:
        context: The telegram.ext.CallbackContext object
    """
    logger.info("Starting daily real-time trading processing")
    
    with app.app_context():
        # Get all active users
        active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
        logger.info(f"Found {len(active_users)} active users for trading")
        
        for user in active_users:
            logger.info(f"Processing trading for user {user.id}")
            
            # First, ensure the user has an active 7-Day 2x ROI cycle
            cycle = create_or_get_active_cycle(user.id)
            
            # Process the daily ROI for the 7-Day 2x ROI system
            if cycle:
                profit_amount, profit_percentage = process_daily_roi(user.id)
                logger.info(f"User {user.id} 7-Day 2x ROI: {profit_amount:.2f} SOL ({profit_percentage:.2f}%)")
            else:
                # Fall back to standard trading if no cycle is active
                profit_amount, profit_percentage = execute_daily_trading(user.id)
                logger.info(f"User {user.id} standard trading: {profit_amount:.2f} SOL ({profit_percentage:.2f}%)")
            
            logger.info(f"User {user.id} daily profit: {profit_amount:.2f} SOL ({profit_percentage:.2f}%)")
            
            # Check if we need to start a new cycle
            if not cycle:
                # Create a new cycle for future processing
                create_or_get_active_cycle(user.id)


def get_next_run_times(application):
    """
    Get the next run times for all scheduled jobs.
    Useful for debugging and testing.
    
    Args:
        application: The telegram.ext.Application object
        
    Returns:
        dict: Job names and their next run times
    """
    next_runs = {}
    
    if not hasattr(application, 'job_queue') or application.job_queue is None:
        logger.warning("Job queue is not available. Cannot get next run times.")
        return next_runs
    
    try:
        for job in application.job_queue.jobs():
            next_runs[job.name] = job.next_t.strftime("%Y-%m-%d %H:%M:%S UTC") if job.next_t else "Not scheduled"
    except Exception as e:
        logger.error(f"Error getting next run times: {e}")
    
    return next_runs
