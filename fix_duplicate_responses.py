"""
Fix Duplicate Response Issue in Bot Handlers
This script helps identify and fix the duplicate response issue
seen in the bot logs where multiple listeners are being added
"""

import logging
import re
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_duplicate_listeners():
    """Fix duplicate listeners in bot_v20_runner.py"""
    try:
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
            
        # Read the file content
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
            
        # Find patterns that add listeners
        listener_pattern = r'(text_listeners\[chat_id\].append\(callback\))'
        
        # Count instances
        listener_matches = re.findall(listener_pattern, content)
        logger.info(f"Found {len(listener_matches)} instances of listener addition")
        
        # Check for duplicate listener issues
        check_pattern = r'if\s+chat_id\s+not\s+in\s+text_listeners:'
        has_check = re.search(check_pattern, content) is not None
        
        if not has_check:
            logger.info("Adding check to prevent duplicate listeners")
            
            # Find a good place to add the check
            target_pattern = r'(def\s+add_text_listener\(chat_id,\s*callback\):)'
            
            if re.search(target_pattern, content):
                # Add the check for existing listeners
                fixed_code = re.sub(
                    target_pattern,
                    r'\1\n    # Remove existing listener if any\n    if chat_id in text_listeners:\n        logger.info(f"Removing existing listener for chat {chat_id} before adding new one")\n        text_listeners[chat_id] = []',
                    content
                )
                
                # Write the updated content
                with open('bot_v20_runner.py', 'w') as file:
                    file.write(fixed_code)
                    
                logger.info("Successfully added check for duplicate listeners")
                return True
            else:
                logger.error("Could not find add_text_listener function")
                return False
        else:
            logger.info("Duplicate listener check already exists")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing duplicate listeners: {e}")
        return False

if __name__ == "__main__":
    print("Fixing duplicate response issue...")
    
    if fix_duplicate_listeners():
        print("✅ Successfully fixed duplicate listener issue")
    else:
        print("❌ Failed to fix duplicate listener issue")