#!/usr/bin/env python
"""
Working Balance Manager - Fixed version for balance adjustments
This version ensures database updates actually persist correctly
"""
import logging
from datetime import datetime
from app import app, db
from models import User, Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def adjust_balance_fixed(telegram_id, amount, reason="Admin balance adjustment"):
    """
    Fixed balance adjustment that actually works
    
    Args:
        telegram_id (str): Telegram ID of the user
        amount (float): Amount to adjust (positive to add, negative to deduct)
        reason (str): Reason for the adjustment
        
    Returns:
        tuple: (success, message)
    """
    try:
        amount = float(amount)
    except ValueError:
        return False, f"Invalid amount: {amount}"
    
    with app.app_context():
        try:
            # Find user by telegram_id
            user = User.query.filter_by(telegram_id=str(telegram_id)).first()
            
            if not user:
                return False, f"User not found with Telegram ID: {telegram_id}"
            
            # Store original balance
            original_balance = float(user.balance or 0)
            
            # Check if deduction would make balance negative
            if amount < 0 and abs(amount) > original_balance:
                return False, f"Cannot deduct {abs(amount)} SOL - user only has {original_balance} SOL"
            
            # Calculate new balance
            new_balance = original_balance + amount
            
            # Update balance using direct SQL to ensure it persists
            from sqlalchemy import text
            db.session.execute(
                text("UPDATE \"user\" SET balance = :new_balance WHERE telegram_id = :telegram_id"),
                {"new_balance": new_balance, "telegram_id": telegram_id}
            )
            
            # Create transaction record
            transaction_type = 'admin_credit' if amount > 0 else 'admin_debit'
            
            # Insert transaction using direct SQL too
            db.session.execute(
                text("""INSERT INTO "transaction" (user_id, transaction_type, amount, token_name, timestamp, status, notes)
                     VALUES (:user_id, :transaction_type, :amount, :token_name, :timestamp, :status, :notes)"""),
                {
                    "user_id": user.id,
                    "transaction_type": transaction_type,
                    "amount": abs(amount),
                    "token_name": "SOL",
                    "timestamp": datetime.utcnow(),
                    "status": "completed",
                    "notes": reason
                }
            )
            
            # Commit the changes
            db.session.commit()
            
            # Verify the update worked
            result = db.session.execute(
                text("SELECT balance FROM \"user\" WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id}
            )
            actual_balance = result.scalar()
            
            action_type = "added to" if amount > 0 else "deducted from"
            message = (
                f"BALANCE ADJUSTMENT SUCCESSFUL\n"
                f"User: {user.username} (Telegram ID: {telegram_id})\n"
                f"{abs(amount):.4f} SOL {action_type} balance\n"
                f"Previous balance: {original_balance:.4f} SOL\n"
                f"New balance: {actual_balance:.4f} SOL\n"
                f"Reason: {reason}"
            )
            
            logger.info(message)
            return True, message
            
        except Exception as e:
            db.session.rollback()
            error_message = f"Error adjusting balance: {e}"
            logger.error(error_message)
            return False, error_message

if __name__ == "__main__":
    # Test the function
    success, message = adjust_balance_fixed("5488280696", 1.0, "Test adjustment")
    print("SUCCESS:" if success else "FAILED:", message)