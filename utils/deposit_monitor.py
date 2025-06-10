"""
Deposit Monitor Utility

This module provides utilities for monitoring and processing deposits to the global wallet
by matching transactions to users based on their registered sender wallets.
Enhanced with robust error handling for database connectivity issues.
"""

import logging
import random
import time
from datetime import datetime, timedelta
import threading
import schedule

from app import db, app, retry_database_operation
from models import User, UserStatus, Transaction, SenderWallet
from utils.solana import check_deposit_by_sender, process_auto_deposit
from config import GLOBAL_DEPOSIT_WALLET
from sqlalchemy.exc import OperationalError, DisconnectionError

logger = logging.getLogger(__name__)

# Time between deposit scan cycles (in seconds)
SCAN_INTERVAL = 60  # Check for deposits every minute

# Flag to control the deposit monitor thread
monitor_running = False
monitor_thread = None


def scan_for_deposits():
    """
    Scan for new deposits by monitoring the admin's global wallet for incoming transactions.
    This improved system tracks received amounts rather than user wallet balances.
    Enhanced with robust database error handling.
    """
    logger.info("Starting deposit scan cycle - monitoring admin wallet for incoming transactions")
    deposits_found = 0
    
    def perform_deposit_scan():
        nonlocal deposits_found
        
        with app.app_context():
            try:
                # Import the new admin wallet monitoring function
                from utils.solana import monitor_admin_wallet_transactions, process_auto_deposit
                
                # Monitor admin wallet for all incoming transactions
                detected_deposits = monitor_admin_wallet_transactions()
                
                # Process each detected deposit with database retry logic
                for user_id, amount, tx_signature in detected_deposits:
                    try:
                        logger.info(f"Processing deposit: {amount} SOL for user {user_id}")
                        
                        # Get user information with retry
                        def get_user():
                            return User.query.get(user_id)
                        
                        user = retry_database_operation(get_user, max_retries=2, delay=1)
                        if not user:
                            logger.warning(f"User {user_id} not found for deposit processing")
                            continue
                        
                        # Process the deposit with retry logic
                        def process_deposit():
                            return process_auto_deposit(user_id, amount, tx_signature)
                        
                        success = retry_database_operation(process_deposit, max_retries=3, delay=2)
                        
                        if success:
                            deposits_found += 1
                            logger.info(f"Auto-deposit of {amount} SOL processed for user {user.telegram_id}")
                            
                            # Update the sender wallet's last_used timestamp with retry
                            try:
                                def update_wallet_timestamp():
                                    sender_wallet = SenderWallet.query.filter_by(user_id=user_id).first()
                                    if sender_wallet:
                                        sender_wallet.last_used = datetime.utcnow()
                                        db.session.commit()
                                        return True
                                    return False
                                
                                retry_database_operation(update_wallet_timestamp, max_retries=2, delay=1)
                                
                            except Exception as wallet_update_error:
                                logger.error(f"Failed to update wallet timestamp after retries: {str(wallet_update_error)}")
                            
                            # Send notification to user (optional)
                            try:

                                pass
                            except Exception as notify_error:
                                logger.error(f"Failed to send notification to user {user.telegram_id}: {str(notify_error)}")
                        else:
                            logger.error(f"Failed to process deposit for user {user.telegram_id} after retries")
                            
                    except (OperationalError, DisconnectionError) as db_error:
                        logger.error(f"Database connection error while processing deposit for user {user_id}: {str(db_error)}")
                        # Continue with next deposit instead of failing entire scan
                        continue
                    except Exception as deposit_error:
                        logger.error(f"Error processing deposit for user {user_id}: {str(deposit_error)}")
                        continue
                        
            except Exception as scan_error:
                logger.error(f"Error during deposit scan: {str(scan_error)}")
                raise scan_error
    
    try:
        # Execute deposit scan with retry logic for database operations
        retry_database_operation(perform_deposit_scan, max_retries=2, delay=5)
    except Exception as final_error:
        logger.error(f"Deposit scan failed after all retries: {str(final_error)}")
        # Don't crash the monitoring thread, just log and continue
    
    logger.info(f"Deposit scan cycle completed. Processed {deposits_found} deposits from admin wallet monitoring")


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