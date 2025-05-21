import logging
import math
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from app import db, app
from models import User, Profit, Transaction, TradingCycle, CycleStatus, UserStatus

logger = logging.getLogger(__name__)

def create_or_get_active_cycle(user_id):
    """
    Get the active trading cycle for a user, or create a new one if none exists.
    
    Args:
        user_id (int): Database ID of the user
    
    Returns:
        TradingCycle: The active trading cycle, or None if error
    """
    with app.app_context():
        try:
            # Check for existing active cycle
            active_cycle = TradingCycle.query.filter_by(
                user_id=user_id, 
                status=CycleStatus.IN_PROGRESS
            ).first()
            
            if active_cycle:
                return active_cycle
                
            # Get user info
            user = User.query.get(user_id)
            if not user or user.balance <= 0:
                logger.warning(f"Cannot create cycle: User {user_id} has insufficient balance")
                return None
                
            # Create new cycle
            new_cycle = TradingCycle(
                user_id=user_id,
                start_date=datetime.utcnow(),
                initial_balance=user.balance,
                current_balance=user.balance,
                target_balance=user.balance * 2,  # 2x the initial balance
                daily_roi_percentage=28.57,  # ~28.57% per day to reach 2x in 7 days
                status=CycleStatus.IN_PROGRESS,
                is_auto_roi=True
            )
            
            db.session.add(new_cycle)
            db.session.commit()
            
            logger.info(f"Created new 7-day 2x ROI cycle for user {user_id} with initial balance {new_cycle.initial_balance}")
            return new_cycle
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating trading cycle: {e}")
            db.session.rollback()
            return None

def process_daily_roi(user_id):
    """
    Process the daily ROI for a user's active trading cycle.
    
    Args:
        user_id (int): Database ID of the user
    
    Returns:
        tuple: (profit_amount, profit_percentage)
    """
    with app.app_context():
        try:
            # Get user and active cycle
            user = User.query.get(user_id)
            if not user or user.status != UserStatus.ACTIVE:
                logger.warning(f"User {user_id} not active or not found")
                return 0, 0
                
            # Get or create cycle
            cycle = create_or_get_active_cycle(user_id)
            if not cycle:
                return 0, 0
                
            # If cycle is complete or paused, return 0
            if cycle.status != CycleStatus.IN_PROGRESS:
                return 0, 0
                
            # Calculate daily ROI based on initial balance
            # Use the cycle-specific daily ROI percentage (which can be adjusted by admin)
            daily_roi_percentage = cycle.daily_roi_percentage
            profit_percentage = daily_roi_percentage
            profit_amount = cycle.initial_balance * (profit_percentage / 100)
            
            # Update cycle current balance and total profit
            cycle.current_balance += profit_amount
            cycle.total_profit_amount += profit_amount
            cycle.total_roi_percentage += profit_percentage
            
            # Update user balance
            user.balance += profit_amount
            
            # Create a profit record for today
            today = datetime.utcnow().date()
            existing_profit = Profit.query.filter_by(user_id=user_id, date=today).first()
            
            if existing_profit:
                # Update existing profit record
                existing_profit.amount = profit_amount
                existing_profit.percentage = profit_percentage
            else:
                # Create new profit record
                new_profit = Profit(
                    user_id=user_id,
                    amount=profit_amount,
                    percentage=profit_percentage,
                    date=today
                )
                db.session.add(new_profit)
            
            # Check if cycle should be completed (reached 2x or 7 days elapsed)
            if cycle.current_balance >= cycle.target_balance or cycle.days_elapsed >= 7:
                cycle.status = CycleStatus.COMPLETED
                cycle.end_date = datetime.utcnow()
                logger.info(f"Completed 7-day 2x ROI cycle for user {user_id}: "
                           f"Initial: {cycle.initial_balance}, Final: {cycle.current_balance}")
            
            db.session.commit()
            
            logger.info(f"Processed daily ROI for user {user_id}: "
                       f"{profit_amount:.2f} SOL ({profit_percentage:.2f}%)")
            return profit_amount, profit_percentage
            
        except SQLAlchemyError as e:
            logger.error(f"Database error processing daily ROI: {e}")
            db.session.rollback()
            return 0, 0

