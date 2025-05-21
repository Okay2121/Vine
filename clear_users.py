"""
Script to clear all users from the database
"""
from app import app, db
from models import User, Transaction, Profit, ReferralCode, UserStatus

def clear_all_users():
    """Clear all users from the database"""
    print("Starting database cleanup...")
    
    with app.app_context():
        try:
            # First delete all transactions (due to foreign key constraints)
            transaction_count = Transaction.query.delete()
            print(f"Deleted {transaction_count} transactions")
            
            # Delete profits
            profit_count = Profit.query.delete()
            print(f"Deleted {profit_count} profit records")
            
            # Delete referral codes
            referral_code_count = ReferralCode.query.delete()
            print(f"Deleted {referral_code_count} referral codes")
            
            # Finally delete users
            user_count = User.query.delete()
            print(f"Deleted {user_count} users")
            
            # Commit the changes
            db.session.commit()
            print("All users and related data successfully cleared from the database")
        except Exception as e:
            print(f"Error clearing users: {e}")
            db.session.rollback()

if __name__ == "__main__":
    clear_all_users()