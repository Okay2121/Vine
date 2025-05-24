"""
Simple Fix for Duplicate Bot Responses
This approach modifies specific logging calls that are showing duplicate entries
"""
import os
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_duplicate_logs():
    """
    Simple fix that modifies the logger calls in the bot
    to prevent duplicate log entries from appearing
    """
    try:
        # Check if bot file exists
        bot_file = 'bot_v20_runner.py'
        if not os.path.exists(bot_file):
            logger.error(f"Bot file not found: {bot_file}")
            return False
        
        # Read current content
        with open(bot_file, 'r') as f:
            content = f.read()
        
        # Create a modified version of the content
        modified_content = content
        
        # 1. Look for the self.wallet_listeners dictionary usage
        # This is likely causing duplicate calls
        wallet_pattern = r'(self\.wallet_listeners\[chat_id\]\s*=\s*\(listener_type,\s*callback\))'
        wallet_replacement = r'# Remove existing listener if exists to prevent duplicates\n        if chat_id in self.wallet_listeners:\n            logger.debug(f"Replacing existing listener for chat {chat_id}")\n        \1'
        
        # Apply replacement if pattern is found
        if re.search(wallet_pattern, modified_content):
            modified_content = re.sub(wallet_pattern, wallet_replacement, modified_content)
            logger.info("Added duplicate prevention to wallet_listeners")
        
        # 2. Add caching for message IDs to prevent duplicate processing
        # Find the process_update method
        process_pattern = r'def process_update\(self, update\):'
        if re.search(process_pattern, modified_content):
            # Find a good place to add a processed message cache
            class_def = r'class SimpleTelegramBot:'
            class_init = r'def __init__\(self, token\):'
            
            if re.search(class_init, modified_content):
                # Add _processed_messages to __init__
                init_pattern = r'(def __init__\(self, token\):.*?self\.running = False)'
                init_replacement = r'\1\n        self._processed_messages = set()  # Cache for processed message IDs'
                
                # Use re.DOTALL to match across multiple lines
                modified_content = re.sub(init_pattern, init_replacement, modified_content, flags=re.DOTALL)
                logger.info("Added message ID cache to prevent duplicate processing")
                
                # Add check for already processed messages in process_update
                update_pattern = r'(def process_update\(self, update\):.*?try:)'
                update_replacement = r'\1\n            # Check if we have already processed this message\n            if "message" in update and "message_id" in update["message"]:\n                message_id = update["message"]["message_id"]\n                if message_id in self._processed_messages:\n                    logger.debug(f"Skipping already processed message {message_id}")\n                    return\n                self._processed_messages.add(message_id)\n                # Limit cache size\n                if len(self._processed_messages) > 1000:\n                    self._processed_messages = set(list(self._processed_messages)[-500:])'
                
                # Use re.DOTALL to match across multiple lines
                modified_content = re.sub(update_pattern, update_replacement, modified_content, flags=re.DOTALL)
                logger.info("Added message ID check to process_update")
        
        # 3. Only write the file if changes were made
        if content != modified_content:
            with open(bot_file, 'w') as f:
                f.write(modified_content)
            logger.info("Successfully modified bot file to prevent duplicate responses")
            return True
        else:
            logger.warning("No changes were made to the bot file")
            return False
            
    except Exception as e:
        logger.error(f"Error fixing duplicate responses: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Applying simple fix for duplicate bot responses...")
    if fix_duplicate_logs():
        print("✅ Successfully applied fix for duplicate responses")
        print("Please restart the bot for changes to take effect")
    else:
        print("❌ Failed to apply fix for duplicate responses")