def get_user_roi_metrics(user_id):
    """
    Get ROI metrics for a user's active trading cycle.
    
    Args:
        user_id (int): Database ID of the user
    
    Returns:
        dict: Dictionary containing ROI metrics
    """
    with app.app_context():
        try:
            # Default values
            metrics = {
                "has_active_cycle": False,
                "initial_balance": 0,
                "current_balance": 0,
                "target_balance": 0,
                "days_elapsed": 0,
                "days_remaining": 7,
                "progress_percentage": 0,
                "is_on_track": True,
                "daily_roi": 0,
                "total_roi": 0,
                "cycle_status": CycleStatus.NOT_STARTED.value
            }
            
            # Get user's active cycle
            cycle = TradingCycle.query.filter_by(
                user_id=user_id, 
                status=CycleStatus.IN_PROGRESS
            ).first()
            
            if not cycle:
                return metrics
                
            # Update metrics with actual values
            metrics.update({
                "has_active_cycle": True,
                "initial_balance": cycle.initial_balance,
                "current_balance": cycle.current_balance,
                "target_balance": cycle.target_balance,
                "days_elapsed": cycle.days_elapsed,
                "days_remaining": cycle.days_remaining,
                "progress_percentage": cycle.progress_percentage,
                "is_on_track": cycle.is_on_track,
                "daily_roi": cycle.daily_roi_percentage,
                "total_roi": cycle.total_roi_percentage,
                "cycle_status": cycle.status.value
            })
            
            return metrics
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting ROI metrics: {e}")
            return {
                "has_active_cycle": False,
                "error": "Database error"
            }

# Admin functions for managing ROI cycles

def admin_start_new_cycle(user_id, initial_balance=None, daily_roi=None):
    """
    Admin function to start a new 7-day 2x ROI cycle for a user.
    
    Args:
        user_id (int): Database ID of the user
        initial_balance (float, optional): Starting balance for the cycle
        daily_roi (float, optional): Daily ROI percentage
    
    Returns:
        bool: True if successful, False otherwise
    """
    with app.app_context():
        try:
            # Get user info
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
                
            # End any active cycles
            active_cycle = TradingCycle.query.filter_by(
                user_id=user_id, 
                status=CycleStatus.IN_PROGRESS
            ).first()
            
            if active_cycle:
                active_cycle.status = CycleStatus.COMPLETED
                active_cycle.end_date = datetime.utcnow()
            
            # Set initial balance
            if initial_balance is None:
                initial_balance = user.balance
                
            # Create new cycle
            new_cycle = TradingCycle(
                user_id=user_id,
                start_date=datetime.utcnow(),
                initial_balance=initial_balance,
                current_balance=initial_balance,
                target_balance=initial_balance * 2,  # 2x the initial balance
                daily_roi_percentage=daily_roi or 28.57,
                status=CycleStatus.IN_PROGRESS,
                is_auto_roi=daily_roi is None  # Auto ROI if daily_roi not specified
            )
            
            db.session.add(new_cycle)
            db.session.commit()
            
            logger.info(f"Admin started new 7-day 2x ROI cycle for user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error starting new cycle: {e}")
            db.session.rollback()
            return False

def admin_adjust_roi(user_id, daily_roi):
    """
    Admin function to adjust the daily ROI percentage for a user's active cycle.
    
    Args:
        user_id (int): Database ID of the user
        daily_roi (float): New daily ROI percentage
    
    Returns:
        bool: True if successful, False otherwise
    """
    with app.app_context():
        try:
            # Get user's active cycle
            cycle = TradingCycle.query.filter_by(
                user_id=user_id, 
                status=CycleStatus.IN_PROGRESS
            ).first()
            
            if not cycle:
                logger.error(f"No active cycle found for user {user_id}")
                return False
                
            # Update daily ROI and turn off auto ROI
            cycle.daily_roi_percentage = daily_roi
            cycle.is_auto_roi = False
            
            db.session.commit()
            
            logger.info(f"Admin adjusted daily ROI for user {user_id} to {daily_roi}%")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error adjusting ROI: {e}")
            db.session.rollback()
            return False

