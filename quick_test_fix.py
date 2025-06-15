#!/usr/bin/env python3
"""
Quick test to verify the View All Users fix
"""

import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fixed_handler():
    """Test the fixed admin_view_all_users_handler."""
    print("Testing fixed View All Users handler...")
    
    try:
        from bot_v20_runner import SimpleTelegramBot, admin_view_all_users_handler, _bot_instance
        from config import BOT_TOKEN, ADMIN_IDS
        
        # Create bot instance
        bot = SimpleTelegramBot(BOT_TOKEN)
        
        # Set the global bot instance
        import bot_v20_runner
        bot_v20_runner._bot_instance = bot
        
        # Test with admin ID
        if ADMIN_IDS:
            admin_id = ADMIN_IDS[0]
            mock_update = {
                'callback_query': {
                    'data': 'admin_view_all_users',
                    'from': {'id': admin_id}
                }
            }
            
            print(f"Testing with admin ID: {admin_id}")
            
            # Call the handler
            admin_view_all_users_handler(mock_update, admin_id)
            
            print("✅ Handler executed without bot instance errors")
            return True
        else:
            print("❌ No admin IDs configured")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_handler()
    print(f"Test result: {'PASS' if success else 'FAIL'}")