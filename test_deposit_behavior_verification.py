#!/usr/bin/env python
"""
Comprehensive Test: Cumulative Initial Deposit Verification
Tests that initial deposit increases with each new deposit
"""
import logging
from datetime import datetime
from app import app, db
from models import User, Transaction
from utils.solana import process_auto_deposit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_comprehensive_deposit_test():
    """Run a complete test of the cumulative deposit behavior"""
    
    print("="*60)
    print("TESTING CUMULATIVE INITIAL DEPOSIT BEHAVIOR")
    print("="*60)
    
    with app.app_context():
        try:
            # Clean up any existing test user
            test_user = User.query.filter_by(username='deposit_test_user').first()
            if test_user:
                Transaction.query.filter_by(user_id=test_user.id).delete()
                db.session.delete(test_user)
                db.session.commit()
                print("Cleaned up existing test user")
            
            # Create fresh test user
            test_user = User(
                telegram_id='777777777',
                username='deposit_test_user',
                first_name='DepositTest',
                balance=0.0,
                initial_deposit=0.0
            )
            db.session.add(test_user)
            db.session.commit()
            
            print(f"\nCreated test user: {test_user.username}")
            print(f"Starting state: Balance={test_user.balance:.4f}, Initial={test_user.initial_deposit:.4f}")
            
            # Track expected values
            expected_balance = 0.0
            expected_initial = 0.0
            
            # Test deposits
            deposits = [1.5, 2.0, 0.75, 3.25]
            
            for i, deposit_amount in enumerate(deposits, 1):
                print(f"\n--- DEPOSIT {i}: {deposit_amount} SOL ---")
                
                # Process the deposit
                success = process_auto_deposit(test_user.id, deposit_amount, f"test_tx_{i}")
                
                if not success:
                    print(f"❌ Deposit {i} failed!")
                    return False
                
                # Update expected values
                expected_balance += deposit_amount
                expected_initial += deposit_amount
                
                # Refresh user data
                db.session.refresh(test_user)
                
                # Display results
                print(f"Expected: Balance={expected_balance:.4f}, Initial={expected_initial:.4f}")
                print(f"Actual:   Balance={test_user.balance:.4f}, Initial={test_user.initial_deposit:.4f}")
                
                # Verify values
                if abs(test_user.balance - expected_balance) > 0.001:
                    print(f"❌ Balance mismatch! Expected {expected_balance:.4f}, got {test_user.balance:.4f}")
                    return False
                
                if abs(test_user.initial_deposit - expected_initial) > 0.001:
                    print(f"❌ Initial deposit mismatch! Expected {expected_initial:.4f}, got {test_user.initial_deposit:.4f}")
                    return False
                
                print(f"✅ Deposit {i} processed correctly")
            
            # Final verification
            print(f"\n--- FINAL VERIFICATION ---")
            total_deposited = sum(deposits)
            print(f"Total deposited: {total_deposited:.4f} SOL")
            print(f"Final balance: {test_user.balance:.4f} SOL")
            print(f"Final initial deposit: {test_user.initial_deposit:.4f} SOL")
            
            # Check transaction count
            deposit_count = Transaction.query.filter_by(
                user_id=test_user.id,
                transaction_type='deposit',
                status='completed'
            ).count()
            print(f"Deposit transactions recorded: {deposit_count}")
            
            # Verify all values match
            if (abs(test_user.balance - total_deposited) < 0.001 and 
                abs(test_user.initial_deposit - total_deposited) < 0.001 and
                deposit_count == len(deposits)):
                
                print("\n" + "="*60)
                print("🎉 ALL TESTS PASSED!")
                print("✅ Initial deposit correctly increases with each deposit")
                print("✅ Balance and initial deposit stay synchronized")
                print("✅ All transactions properly recorded")
                print("="*60)
                return True
            else:
                print("\n❌ VERIFICATION FAILED")
                return False
                
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_existing_user_behavior():
    """Test the behavior with an existing user"""
    
    print("\n" + "="*60)
    print("TESTING WITH EXISTING USER")
    print("="*60)
    
    with app.app_context():
        try:
            # Find the electrocute2011 user
            user = User.query.filter_by(username='electrocute2011').first()
            
            if not user:
                print("User electrocute2011 not found, skipping existing user test")
                return True
            
            print(f"Found user: {user.username}")
            print(f"Current state: Balance={user.balance:.4f}, Initial={user.initial_deposit:.4f}")
            
            # Record current values
            original_balance = user.balance
            original_initial = user.initial_deposit
            
            # Add a small test deposit
            test_amount = 0.1
            print(f"\nAdding test deposit of {test_amount} SOL...")
            
            success = process_auto_deposit(user.id, test_amount, "existing_user_test_tx")
            
            if not success:
                print("❌ Test deposit failed")
                return False
            
            # Refresh and check
            db.session.refresh(user)
            
            expected_balance = original_balance + test_amount
            expected_initial = original_initial + test_amount
            
            print(f"After deposit: Balance={user.balance:.4f}, Initial={user.initial_deposit:.4f}")
            print(f"Expected:      Balance={expected_balance:.4f}, Initial={expected_initial:.4f}")
            
            balance_increase = user.balance - original_balance
            initial_increase = user.initial_deposit - original_initial
            
            print(f"Balance increased by: {balance_increase:.4f} SOL")
            print(f"Initial increased by: {initial_increase:.4f} SOL")
            
            if abs(balance_increase - test_amount) < 0.001 and abs(initial_increase - test_amount) < 0.001:
                print("✅ Existing user deposit behavior working correctly")
                return True
            else:
                print("❌ Existing user deposit behavior failed")
                return False
                
        except Exception as e:
            logger.error(f"Existing user test failed: {e}")
            return False

def main():
    """Run all tests"""
    print("Starting Comprehensive Deposit Behavior Verification\n")
    
    # Test 1: Fresh user with multiple deposits
    test1_passed = run_comprehensive_deposit_test()
    
    # Test 2: Existing user behavior
    test2_passed = test_existing_user_behavior()
    
    print("\n" + "="*60)
    print("FINAL TEST RESULTS")
    print("="*60)
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Cumulative initial deposit behavior is working correctly")
        print("✅ Each deposit increases both balance and initial deposit")
        print("✅ System maintains accurate running totals")
    else:
        print("❌ SOME TESTS FAILED")
        if not test1_passed:
            print("❌ Fresh user test failed")
        if not test2_passed:
            print("❌ Existing user test failed")
    
    print("="*60)
    return test1_passed and test2_passed

if __name__ == "__main__":
    main()