def admin_pause_cycle(user_id):
    """
    Admin function to pause a user's active ROI cycle.
    
    Args:
        user_id (int): Database ID of the user
    
    Returns:
        bool: True if successful, False otherwise
    """
    with app.app_context():
        try:
            # Get user's active cycle
            cycle = TradingCycle.query.filter_by(
                user_id=user_id, 
                status=CycleStatus.IN_PROGRESS
            ).first()
            
            if not cycle:
                logger.error(f"No active cycle found for user {user_id}")
                return False
                
            # Pause the cycle
            cycle.status = CycleStatus.PAUSED
            
            db.session.commit()
            
            logger.info(f"Admin paused ROI cycle for user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error pausing cycle: {e}")
            db.session.rollback()
            return False

def admin_resume_cycle(user_id):
    """
    Admin function to resume a paused ROI cycle.
    
    Args:
        user_id (int): Database ID of the user
    
    Returns:
        bool: True if successful, False otherwise
    """
    with app.app_context():
        try:
            # Get user's paused cycle
            cycle = TradingCycle.query.filter_by(
                user_id=user_id, 
                status=CycleStatus.PAUSED
            ).first()
            
            if not cycle:
                logger.error(f"No paused cycle found for user {user_id}")
                return False
                
            # Resume the cycle
            cycle.status = CycleStatus.IN_PROGRESS
            
            db.session.commit()
            
            logger.info(f"Admin resumed ROI cycle for user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error resuming cycle: {e}")
            db.session.rollback()
            return False

def admin_update_cycle_after_balance_adjustment(user_id, adjustment_amount):
    """
    Admin function to update a user's active ROI cycle after a balance adjustment.
    This ensures the autopilot dashboard reflects the new balance immediately.
    
    Args:
        user_id (int): Database ID of the user
        adjustment_amount (float): Amount that was added to the user's balance
        
    Returns:
        bool: True if successful, False otherwise
    """
    with app.app_context():
        try:
            # Get user's active cycle
            cycle = TradingCycle.query.filter_by(
                user_id=user_id, 
                status=CycleStatus.IN_PROGRESS
            ).first()
            
            # If no active cycle, check if we need to create one
            if not cycle:
                # Get the user object
                user = User.query.get(user_id)
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                # Create a new cycle since there's been a balance adjustment
                return admin_start_new_cycle(user_id)
            
            # Update the cycle's current balance to reflect the adjustment
            previous_balance = cycle.current_balance
            cycle.current_balance += adjustment_amount
            
            # Log the balance update
            logger.info(f"Updated ROI cycle for user {user_id}: Balance {previous_balance:.4f} → {cycle.current_balance:.4f} (+{adjustment_amount:.4f})")
            
            # Update the progress percentage
            progress = min(100, ((cycle.current_balance - cycle.initial_balance) / (cycle.target_balance - cycle.initial_balance)) * 100)
            cycle.progress_percentage = max(0, progress)  # Ensure it's not negative
            
            # Check if the target has been reached
            if cycle.current_balance >= cycle.target_balance:
                cycle.status = CycleStatus.COMPLETED
                cycle.end_date = datetime.utcnow()
                logger.info(f"ROI cycle completed for user {user_id} after balance adjustment")
            
            db.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating cycle after balance adjustment: {e}")
            db.session.rollback()
            return False

def get_cycle_history(user_id, limit=10):
    """
    Get the trading cycle history for a user.
    
    Args:
        user_id (int): Database ID of the user
        limit (int): Maximum number of cycles to return
    
    Returns:
        list: List of trading cycles
    """
    with app.app_context():
        try:
            cycles = TradingCycle.query.filter_by(user_id=user_id)\
                .order_by(TradingCycle.start_date.desc())\
                .limit(limit).all()
                
            return cycles
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting cycle history: {e}")
            return []
