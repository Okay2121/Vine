#!/usr/bin/env python
"""
Fix for admin balance adjustment functionality
This script verifies that a user's balance can be properly updated through admin adjustments
and that the change is reflected in the user's dashboard.
"""
import logging
import sys
from datetime import datetime
from app import app, db
from models import User, Transaction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def list_users():
    """List all users in the database to identify who to adjust"""
    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found in the database.")
            return
            
        print(f"\nFound {len(users)} users:")
        for user in users:
            print(f"ID: {user.id}, Telegram: {user.telegram_id}, Username: @{user.username}, Balance: {user.balance:.4f} SOL")
        print()

def check_user_dashboard(user_id=None, telegram_id=None, username=None):
    """Check a user's dashboard including balance and transaction history"""
    with app.app_context():
        # Find the user
        user = None
        if user_id:
            user = User.query.get(user_id)
        elif telegram_id:
            user = User.query.filter_by(telegram_id=telegram_id).first()
        elif username:
            if username.startswith('@'):
                username = username[1:]
            user = User.query.filter_by(username=username).first()
            
        if not user:
            print(f"User not found.")
            return
            
        # Display user information
        print(f"\n==== USER DASHBOARD ====")
        print(f"ID: {user.id}")
        print(f"Telegram ID: {user.telegram_id}")
        print(f"Username: @{user.username}")
        print(f"Balance: {user.balance:.4f} SOL")
        
        # Get transaction history
        transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
        
        if transactions:
            print(f"\nRecent Transactions:")
            for i, tx in enumerate(transactions, 1):
                print(f"{i}. {tx.transaction_type.upper()} - {tx.amount:.4f} SOL - {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {tx.notes or 'No notes'}")
        else:
            print("\nNo recent transactions found.")
        
        print(f"=======================\n")

def adjust_balance(user_identifier, amount, reason="Manual adjustment"):
    """Adjust a user's balance directly"""
    with app.app_context():
        # Find the user
        user = None
        if isinstance(user_identifier, int) or user_identifier.isdigit():
            # First try by ID
            user = User.query.get(int(user_identifier))
            if not user:
                # Then try by telegram_id
                user = User.query.filter_by(telegram_id=user_identifier).first()
        else:
            # Try by username
            if user_identifier.startswith('@'):
                user_identifier = user_identifier[1:]
            user = User.query.filter_by(username=user_identifier).first()
            
        if not user:
            print(f"User not found: {user_identifier}")
            return False
            
        # Store old balance
        old_balance = user.balance
        
        # Update balance
        user.balance += float(amount)
        
        # Create transaction
        tx_type = 'admin_credit' if float(amount) > 0 else 'admin_debit'
        transaction = Transaction(
            user_id=user.id,
            transaction_type=tx_type,
            amount=abs(float(amount)),
            token_name="SOL",
            timestamp=datetime.utcnow(),
            status='completed',
            notes=reason
        )
        
        # Save changes
        db.session.add(transaction)
        db.session.commit()
        
        # Display results
        print(f"\n✅ Balance adjusted successfully!")
        print(f"User: {user.username} (ID: {user.id}, Telegram ID: {user.telegram_id})")
        print(f"Old Balance: {old_balance:.4f} SOL")
        print(f"New Balance: {user.balance:.4f} SOL")
        print(f"Change: {'➕' if float(amount) > 0 else '➖'} {abs(float(amount)):.4f} SOL")
        print(f"Reason: {reason}")
        print(f"Transaction ID: {transaction.id}\n")
        
        return True

def main():
    """Main function to run the fix"""
    print("Admin Balance Adjustment Fix")
    print("----------------------------")
    
    # List all users
    list_users()
    
    # Get user to adjust
    user_input = input("Enter user ID, Telegram ID, or username to adjust: ")
    
    # Check user dashboard before adjustment
    print("\nUser dashboard BEFORE adjustment:")
    check_user_dashboard(username=user_input)
    
    # Get adjustment amount
    amount = input("Enter adjustment amount (positive to add, negative to subtract): ")
    try:
        amount = float(amount)
    except ValueError:
        print("Invalid amount. Please enter a number.")
        return
        
    # Get reason
    reason = input("Enter reason for adjustment (or press Enter for default): ")
    if not reason:
        reason = "Manual balance adjustment"
    
    # Adjust balance
    success = adjust_balance(user_input, amount, reason)
    if not success:
        return
    
    # Check user dashboard after adjustment
    print("\nUser dashboard AFTER adjustment:")
    check_user_dashboard(username=user_input)
    
    print("\nBalance adjustment completed successfully.")
    
if __name__ == "__main__":
    with app.app_context():
        main()