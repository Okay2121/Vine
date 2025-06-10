"""
Test and Debug Script for the New Deposit Detection System
==========================================================
This script tests the improved deposit detection system that monitors
the admin's global wallet for incoming transactions instead of checking user balances.
"""

import logging
import sys
from datetime import datetime, timedelta
from app import app, db
from models import User, SenderWallet, Transaction
from utils.solana import monitor_admin_wallet_transactions, process_auto_deposit
from config import GLOBAL_DEPOSIT_WALLET, MIN_DEPOSIT

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_admin_wallet_monitoring():
    """Test the admin wallet monitoring function."""
    logger.info("Testing admin wallet monitoring system...")
    
    with app.app_context():
        try:
            # Test the monitoring function
            detected_deposits = monitor_admin_wallet_transactions()
            
            logger.info(f"Admin wallet monitoring test completed")
            logger.info(f"Detected deposits: {len(detected_deposits)}")
            
            for i, (user_id, amount, tx_signature) in enumerate(detected_deposits):
                logger.info(f"Deposit {i+1}: User {user_id}, Amount: {amount} SOL, TX: {tx_signature[:16]}...")
                
            return detected_deposits
            
        except Exception as e:
            logger.error(f"Error testing admin wallet monitoring: {str(e)}")
            return []

def test_deposit_processing():
    """Test the complete deposit processing pipeline."""
    logger.info("Testing complete deposit processing pipeline...")
    
    with app.app_context():
        try:
            # Get detected deposits
            detected_deposits = monitor_admin_wallet_transactions()
            
            if not detected_deposits:
                logger.info("No deposits detected to process")
                return
            
            # Process the first detected deposit
            user_id, amount, tx_signature = detected_deposits[0]
            
            logger.info(f"Testing processing of deposit: {amount} SOL for user {user_id}")
            
            # Get user information before processing
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return
            
            initial_balance = user.balance
            logger.info(f"User {user.telegram_id} initial balance: {initial_balance} SOL")
            
            # Process the deposit
            success = process_auto_deposit(user_id, amount, tx_signature)
            
            if success:
                # Check the updated balance
                updated_user = User.query.get(user_id)
                new_balance = updated_user.balance
                
                logger.info(f"Deposit processed successfully!")
                logger.info(f"Previous balance: {initial_balance} SOL")
                logger.info(f"New balance: {new_balance} SOL")
                logger.info(f"Difference: {new_balance - initial_balance} SOL")
                
                # Check transaction record
                transaction = Transaction.query.filter_by(tx_hash=tx_signature).first()
                if transaction:
                    logger.info(f"Transaction record created: {transaction.transaction_type}, {transaction.amount} SOL")
                else:
                    logger.warning("No transaction record found!")
            else:
                logger.error("Failed to process deposit")
                
        except Exception as e:
            logger.error(f"Error testing deposit processing: {str(e)}")

def check_system_status():
    """Check the current status of the deposit detection system."""
    logger.info("Checking deposit detection system status...")
    
    with app.app_context():
        try:
            # Check database connectivity
            user_count = User.query.count()
            wallet_count = SenderWallet.query.count()
            transaction_count = Transaction.query.count()
            
            logger.info(f"Database status:")
            logger.info(f"  Users: {user_count}")
            logger.info(f"  Sender wallets: {wallet_count}")
            logger.info(f"  Transactions: {transaction_count}")
            
            # Check recent transactions
            recent_transactions = Transaction.query.filter(
                Transaction.timestamp > datetime.utcnow() - timedelta(hours=24)
            ).order_by(Transaction.timestamp.desc()).limit(5).all()
            
            logger.info(f"Recent transactions (last 24 hours): {len(recent_transactions)}")
            for tx in recent_transactions:
                logger.info(f"  {tx.timestamp}: {tx.transaction_type} {tx.amount} SOL (User {tx.user_id})")
            
            # Check configuration
            logger.info(f"Configuration:")
            logger.info(f"  Global deposit wallet: {GLOBAL_DEPOSIT_WALLET}")
            logger.info(f"  Minimum deposit: {MIN_DEPOSIT} SOL")
            
        except Exception as e:
            logger.error(f"Error checking system status: {str(e)}")

def simulate_deposit_test():
    """Create a test scenario to verify the system works."""
    logger.info("Running simulation test...")
    
    with app.app_context():
        try:
            # Find a test user or create one
            test_user = User.query.filter_by(username="testuser").first()
            if not test_user:
                logger.info("Creating test user...")
                test_user = User()
                test_user.username = "testuser"
                test_user.telegram_id = "999999999"
                test_user.balance = 0.0
                test_user.initial_deposit = 0.0
                db.session.add(test_user)
                db.session.commit()
                logger.info(f"Created test user with ID: {test_user.id}")
            
            # Create a test sender wallet if it doesn't exist
            test_wallet_address = "TestWallet123456789ABC"
            sender_wallet = SenderWallet.query.filter_by(wallet_address=test_wallet_address).first()
            if not sender_wallet:
                logger.info("Creating test sender wallet...")
                sender_wallet = SenderWallet()
                sender_wallet.user_id = test_user.id
                sender_wallet.wallet_address = test_wallet_address
                sender_wallet.created_at = datetime.utcnow()
                sender_wallet.last_used = datetime.utcnow()
                sender_wallet.is_primary = True
                db.session.add(sender_wallet)
                db.session.commit()
                logger.info(f"Created test sender wallet: {test_wallet_address}")
            
            logger.info("Test setup completed")
            logger.info(f"Test user ID: {test_user.id}")
            logger.info(f"Test wallet: {test_wallet_address}")
            
        except Exception as e:
            logger.error(f"Error setting up simulation test: {str(e)}")

def main():
    """Main function to run all tests."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "all"
    
    logger.info(f"Starting deposit system test: {test_type}")
    
    if test_type in ["all", "status"]:
        check_system_status()
        print("-" * 50)
    
    if test_type in ["all", "monitor"]:
        test_admin_wallet_monitoring()
        print("-" * 50)
    
    if test_type in ["all", "process"]:
        test_deposit_processing()
        print("-" * 50)
    
    if test_type in ["all", "simulate"]:
        simulate_deposit_test()
        print("-" * 50)
    
    logger.info("Test completed")

if __name__ == "__main__":
    main()