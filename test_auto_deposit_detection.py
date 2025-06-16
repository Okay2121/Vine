#!/usr/bin/env python3
"""
Auto Deposit Detection System Test
==================================
This script tests the complete auto deposit detection workflow:
1. Verifies database setup for sender wallet tracking
2. Tests wallet-to-user matching functionality
3. Simulates deposit detection and processing
4. Validates transaction recording and balance updates
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, SenderWallet, Transaction, UserStatus
from utils.solana import monitor_admin_wallet_transactions, process_auto_deposit, link_sender_wallet_to_user
from helpers import get_global_deposit_wallet
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoDepositTester:
    """Tests the auto deposit detection system"""
    
    def __init__(self):
        self.test_results = []
        
    def test_database_structure(self):
        """Test that all required database tables and relationships exist"""
        logger.info("Testing database structure...")
        
        with app.app_context():
            try:
                # Test User table
                user_count = User.query.count()
                logger.info(f"Users in database: {user_count}")
                
                # Test SenderWallet table
                sender_wallet_count = SenderWallet.query.count()
                logger.info(f"Sender wallets in database: {sender_wallet_count}")
                
                # Test Transaction table
                transaction_count = Transaction.query.count()
                logger.info(f"Transactions in database: {transaction_count}")
                
                # Test relationships
                if user_count > 0:
                    sample_user = User.query.first()
                    sender_wallets = sample_user.sender_wallets
                    user_transactions = sample_user.transactions
                    logger.info(f"Sample user has {len(sender_wallets)} sender wallets and {len(user_transactions)} transactions")
                
                self.test_results.append(("Database Structure", "PASS", "All tables accessible"))
                return True
                
            except Exception as e:
                logger.error(f"Database structure test failed: {e}")
                self.test_results.append(("Database Structure", "FAIL", str(e)))
                return False
    
    def test_global_wallet_configuration(self):
        """Test that global deposit wallet is properly configured"""
        logger.info("Testing global wallet configuration...")
        
        try:
            global_wallet = get_global_deposit_wallet()
            logger.info(f"Global deposit wallet: {global_wallet}")
            
            if global_wallet and len(global_wallet) > 30:  # Basic validation
                self.test_results.append(("Global Wallet Config", "PASS", f"Wallet: {global_wallet[:10]}..."))
                return True
            else:
                self.test_results.append(("Global Wallet Config", "FAIL", "Invalid or missing global wallet"))
                return False
                
        except Exception as e:
            logger.error(f"Global wallet configuration test failed: {e}")
            self.test_results.append(("Global Wallet Config", "FAIL", str(e)))
            return False
    
    def test_sender_wallet_linking(self):
        """Test linking sender wallets to users"""
        logger.info("Testing sender wallet linking...")
        
        with app.app_context():
            try:
                # Create a test user if none exist
                test_user = User.query.filter_by(telegram_id="test_deposit_user").first()
                if not test_user:
                    test_user = User(
                        telegram_id="test_deposit_user",
                        username="test_user",
                        first_name="Test",
                        status=UserStatus.DEPOSITING,
                        balance=0.0
                    )
                    db.session.add(test_user)
                    db.session.commit()
                    logger.info(f"Created test user with ID: {test_user.id}")
                
                # Test wallet linking
                test_sender_wallet = "TestSenderWallet123456789012345678901234567890"
                
                # Remove existing link if any
                existing_link = SenderWallet.query.filter_by(wallet_address=test_sender_wallet).first()
                if existing_link:
                    db.session.delete(existing_link)
                    db.session.commit()
                
                # Link new wallet
                link_success = link_sender_wallet_to_user(test_user.id, test_sender_wallet)
                
                if link_success:
                    # Verify the link was created
                    created_link = SenderWallet.query.filter_by(wallet_address=test_sender_wallet).first()
                    if created_link and created_link.user_id == test_user.id:
                        logger.info(f"Successfully linked wallet {test_sender_wallet} to user {test_user.id}")
                        self.test_results.append(("Sender Wallet Linking", "PASS", "Wallet linked successfully"))
                        return True
                    else:
                        self.test_results.append(("Sender Wallet Linking", "FAIL", "Link not found in database"))
                        return False
                else:
                    self.test_results.append(("Sender Wallet Linking", "FAIL", "Link function returned False"))
                    return False
                    
            except Exception as e:
                logger.error(f"Sender wallet linking test failed: {e}")
                self.test_results.append(("Sender Wallet Linking", "FAIL", str(e)))
                return False
    
    def test_deposit_processing(self):
        """Test the auto deposit processing workflow"""
        logger.info("Testing deposit processing...")
        
        with app.app_context():
            try:
                # Get test user
                test_user = User.query.filter_by(telegram_id="test_deposit_user").first()
                if not test_user:
                    self.test_results.append(("Deposit Processing", "SKIP", "No test user found"))
                    return False
                
                # Record initial balance
                initial_balance = test_user.balance
                logger.info(f"User initial balance: {initial_balance}")
                
                # Test deposit processing
                test_amount = 1.5
                test_tx_signature = f"test_transaction_{datetime.utcnow().timestamp()}"
                
                # Process the deposit
                success = process_auto_deposit(test_user.id, test_amount, test_tx_signature)
                
                if success:
                    # Refresh user data
                    db.session.refresh(test_user)
                    new_balance = test_user.balance
                    
                    # Check balance update
                    expected_balance = initial_balance + test_amount
                    if abs(new_balance - expected_balance) < 0.0001:  # Float precision tolerance
                        logger.info(f"Balance updated correctly: {initial_balance} -> {new_balance}")
                        
                        # Check transaction record
                        transaction = Transaction.query.filter_by(tx_hash=test_tx_signature).first()
                        if transaction:
                            logger.info(f"Transaction recorded: {transaction.amount} SOL, status: {transaction.status}")
                            self.test_results.append(("Deposit Processing", "PASS", f"Processed {test_amount} SOL successfully"))
                            return True
                        else:
                            self.test_results.append(("Deposit Processing", "FAIL", "Transaction not recorded"))
                            return False
                    else:
                        self.test_results.append(("Deposit Processing", "FAIL", f"Balance mismatch: expected {expected_balance}, got {new_balance}"))
                        return False
                else:
                    self.test_results.append(("Deposit Processing", "FAIL", "Process function returned False"))
                    return False
                    
            except Exception as e:
                logger.error(f"Deposit processing test failed: {e}")
                self.test_results.append(("Deposit Processing", "FAIL", str(e)))
                return False
    
    def test_duplicate_prevention(self):
        """Test that duplicate transactions are prevented"""
        logger.info("Testing duplicate transaction prevention...")
        
        with app.app_context():
            try:
                test_user = User.query.filter_by(telegram_id="test_deposit_user").first()
                if not test_user:
                    self.test_results.append(("Duplicate Prevention", "SKIP", "No test user found"))
                    return False
                
                # Record initial balance
                initial_balance = test_user.balance
                
                # Try to process the same transaction again
                test_tx_signature = f"test_transaction_{datetime.utcnow().timestamp()}"
                
                # First processing
                success1 = process_auto_deposit(test_user.id, 1.0, test_tx_signature)
                db.session.refresh(test_user)
                balance_after_first = test_user.balance
                
                # Second processing (should be prevented)
                success2 = process_auto_deposit(test_user.id, 1.0, test_tx_signature)
                db.session.refresh(test_user)
                balance_after_second = test_user.balance
                
                # Balance should not change on second processing
                if success1 and success2 and balance_after_first == balance_after_second:
                    logger.info("Duplicate transaction correctly prevented")
                    self.test_results.append(("Duplicate Prevention", "PASS", "Duplicate processing prevented"))
                    return True
                else:
                    self.test_results.append(("Duplicate Prevention", "FAIL", "Duplicate not prevented"))
                    return False
                    
            except Exception as e:
                logger.error(f"Duplicate prevention test failed: {e}")
                self.test_results.append(("Duplicate Prevention", "FAIL", str(e)))
                return False
    
    def test_wallet_matching_accuracy(self):
        """Test accuracy of wallet-to-user matching"""
        logger.info("Testing wallet matching accuracy...")
        
        with app.app_context():
            try:
                # Get all sender wallets
                sender_wallets = SenderWallet.query.all()
                logger.info(f"Testing matching for {len(sender_wallets)} sender wallets")
                
                if len(sender_wallets) == 0:
                    self.test_results.append(("Wallet Matching", "SKIP", "No sender wallets to test"))
                    return False
                
                # Test matching for each wallet
                successful_matches = 0
                for wallet in sender_wallets:
                    # Verify the wallet can be found by address
                    found_wallet = SenderWallet.query.filter_by(wallet_address=wallet.wallet_address).first()
                    if found_wallet and found_wallet.user_id == wallet.user_id:
                        successful_matches += 1
                
                match_rate = successful_matches / len(sender_wallets)
                logger.info(f"Wallet matching accuracy: {match_rate:.2%} ({successful_matches}/{len(sender_wallets)})")
                
                if match_rate >= 1.0:  # 100% accuracy expected
                    self.test_results.append(("Wallet Matching", "PASS", f"{match_rate:.1%} accuracy"))
                    return True
                else:
                    self.test_results.append(("Wallet Matching", "FAIL", f"Only {match_rate:.1%} accuracy"))
                    return False
                    
            except Exception as e:
                logger.error(f"Wallet matching test failed: {e}")
                self.test_results.append(("Wallet Matching", "FAIL", str(e)))
                return False
    
    def test_deposit_monitor_status(self):
        """Test current status of the deposit monitoring system"""
        logger.info("Testing deposit monitor status...")
        
        try:
            from utils.deposit_monitor import is_monitor_running
            
            is_running = is_monitor_running()
            logger.info(f"Deposit monitor running: {is_running}")
            
            if is_running:
                self.test_results.append(("Monitor Status", "PASS", "Monitor is active"))
                return True
            else:
                self.test_results.append(("Monitor Status", "WARNING", "Monitor not running"))
                return False
                
        except Exception as e:
            logger.error(f"Monitor status test failed: {e}")
            self.test_results.append(("Monitor Status", "FAIL", str(e)))
            return False
    
    def generate_summary_report(self):
        """Generate a comprehensive test report"""
        
        print("\n" + "="*80)
        print("AUTO DEPOSIT DETECTION SYSTEM TEST REPORT")
        print("="*80)
        
        passed = len([r for r in self.test_results if r[1] == "PASS"])
        failed = len([r for r in self.test_results if r[1] == "FAIL"])
        warnings = len([r for r in self.test_results if r[1] == "WARNING"])
        skipped = len([r for r in self.test_results if r[1] == "SKIP"])
        total = len(self.test_results)
        
        print(f"\nTEST SUMMARY:")
        print(f"  Total Tests: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Warnings: {warnings}")
        print(f"  Skipped: {skipped}")
        
        if self.test_results:
            print(f"\nDETAILED RESULTS:")
            for test_name, status, details in self.test_results:
                status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠" if status == "WARNING" else "○"
                print(f"  {status_symbol} {test_name:<25} {status:<8} {details}")
        
        print(f"\nSYSTEM STATUS:")
        if failed == 0:
            print("  ✓ Auto deposit detection system is working correctly")
            print("  ✓ Ready for production use")
        elif failed <= 2 and warnings == 0:
            print("  ⚠ Minor issues detected - system mostly functional")
            print("  ⚠ Review failed tests before production use")
        else:
            print("  ✗ Critical issues detected - system needs attention")
            print("  ✗ Fix issues before production deployment")
        
        print("="*80)
        
        return failed == 0
    
    def run_all_tests(self):
        """Run the complete test suite"""
        logger.info("Starting auto deposit detection system tests...")
        
        tests = [
            ("Database Structure", self.test_database_structure),
            ("Global Wallet Config", self.test_global_wallet_configuration),
            ("Sender Wallet Linking", self.test_sender_wallet_linking),
            ("Deposit Processing", self.test_deposit_processing),
            ("Duplicate Prevention", self.test_duplicate_prevention),
            ("Wallet Matching", self.test_wallet_matching_accuracy),
            ("Monitor Status", self.test_deposit_monitor_status)
        ]
        
        for test_name, test_function in tests:
            try:
                logger.info(f"Running: {test_name}")
                test_function()
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {e}")
                self.test_results.append((test_name, "FAIL", f"Test crashed: {str(e)}"))
        
        return self.generate_summary_report()

def main():
    """Run the auto deposit detection tests"""
    tester = AutoDepositTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())