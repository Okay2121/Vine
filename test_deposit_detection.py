#!/usr/bin/env python3
"""
Deposit Detection System Diagnostic
===================================
Tests all components of the auto deposit detection system to identify issues.
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, SenderWallet, Transaction, SystemSettings
from utils.solana import monitor_admin_wallet_transactions, extract_transaction_details
from helpers import get_global_deposit_wallet
import requests
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_setup():
    """Test database connectivity and table setup."""
    logger.info("=== Testing Database Setup ===")
    
    with app.app_context():
        try:
            # Test basic queries
            user_count = User.query.count()
            wallet_count = SenderWallet.query.count()
            tx_count = Transaction.query.count()
            
            logger.info(f"Users: {user_count}")
            logger.info(f"Sender Wallets: {wallet_count}")
            logger.info(f"Transactions: {tx_count}")
            
            # Check deposit wallet setting
            deposit_wallet = get_global_deposit_wallet()
            logger.info(f"Global Deposit Wallet: {deposit_wallet}")
            
            return True
            
        except Exception as e:
            logger.error(f"Database setup test failed: {e}")
            return False

def test_sender_wallet_matching():
    """Test if users have registered sender wallets for matching."""
    logger.info("=== Testing Sender Wallet Matching ===")
    
    with app.app_context():
        try:
            sender_wallets = SenderWallet.query.all()
            logger.info(f"Found {len(sender_wallets)} registered sender wallets")
            
            for wallet in sender_wallets[:5]:  # Show first 5
                user = User.query.get(wallet.user_id)
                if user:
                    logger.info(f"  User {user.telegram_id}: {wallet.wallet_address}")
                else:
                    logger.warning(f"  Orphaned wallet: {wallet.wallet_address}")
            
            if len(sender_wallets) == 0:
                logger.warning("No sender wallets registered - deposits cannot be matched to users!")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Sender wallet test failed: {e}")
            return False

def test_admin_wallet_api():
    """Test Solana RPC API connection and admin wallet transaction fetching."""
    logger.info("=== Testing Admin Wallet API ===")
    
    try:
        from config import SOLANA_RPC_URL
        deposit_wallet = get_global_deposit_wallet()
        
        logger.info(f"Testing connection to: {SOLANA_RPC_URL}")
        logger.info(f"Checking transactions for wallet: {deposit_wallet}")
        
        # Test API connection
        headers = {"Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                deposit_wallet,
                {
                    "limit": 10,
                    "commitment": "confirmed"
                }
            ]
        }
        
        response = requests.post(SOLANA_RPC_URL, headers=headers, data=json.dumps(payload))
        result = response.json()
        
        logger.info(f"API Response Status: {response.status_code}")
        
        if 'result' in result:
            transactions = result['result']
            logger.info(f"Found {len(transactions)} transactions")
            
            for i, tx in enumerate(transactions[:3]):  # Show first 3
                signature = tx.get('signature', 'N/A')
                block_time = tx.get('blockTime', 'N/A')
                logger.info(f"  TX {i+1}: {signature[:16]}... at {block_time}")
                
            return True
        else:
            logger.error(f"API Error: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Admin wallet API test failed: {e}")
        return False

def test_transaction_processing():
    """Test transaction detail extraction and processing."""
    logger.info("=== Testing Transaction Processing ===")
    
    try:
        # Test the monitor function
        detected_deposits = monitor_admin_wallet_transactions()
        logger.info(f"Monitor detected {len(detected_deposits)} deposits")
        
        for deposit in detected_deposits:
            user_id, amount, signature = deposit
            logger.info(f"  Detected: User {user_id}, Amount {amount} SOL, TX {signature[:16]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Transaction processing test failed: {e}")
        return False

def test_duplicate_prevention():
    """Test if duplicate transaction prevention is working."""
    logger.info("=== Testing Duplicate Prevention ===")
    
    with app.app_context():
        try:
            # Check for recent transactions
            recent_txs = Transaction.query.filter_by(transaction_type='deposit').order_by(Transaction.id.desc()).limit(10).all()
            logger.info(f"Found {len(recent_txs)} recent deposit transactions")
            
            tx_hashes = set()
            duplicates = 0
            
            for tx in recent_txs:
                if tx.tx_hash in tx_hashes:
                    duplicates += 1
                    logger.warning(f"Duplicate transaction hash: {tx.tx_hash}")
                else:
                    tx_hashes.add(tx.tx_hash)
                    
            logger.info(f"Duplicate transactions found: {duplicates}")
            
            return duplicates == 0
            
        except Exception as e:
            logger.error(f"Duplicate prevention test failed: {e}")
            return False

def create_test_sender_wallet():
    """Create a test sender wallet for testing purposes."""
    logger.info("=== Creating Test Sender Wallet ===")
    
    with app.app_context():
        try:
            # Find a user without a sender wallet
            user = User.query.filter(~User.id.in_(
                db.session.query(SenderWallet.user_id)
            )).first()
            
            if not user:
                logger.warning("No users available for test sender wallet creation")
                return False
            
            # Create a test sender wallet
            test_wallet = SenderWallet(
                user_id=user.id,
                wallet_address="TestWallet123456789012345678901234567890",
                created_at=datetime.utcnow()
            )
            
            db.session.add(test_wallet)
            db.session.commit()
            
            logger.info(f"Created test sender wallet for user {user.telegram_id}: {test_wallet.wallet_address}")
            return True
            
        except Exception as e:
            logger.error(f"Test sender wallet creation failed: {e}")
            return False

def run_full_diagnostic():
    """Run complete diagnostic of the deposit detection system."""
    logger.info("Starting Deposit Detection System Diagnostic")
    logger.info("=" * 50)
    
    tests = [
        ("Database Setup", test_database_setup),
        ("Sender Wallet Matching", test_sender_wallet_matching), 
        ("Admin Wallet API", test_admin_wallet_api),
        ("Transaction Processing", test_transaction_processing),
        ("Duplicate Prevention", test_duplicate_prevention),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            status = "PASS" if result else "FAIL"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"{test_name}: FAIL - {e}")
        
        logger.info("-" * 30)
    
    # Summary
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 50)
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} {test_name}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed < total:
        logger.warning("Some tests failed - deposit detection may not work properly")
        
        # Suggest fixes
        if not results.get("Sender Wallet Matching"):
            logger.info("FIX: Users need to register sender wallets for deposit matching")
        
        if not results.get("Admin Wallet API"):
            logger.info("FIX: Check Solana RPC URL and network connectivity")
            
    else:
        logger.info("All tests passed - deposit detection system appears functional")

if __name__ == "__main__":
    run_full_diagnostic()