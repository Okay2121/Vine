"""
Simple Balance Adjuster - A robust solution for adjusting user balances
This fixes the issue where balance adjustments aren't properly updating in the database
"""
import logging
import sys
from datetime import datetime
from sqlalchemy import text
from app import app, db
from models import User, Transaction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def adjust_user_balance(identifier, amount, reason="Admin balance adjustment"):
    """
    Reliably adjust a user's balance using direct SQL when needed
    
    Args:
        identifier (str): Username (with or without @) or telegram_id
        amount (float): Amount to adjust (positive to add, negative to deduct)
        reason (str): Reason for the adjustment
        
    Returns:
        tuple: (success, message)
    """
    # Ensure we're working with a valid amount
    try:
        amount = float(amount)
    except ValueError:
        return False, f"Invalid amount: {amount}"
    
    with app.app_context():
        # Find the user
        user = None
        
        # Try finding by telegram_id first
        if identifier.isdigit():
            user = User.query.filter_by(telegram_id=identifier).first()
        
        # Then try by username (strip @ if present)
        if not user and isinstance(identifier, str):
            username = identifier.lstrip('@')
            user = User.query.filter(User.username.ilike(username)).first()
            
        # Last resort, try by id
        if not user and identifier.isdigit():
            user = User.query.get(int(identifier))
            
        if not user:
            return False, f"User not found: {identifier}"
            
        # Check if deduction would make balance negative
        if amount < 0 and abs(amount) > user.balance:
            return False, f"Cannot deduct {abs(amount)} SOL - user only has {user.balance} SOL"
        
        # Store original balance for logging
        original_balance = user.balance
        logger.info(f"Original balance for {user.username}: {original_balance}")
        
        try:
            # Method 1: Use direct SQL update which is more reliable
            # Use parameterized query to avoid SQL injection
            sql = text("UPDATE user SET balance = balance + :amount WHERE id = :user_id")
            db.session.execute(sql, {"amount": amount, "user_id": user.id})
            
            # No need for ORM update since we're using direct SQL
            
            # Create transaction record
            transaction = Transaction()
            transaction.user_id = user.id
            transaction.transaction_type = 'admin_credit' if amount > 0 else 'admin_debit'
            transaction.amount = abs(amount)
            transaction.token_name = "SOL"
            transaction.timestamp = datetime.utcnow()
            transaction.status = 'completed'
            transaction.notes = reason
            
            # Add and commit
            db.session.add(transaction)
            db.session.commit()
            
            # Refresh the user to see the new balance
            db.session.refresh(user)
            new_balance = user.balance
            
            # Verify the change was made
            if abs(new_balance - (original_balance + amount)) > 0.0001:
                logger.warning(f"Balance may not have updated correctly. Expected: {original_balance + amount}, Got: {new_balance}")
            
            # Format success message
            action = "added to" if amount > 0 else "deducted from"
            message = (
                f"✅ Balance adjustment successful\n\n"
                f"User: {user.username} (ID: {user.id})\n"
                f"{abs(amount):.4f} SOL {action} balance\n"
                f"Previous balance: {original_balance:.4f} SOL\n"
                f"New balance: {new_balance:.4f} SOL\n"
                f"Reason: {reason}"
            )
            
            return True, message
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adjusting balance: {e}")
            return False, f"Database error: {str(e)}"

def test_adjustment():
    """Test the balance adjuster with a small amount"""
    # Find first user in system
    with app.app_context():
        user = User.query.first()
        if not user:
            print("No users found for testing")
            return
            
        print(f"Testing with user: {user.username} (ID: {user.id})")
        print(f"Current balance: {user.balance}")
        
        # Make a small positive adjustment
        success, message = adjust_user_balance(
            str(user.id),
            0.001,
            "Test adjustment"
        )
        
        print(f"Adjustment result: {success}")
        print(message)
        
        # Verify the change
        user = User.query.get(user.id)  # Refresh user
        print(f"Updated balance: {user.balance}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simple_balance_adjuster.py <username/telegram_id> <amount> [reason]")
        print("Example: python simple_balance_adjuster.py @user123 1.5 'Bonus payment'")
        
        # Run test if no arguments
        print("\nRunning test adjustment...")
        test_adjustment()
    else:
        identifier = sys.argv[1]
        amount = sys.argv[2]
        reason = sys.argv[3] if len(sys.argv) > 3 else "Admin balance adjustment"
        
        success, message = adjust_user_balance(identifier, amount, reason)
        print(message)