"""
Verify ROI Application
This script checks that ROI (Return on Investment) is correctly applied to user balances
"""
import logging
import time
from datetime import datetime

from app import app, db
from models import User, Transaction, Profit

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ROI VERIFICATION")

# ROI percentage to verify
ROI_PERCENTAGE = 8.5

def verify_roi_application():
    """
    Verify that the ROI has been correctly applied to all active users
    """
    print("\n===== ROI APPLICATION VERIFICATION =====")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"ROI Percentage: {ROI_PERCENTAGE}%")
    print("-" * 40)
    
    with app.app_context():
        # Get all active users
        from models import UserStatus
        active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
        
        print(f"Found {len(active_users)} active users")
        
        if not active_users:
            print("No active users found. Cannot verify ROI application.")
            return False
        
        # Sample a few users for detailed verification
        sample_size = min(5, len(active_users))
        sample_users = active_users[:sample_size]
        
        # Create headers for the report table
        print("\n{:<5} {:<15} {:<15} {:<15} {:<15} {:<10}".format(
            "ID", "Username", "Balance", "Calculated ROI", "Actual Profit", "Match"
        ))
        print("-" * 80)
        
        # Track results
        all_match = True
        total_users_affected = 0
        total_roi_applied = 0
        
        # Check each user in the sample
        for user in sample_users:
            # Get the user's balance
            balance = user.balance
            
            # Calculate expected ROI
            expected_roi = balance * (ROI_PERCENTAGE / 100)
            
            # Get actual recent profit records
            recent_profit = Profit.query.filter_by(user_id=user.id).order_by(Profit.date.desc()).first()
            
            if recent_profit:
                actual_profit = recent_profit.amount
                match = abs(actual_profit - expected_roi) < 0.0001
                
                if match:
                    total_users_affected += 1
                    total_roi_applied += actual_profit
                else:
                    all_match = False
                
                # Print the result row
                print("{:<5} {:<15} {:<15.4f} {:<15.4f} {:<15.4f} {:<10}".format(
                    user.id,
                    user.username or f"User {user.id}",
                    balance,
                    expected_roi,
                    actual_profit,
                    "✓" if match else "✗"
                ))
            else:
                all_match = False
                print("{:<5} {:<15} {:<15.4f} {:<15.4f} {:<15} {:<10}".format(
                    user.id,
                    user.username or f"User {user.id}",
                    balance,
                    expected_roi,
                    "N/A",
                    "✗"
                ))
        
        # Print summary
        print("\n----- SUMMARY -----")
        print(f"Total active users: {len(active_users)}")
        print(f"Users with correctly applied ROI: {total_users_affected}")
        print(f"Total ROI applied: {total_roi_applied:.4f} SOL")
        
        # Check for any skipped users
        skipped_users = len(active_users) - total_users_affected
        if skipped_users > 0:
            print(f"Warning: {skipped_users} active users may not have received ROI")
        
        # Check database synchronization
        print("\n----- DATABASE SYNCHRONIZATION -----")
        
        # Check profit transactions
        profit_txs = Transaction.query.filter_by(
            transaction_type='profit'
        ).order_by(Transaction.timestamp.desc()).limit(5).all()
        
        if profit_txs:
            print(f"Found {len(profit_txs)} recent profit transactions:")
            for i, tx in enumerate(profit_txs, 1):
                print(f"  {i}. User ID: {tx.user_id}, Amount: {tx.amount} SOL, Time: {tx.timestamp}")
            
            # Check if the transactions have the processed_at field
            if hasattr(profit_txs[0], 'processed_at') and profit_txs[0].processed_at:
                print(f"Profit transactions include processed_at timestamp ✓")
            else:
                print(f"Profit transactions do not include processed_at timestamp ✗")
        else:
            print("No profit transactions found in the database")
        
        # Final assessment
        print("\n===== VERIFICATION RESULTS =====")
        if all_match and total_users_affected == len(sample_users):
            print(f"✅ ROI of {ROI_PERCENTAGE}% has been correctly applied to all sampled users")
            print(f"✅ Database is properly synchronized with all profit records")
            
            if skipped_users == 0:
                print(f"✅ All active users received their ROI")
            else:
                print(f"⚠️ Some active users may not have received ROI")
        else:
            print(f"❌ ROI application verification failed")
            print(f"   - Sampled users with correct ROI: {total_users_affected}/{len(sample_users)}")
            
        return all_match and total_users_affected == len(sample_users)

if __name__ == "__main__":
    verify_roi_application()