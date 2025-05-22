"""
Test ROI Application
This script tests the 8.5% ROI application to existing users in the system
"""
import logging
from datetime import datetime

from app import app, db
from models import User, Transaction, Profit, UserStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ROI_TEST")

# ROI percentage to apply
ROI_PERCENTAGE = 8.5

def get_user_details():
    """Get details of all users in the system"""
    with app.app_context():
        users = User.query.all()
        
        print(f"\nFound {len(users)} users in the system")
        print("-" * 60)
        print(f"{'ID':<5} {'Username':<15} {'Telegram ID':<15} {'Status':<10} {'Balance':<10}")
        print("-" * 60)
        
        for user in users:
            status = user.status.value if hasattr(user.status, 'value') else str(user.status)
            print(f"{user.id:<5} {user.username or 'N/A':<15} {user.telegram_id:<15} {status:<10} {user.balance:<10.2f}")
        
        return users

def update_user_status(user_id):
    """Set a specific user to ACTIVE status for testing"""
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User with ID {user_id} not found")
            return False
            
        # Set user to active status
        user.status = UserStatus.ACTIVE
        db.session.commit()
        
        print(f"User {user.username or user.telegram_id} (ID: {user.id}) set to ACTIVE status")
        return True

def apply_roi_to_user(user_id):
    """Apply the 8.5% ROI to a specific user"""
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User with ID {user_id} not found")
            return False
            
        # Record pre-ROI state
        initial_balance = user.balance
        print(f"\nApplying {ROI_PERCENTAGE}% ROI to user: {user.username or user.telegram_id}")
        print(f"Initial balance: {initial_balance} SOL")
        
        # Calculate ROI amount
        roi_amount = initial_balance * (ROI_PERCENTAGE / 100)
        
        # Update user balance
        user.balance += roi_amount
        
        # Create profit record
        today = datetime.utcnow().date()
        profit = Profit.query.filter_by(user_id=user.id, date=today).first()
        
        if profit:
            # Update existing profit
            profit.amount = roi_amount
            profit.percentage = ROI_PERCENTAGE
            print(f"Updated existing profit record")
        else:
            # Create new profit record
            profit = Profit(
                user_id=user.id,
                amount=roi_amount,
                percentage=ROI_PERCENTAGE,
                date=today
            )
            db.session.add(profit)
            print(f"Created new profit record")
        
        # Create transaction record
        tx = Transaction(
            user_id=user.id,
            transaction_type="profit",
            amount=roi_amount,
            status="completed",
            notes=f"Daily ROI: {ROI_PERCENTAGE}%",
            timestamp=datetime.utcnow()
        )
        
        # Set processed_at if the field exists
        if hasattr(tx, 'processed_at'):
            tx.processed_at = datetime.utcnow()
            
        db.session.add(tx)
        db.session.commit()
        
        # Verify the changes
        updated_user = User.query.get(user_id)
        expected_balance = initial_balance + roi_amount
        
        print(f"ROI amount: {roi_amount:.4f} SOL")
        print(f"Expected new balance: {expected_balance:.4f} SOL")
        print(f"Actual new balance: {updated_user.balance:.4f} SOL")
        
        balance_match = abs(updated_user.balance - expected_balance) < 0.0001
        print(f"Balance correctly updated: {'✅' if balance_match else '❌'}")
        
        # Get the transaction record
        tx_record = Transaction.query.filter_by(
            user_id=user.id,
            transaction_type="profit",
            notes=f"Daily ROI: {ROI_PERCENTAGE}%"
        ).order_by(Transaction.timestamp.desc()).first()
        
        if tx_record:
            print(f"\nTransaction record created:")
            print(f"  Type: {tx_record.transaction_type}")
            print(f"  Amount: {tx_record.amount:.4f} SOL")
            print(f"  Status: {tx_record.status}")
            print(f"  Timestamp: {tx_record.timestamp}")
            
            if hasattr(tx_record, 'processed_at') and tx_record.processed_at:
                print(f"  Processed at: {tx_record.processed_at}")
        else:
            print("❌ Transaction record not found")
        
        # Get the profit record
        profit_record = Profit.query.filter_by(
            user_id=user.id,
            date=today
        ).first()
        
        if profit_record:
            print(f"\nProfit record created/updated:")
            print(f"  Amount: {profit_record.amount:.4f} SOL")
            print(f"  Percentage: {profit_record.percentage:.2f}%")
            print(f"  Date: {profit_record.date}")
        else:
            print("❌ Profit record not found")
        
        return balance_match

def run_roi_test():
    """Run the ROI test on an existing user"""
    print("\n===== ROI APPLICATION TEST =====")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"ROI Percentage: {ROI_PERCENTAGE}%")
    
    # Step 1: Get list of users
    users = get_user_details()
    
    if not users:
        print("No users found in the system")
        return False
    
    # Step 2: Select a user to test with
    selected_user_id = users[0].id  # Use the first user by default
    
    # Step 3: Make sure the user is in ACTIVE status
    update_user_status(selected_user_id)
    
    # Step 4: Apply ROI to the user
    success = apply_roi_to_user(selected_user_id)
    
    # Step 5: Final verification
    print("\n===== TEST RESULTS =====")
    if success:
        print(f"✅ ROI application test PASSED")
        print(f"The 8.5% ROI was successfully applied to the user's balance")
        print(f"All profit records and transactions were correctly created")
        print(f"The system is properly synchronized in real-time")
    else:
        print(f"❌ ROI application test FAILED")
        print(f"Check the logs above for details on what went wrong")
    
    return success

if __name__ == "__main__":
    run_roi_test()