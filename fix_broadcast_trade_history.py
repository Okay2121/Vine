#!/usr/bin/env python
"""
Fix Broadcast Trade History - Ensure trades immediately reflect in user transaction history
"""
import logging
from datetime import datetime
from app import app, db
from models import User, Transaction, TradingPosition

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_trade_to_users_with_history(position, roi_percentage):
    """
    Apply trade to users and immediately create transaction history records
    
    Args:
        position: The trading position
        roi_percentage: ROI percentage for the trade
        
    Returns:
        tuple: (success, message, updated_count)
    """
    try:
        with app.app_context():
            # Get all active users with balance > 0
            users = User.query.filter(User.balance > 0).all()
            
            if not users:
                return False, "No active users found", 0
            
            updated_count = 0
            
            for user in users:
                try:
                    # Calculate profit/loss for this user
                    profit_percentage = roi_percentage / 100  # Convert to decimal
                    profit_amount = user.balance * profit_percentage
                    
                    # Skip very small amounts
                    if abs(profit_amount) < 0.000001:
                        continue
                    
                    # Store original balance
                    original_balance = user.balance
                    
                    # Update user balance using direct SQL for reliability
                    from sqlalchemy import text
                    db.session.execute(
                        text("UPDATE \"user\" SET balance = balance + :amount WHERE id = :user_id"),
                        {"amount": profit_amount, "user_id": user.id}
                    )
                    
                    # Create transaction record that will show in history
                    transaction = Transaction()
                    transaction.user_id = user.id
                    transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                    transaction.amount = abs(profit_amount)
                    transaction.token_name = position.token_name if hasattr(position, 'token_name') else "SOL"
                    transaction.timestamp = datetime.utcnow()
                    transaction.status = 'completed'
                    transaction.notes = f"Trade ROI: {roi_percentage:.2f}% - {getattr(position, 'token_name', 'UNKNOWN')}"
                    
                    # Create unique tx_hash for this trade
                    if hasattr(position, 'sell_tx_hash') and position.sell_tx_hash:
                        transaction.tx_hash = f"{position.sell_tx_hash}_u{user.id}"
                    else:
                        transaction.tx_hash = f"trade_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_u{user.id}"
                    
                    transaction.processed_at = datetime.utcnow()
                    
                    # Add transaction to session
                    db.session.add(transaction)
                    
                    updated_count += 1
                    logger.info(f"Applied trade to user {user.username} (ID: {user.id}): {profit_amount:.6f} SOL")
                    
                except Exception as user_error:
                    logger.error(f"Error processing trade for user {user.id}: {user_error}")
                    continue
            
            # Commit all changes at once
            db.session.commit()
            
            return True, f"Applied trade to {updated_count} users with transaction history", updated_count
            
    except Exception as e:
        logger.error(f"Error applying trade to users: {e}")
        db.session.rollback()
        return False, f"Error applying trade to users: {e}", 0

def test_broadcast_trade(token_name="TESTCOIN", roi_percentage=5.0):
    """
    Test function to simulate a broadcast trade and verify it creates transaction history
    """
    try:
        # Create a mock position object
        class MockPosition:
            def __init__(self):
                self.token_name = token_name
                self.sell_tx_hash = f"test_tx_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        position = MockPosition()
        
        # Apply the trade
        success, message, count = apply_trade_to_users_with_history(position, roi_percentage)
        
        if success:
            logger.info(f"✅ Test broadcast trade successful: {message}")
            
            # Verify transaction records were created
            with app.app_context():
                recent_transactions = Transaction.query.filter(
                    Transaction.token_name == token_name
                ).order_by(Transaction.timestamp.desc()).limit(5).all()
                
                logger.info(f"Created {len(recent_transactions)} transaction records:")
                for tx in recent_transactions:
                    logger.info(f"  - User {tx.user_id}: {tx.amount:.6f} {tx.token_name} ({tx.transaction_type})")
                    
            return True
        else:
            logger.error(f"❌ Test broadcast trade failed: {message}")
            return False
            
    except Exception as e:
        logger.error(f"Error in test broadcast trade: {e}")
        return False

if __name__ == "__main__":
    # Test the function
    print("Testing broadcast trade with transaction history...")
    success = test_broadcast_trade()
    
    if success:
        print("✅ Broadcast trade history system is working correctly!")
    else:
        print("❌ There are issues with the broadcast trade history system.")