"""
Force Loss Transaction Creation
==============================
This script manually creates the missing BONETANK loss transaction
to ensure the dashboard reflects the actual loss that occurred.
"""

from app import app, db
from models import User, Transaction, TradingPosition
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_bonetank_loss_transaction():
    """Create the missing BONETANK loss transaction for the user"""
    
    with app.app_context():
        # Find user
        user = User.query.filter_by(telegram_id='7611754415').first()
        if not user:
            logger.error("User not found")
            return
        
        logger.info(f"Creating BONETANK loss transaction for user {user.id}")
        
        # Find the BONETANK trading position with negative ROI
        bonetank_position = TradingPosition.query.filter_by(
            user_id=user.id,
            token_name='BONETANK',
            status='closed'
        ).filter(TradingPosition.roi_percentage < 0).first()
        
        if not bonetank_position:
            logger.error("BONETANK loss position not found")
            return
        
        # Calculate loss amount from the logs (-0.8709 SOL)
        loss_amount = 0.8709  # From the logs: "profit: -0.8709 SOL"
        
        # Create unique transaction hash to avoid duplicates
        unique_suffix = int(datetime.utcnow().timestamp())
        tx_hash = f"bonetank_loss_{user.id}_{unique_suffix}"
        
        # Create the loss transaction
        loss_transaction = Transaction(
            user_id=user.id,
            transaction_type='trade_loss',
            amount=loss_amount,
            token_name='BONETANK',
            timestamp=datetime.utcnow(),
            status='completed',
            notes=f'BONETANK trade loss from position {bonetank_position.id}',
            tx_hash=tx_hash
        )
        
        try:
            db.session.add(loss_transaction)
            db.session.commit()
            
            logger.info(f"Successfully created BONETANK loss transaction: {loss_amount:.6f} SOL")
            
            # Verify the updated performance
            from performance_tracking import get_performance_data
            perf_data = get_performance_data(user.id)
            
            logger.info(f"Updated performance data:")
            logger.info(f"  Today profit: {perf_data['today_profit']:.6f} SOL")
            logger.info(f"  Today percentage: {perf_data['today_percentage']:.2f}%")
            
            return True, loss_amount
            
        except Exception as e:
            logger.error(f"Error creating loss transaction: {e}")
            db.session.rollback()
            return False, 0

def verify_loss_impact():
    """Verify that the loss properly reduced the daily profit"""
    
    with app.app_context():
        user = User.query.filter_by(telegram_id='7611754415').first()
        if not user:
            return
        
        # Check all today's transactions
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_transactions = Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.timestamp >= today_start,
            Transaction.timestamp <= today_end
        ).order_by(Transaction.timestamp.desc()).all()
        
        total_profits = 0
        total_losses = 0
        
        print(f"Today's transactions for user {user.id}:")
        for tx in today_transactions:
            print(f"  {tx.timestamp}: {tx.transaction_type} - {tx.amount:.6f} SOL - {tx.token_name or 'N/A'}")
            
            if tx.transaction_type == 'trade_profit':
                total_profits += tx.amount
            elif tx.transaction_type == 'trade_loss':
                total_losses += tx.amount
        
        net_profit = total_profits - total_losses
        print(f"\nSummary:")
        print(f"  Total profits: {total_profits:.6f} SOL")
        print(f"  Total losses: {total_losses:.6f} SOL")
        print(f"  Net profit: {net_profit:.6f} SOL")
        
        # Check performance data
        from performance_tracking import get_performance_data
        perf_data = get_performance_data(user.id)
        print(f"  Dashboard shows: {perf_data['today_profit']:.6f} SOL ({perf_data['today_percentage']:.2f}%)")

if __name__ == "__main__":
    success, amount = create_bonetank_loss_transaction()
    if success:
        print(f"Created BONETANK loss transaction: {amount:.6f} SOL")
        verify_loss_impact()
    else:
        print("Failed to create loss transaction")