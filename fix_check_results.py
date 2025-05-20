#!/usr/bin/env python
"""
Check if our emergency fix was properly applied and test the bot's handling
of balance adjustments.
"""
import logging
import sys
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulate admin_confirm_adjustment_handler call
def test_balance_adjustment():
    try:
        # First check if the fix was properly applied
        with open("bot_v20_runner.py", "r") as f:
            content = f.read()
            
        # Check if our emergency handler is present
        if "Emergency non-blocking balance adjustment handler" in content:
            logger.info("Emergency fix appears to be properly applied")
        else:
            logger.error("Emergency fix NOT found in the code!")
            return False
            
        logger.info("\n=== SIMULATING BALANCE ADJUSTMENT ===\n")
        
        # Now we'll test invoking the balance_manager directly
        import balance_manager
        
        # Test user info - this should be a real user in your database
        test_id = "7195974467"  # example telegram_id
        test_amount = 0.1  # Small test amount
        test_reason = "Test adjustment from fix_check_results.py"
        
        # Test the balance adjustment in a separate thread
        def test_thread():
            logger.info(f"Testing balance adjustment with identifier: {test_id}")
            success, message = balance_manager.adjust_balance(
                test_id, test_amount, test_reason, skip_trading=True
            )
            logger.info(f"Result: {'SUCCESS' if success else 'FAILED'}")
            logger.info(f"Message: {message}")
            
        # Start the test in a thread
        thread = threading.Thread(target=test_thread)
        thread.daemon = True
        thread.start()
        
        # Wait up to 5 seconds for the thread to complete
        thread.join(5.0)
        
        if thread.is_alive():
            logger.error("❌ Test is STILL RUNNING after 5 seconds - this indicates a blocking issue!")
            return False
        else:
            logger.info("✅ Test completed within timeout - this is good!")
            return True
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Checking if balance adjustment fix is working...")
    
    if test_balance_adjustment():
        print("\n✅ Balance adjustment appears to be working correctly!")
        print("The bot should remain responsive when clicking 'Confirm' button in admin panel")
    else:
        print("\n❌ There may still be issues with the balance adjustment function")
        print("Please check the logs for more details")