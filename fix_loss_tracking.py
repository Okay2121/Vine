"""
Fix Loss Tracking System
========================
This script fixes the loss tracking system to ensure losses properly reduce daily profits
and are reflected in the dashboard calculations.
"""

from app import app, db
from models import User, Transaction, Profit, TradingPosition
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_loss_tracking():
    """
    Fix the loss tracking system by:
    1. Converting negative profit amounts to proper loss transactions
    2. Ensuring all losses are subtracted from daily totals
    3. Creating a unified loss recording system
    """
    
    with app.app_context():
        logger.info("Starting loss tracking system fix...")
        
        # Find all negative profit records that should be losses
        negative_profits = Profit.query.filter(Profit.amount < 0).all()
        
        logger.info(f"Found {len(negative_profits)} negative profit records to convert")
        
        for profit_record in negative_profits:
            try:
                # Convert negative profit to loss transaction
                loss_amount = abs(profit_record.amount)
                
                # Check if loss transaction already exists
                existing_loss = Transaction.query.filter_by(
                    user_id=profit_record.user_id,
                    transaction_type='trade_loss',
                    amount=loss_amount,
                    timestamp__date=profit_record.date
                ).first()
                
                if not existing_loss:
                    # Create loss transaction
                    loss_transaction = Transaction(
                        user_id=profit_record.user_id,
                        transaction_type='trade_loss',
                        amount=loss_amount,
                        timestamp=datetime.combine(profit_record.date, datetime.min.time().replace(hour=12)),
                        status='completed',
                        notes=f'Loss from negative profit record ID {profit_record.id}'
                    )
                    db.session.add(loss_transaction)
                    
                    logger.info(f"Created loss transaction for user {profit_record.user_id}: {loss_amount:.6f} SOL")
                
                # Remove the negative profit record (it's now represented as a loss transaction)
                db.session.delete(profit_record)
                
            except Exception as e:
                logger.error(f"Error processing negative profit record {profit_record.id}: {e}")
                db.session.rollback()
                continue
        
        # Find trading positions with negative ROI but no corresponding loss transactions
        negative_positions = TradingPosition.query.filter(
            TradingPosition.roi_percentage < 0,
            TradingPosition.status == 'closed'
        ).all()
        
        logger.info(f"Found {len(negative_positions)} negative trading positions to check")
        
        for position in negative_positions:
            try:
                # Calculate loss amount based on ROI
                if hasattr(position, 'profit_amount') and position.profit_amount:
                    loss_amount = abs(position.profit_amount)
                else:
                    # Estimate loss based on ROI percentage and typical trade size
                    loss_amount = abs(position.roi_percentage / 100) * 1.0  # Assume 1 SOL trade size
                
                # Check if loss transaction exists for this position
                position_date = position.sell_timestamp.date() if position.sell_timestamp else position.timestamp.date()
                
                existing_loss = Transaction.query.filter_by(
                    user_id=position.user_id,
                    transaction_type='trade_loss',
                    amount=loss_amount
                ).filter(
                    Transaction.timestamp >= datetime.combine(position_date, datetime.min.time()),
                    Transaction.timestamp <= datetime.combine(position_date, datetime.max.time())
                ).first()
                
                if not existing_loss and loss_amount > 0:
                    # Create loss transaction for this position
                    loss_transaction = Transaction(
                        user_id=position.user_id,
                        transaction_type='trade_loss',
                        amount=loss_amount,
                        token_name=position.token_name,
                        timestamp=position.sell_timestamp or position.timestamp,
                        status='completed',
                        notes=f'Loss from trading position {position.id} ({position.token_name})',
                        tx_hash=position.sell_tx_hash or position.buy_tx_hash
                    )
                    db.session.add(loss_transaction)
                    
                    logger.info(f"Created loss transaction for position {position.id}: {loss_amount:.6f} SOL")
                
            except Exception as e:
                logger.error(f"Error processing negative position {position.id}: {e}")
                continue
        
        try:
            db.session.commit()
            logger.info("Loss tracking system fix completed successfully")
            
            # Test the fix with a specific user
            test_user = User.query.filter_by(telegram_id='7611754415').first()
            if test_user:
                from performance_tracking import get_performance_data
                perf_data = get_performance_data(test_user.id)
                logger.info(f"Test user updated profit: {perf_data['today_profit']:.6f} SOL ({perf_data['today_percentage']:.2f}%)")
            
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            db.session.rollback()

def simulate_loss_transaction(user_id, loss_amount=0.01):
    """
    Simulate a loss transaction to test the system
    """
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return
        
        # Create a test loss transaction
        loss_transaction = Transaction(
            user_id=user_id,
            transaction_type='trade_loss',
            amount=loss_amount,
            token_name='TEST',
            timestamp=datetime.utcnow(),
            status='completed',
            notes='Test loss transaction to verify tracking system'
        )
        db.session.add(loss_transaction)
        db.session.commit()
        
        logger.info(f"Created test loss transaction: {loss_amount:.6f} SOL for user {user_id}")
        
        # Check updated performance
        from performance_tracking import get_performance_data
        perf_data = get_performance_data(user_id)
        logger.info(f"Updated performance after loss: {perf_data['today_profit']:.6f} SOL ({perf_data['today_percentage']:.2f}%)")

if __name__ == "__main__":
    fix_loss_tracking()