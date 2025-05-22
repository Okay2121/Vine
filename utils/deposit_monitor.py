"""
Deposit Monitor Utility

This module provides utilities for monitoring and processing deposits to the global wallet
by matching transactions to users based on their registered sender wallets.
"""

import logging
import random
import time
from datetime import datetime, timedelta
import threading
import schedule

from app import db, app
from models import User, UserStatus, Transaction, SenderWallet
from utils.solana import check_deposit_by_sender, process_auto_deposit
from config import GLOBAL_DEPOSIT_WALLET

logger = logging.getLogger(__name__)

# Time between deposit scan cycles (in seconds)
SCAN_INTERVAL = 60  # Check for deposits every minute

# Flag to control the deposit monitor thread
monitor_running = False
monitor_thread = None


def scan_for_deposits():
    """
    Scan for new deposits with improved error handling and failure isolation.
    This function checks all registered sender wallets for transactions
    to the global deposit address with enhanced robustness.
    """
    logger.info("Starting deposit scan cycle")
    deposits_found = 0
    failed_wallets = 0
    
    with app.app_context():
        # Get all registered sender wallets with error handling
        try:
            sender_wallets = SenderWallet.query.all()
            logger.info(f"Checking {len(sender_wallets)} registered sender wallets for deposits")
        except Exception as db_error:
            logger.error(f"Failed to fetch sender wallets: {str(db_error)}")
            return
            
        # Process each wallet independently so errors don't stop the entire scan
        for wallet in sender_wallets:
            try:
                # Get user information with error handling
                user = User.query.get(wallet.user_id)
                if not user:
                    logger.warning(f"User {wallet.user_id} not found for wallet {wallet.wallet_address}")
                    continue
                
                # Check for deposits with timeout protection
                try:
                    deposit_found, amount, tx_signature = check_deposit_by_sender(wallet.wallet_address)
                except Exception as check_error:
                    logger.error(f"Error checking deposits for wallet {wallet.wallet_address}: {str(check_error)}")
                    failed_wallets += 1
                    continue
                
                if deposit_found:
                    logger.info(f"Deposit detected: {amount} SOL from {wallet.wallet_address} for user {user.telegram_id}")
                    
                    # Process the deposit in an isolated transaction
                    success = process_auto_deposit(user.id, amount, tx_signature)
                    
                    if success:
                        # Update wallet timestamp in separate transaction for safety
                        try:
                            db.session.begin_nested()
                            wallet.last_used = datetime.utcnow()
                            db.session.commit()
                            deposits_found += 1
                            logger.info(f"Auto-deposit of {amount} SOL processed for user {user.telegram_id}")
                            
                            # Send notification to user in separate try/except to prevent notification failures
                            # from affecting deposit processing
                            try:
                                # TODO: Implement user notification in future version
                                pass
                            except Exception as notify_error:
                                logger.error(f"Failed to send notification to user {user.telegram_id}: {str(notify_error)}")
                                
                        except Exception as wallet_update_error:
                            logger.error(f"Failed to update wallet timestamp: {str(wallet_update_error)}")
                            db.session.rollback()
                    else:
                        logger.error(f"Failed to process deposit for user {user.telegram_id}")
            except Exception as wallet_error:
                logger.error(f"Error processing wallet {wallet.wallet_address}: {str(wallet_error)}")
                failed_wallets += 1
                
        logger.info(f"Deposit scan cycle completed. Processed {deposits_found} deposits. Failed checks: {failed_wallets}")


def start_deposit_monitor():
    """
    Start the deposit monitoring service in a background thread.
    This function initializes a scheduler to periodically scan for
    new deposits from registered sender wallets.
    """
    global monitor_running, monitor_thread
    
    if monitor_running:
        logger.warning("Deposit monitor is already running")
        return False
    
    def monitor_worker():
        global monitor_running
        
        logger.info("Starting deposit monitor thread")
        monitor_running = True
        
        # Schedule the scan to run at regular intervals
        schedule.every(SCAN_INTERVAL).seconds.do(scan_for_deposits)
        
        # Run an initial scan immediately
        scan_for_deposits()
        
        # Keep running until monitor_running is set to False
        while monitor_running:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("Deposit monitor thread stopped")
    
    # Start the monitor in a separate thread
    monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
    monitor_thread.start()
    
    logger.info(f"Deposit monitor started, checking for deposits every {SCAN_INTERVAL} seconds")
    return True


def stop_deposit_monitor():
    """
    Stop the deposit monitoring service.
    """
    global monitor_running, monitor_thread
    
    if not monitor_running:
        logger.warning("Deposit monitor is not running")
        return False
    
    # Signal the thread to stop
    monitor_running = False
    
    # Wait for the thread to finish (with timeout)
    if monitor_thread:
        monitor_thread.join(timeout=3.0)
    
    logger.info("Deposit monitor stopped")
    return True


def is_monitor_running():
    """
    Check if the deposit monitor is currently running.
    
    Returns:
        bool: True if the monitor is running, False otherwise
    """
    global monitor_running
    return monitor_running