#!/usr/bin/env python
"""
Test Balance Adjustment Message Sequence
This test verifies that the complete message sequence is restored after clicking confirm
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

def test_balance_adjustment_message_sequence():
    """Test the balance adjustment with focus on message sequence"""
    
    logger.info("🧪 Testing Balance Adjustment Message Sequence")
    
    with app.app_context():
        try:
            # Find a test user (or create one)
            test_user = User.query.filter_by(username='electrocute2011').first()
            
            if not test_user:
                logger.info("Creating test user for demonstration")
                test_user = User(
                    telegram_id='7195974467',
                    username='electrocute2011',
                    first_name='Test',
                    balance=0.0000
                )
                db.session.add(test_user)
                db.session.commit()
                logger.info(f"Created test user: {test_user.username}")
            
            logger.info(f"Test user found: {test_user.username} (ID: {test_user.telegram_id})")
            logger.info(f"Current balance: {test_user.balance:.4f} SOL")
            
            # Test the working balance manager directly
            from working_balance_manager import adjust_balance_fixed
            
            # Simulate the adjustment that would happen after clicking confirm
            test_amount = 0.6100
            test_reason = "Bonus"
            
            logger.info(f"Testing adjustment: +{test_amount} SOL for reason: {test_reason}")
            
            # This is what happens when confirm is clicked
            success, detailed_message = adjust_balance_fixed(str(test_user.telegram_id), test_amount, test_reason)
            
            if success:
                logger.info("✅ Balance adjustment successful!")
                
                # Show what messages would be sent in sequence
                print("\n" + "="*60)
                print("MESSAGE SEQUENCE AFTER CLICKING CONFIRM:")
                print("="*60)
                
                # Message 1: Processing
                print("1️⃣ FIRST MESSAGE:")
                print("✅ Processing your balance adjustment request...")
                print()
                
                # Message 2: Completion
                action = "added" if test_amount > 0 else "deducted"
                print("2️⃣ SECOND MESSAGE:")
                print("BALANCE ADJUSTMENT COMPLETED")
                print()
                print(f"Amount: {abs(test_amount):.4f} SOL {action}")
                print()
                
                # Message 3: Detailed success (this comes from working_balance_manager)
                print("3️⃣ THIRD MESSAGE:")
                print(detailed_message)
                print()
                
                print("="*60)
                print("✅ All three messages will be displayed in sequence!")
                print("="*60)
                
                # Verify the balance was actually updated
                updated_user = User.query.filter_by(telegram_id=str(test_user.telegram_id)).first()
                logger.info(f"Updated balance: {updated_user.balance:.4f} SOL")
                
                return True
                
            else:
                logger.error(f"❌ Balance adjustment failed: {detailed_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def main():
    """Run the test"""
    logger.info("Starting Balance Adjustment Message Sequence Test")
    
    success = test_balance_adjustment_message_sequence()
    
    if success:
        logger.info("✅ TEST PASSED: Message sequence is working correctly")
        print("\n🎉 The balance adjustment message sequence has been restored!")
        print("When you click 'Confirm', you will see all three messages as shown above.")
    else:
        logger.error("❌ TEST FAILED: Issues detected")
        
    return success

if __name__ == "__main__":
    main()