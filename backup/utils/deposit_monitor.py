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
    Scan for new deposits by checking all registered sender wallets.
    This function checks if transactions from registered sender wallets
    to the global deposit address have occurred.
    """
    logger.info("Starting deposit scan cycle")
    deposits_found = 0
    
    with app.app_context():
        try:
            # Get all registered sender wallets
            sender_wallets = SenderWallet.query.all()
            logger.info(f"Checking {len(sender_wallets)} registered sender wallets for deposits")
            
            for wallet in sender_wallets:
                # Get user information
                user = User.query.get(wallet.user_id)
                if not user:
                    logger.warning(f"User {wallet.user_id} not found for wallet {wallet.wallet_address}")
                    continue
                
                # Check for deposits from this wallet to the global address
                deposit_found, amount, tx_signature = check_deposit_by_sender(wallet.wallet_address)
                
                if deposit_found:
                    logger.info(f"Deposit detected: {amount} SOL from {wallet.wallet_address} for user {user.telegram_id}")
                    
                    # Process the deposit
                    success = process_auto_deposit(user.id, amount, tx_signature)
                    
                    if success:
                        # Update the last used timestamp
                        wallet.last_used = datetime.utcnow()
                        db.session.commit()
                        deposits_found += 1
                        
                        logger.info(f"Auto-deposit of {amount} SOL processed for user {user.telegram_id}")
                        
                        # TODO: Send notification to user (implement in future version)
                    else:
                        logger.error(f"Failed to process deposit for user {user.telegram_id}")
            
            logger.info(f"Deposit scan cycle completed. Found and processed {deposits_found} deposits")
            
        except Exception as e:
            logger.error(f"Error during deposit scan: {str(e)}")
            db.session.rollback()


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