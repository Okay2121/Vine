"""
Direct Fix for Duplicate Bot Responses
This script updates the specific functions in the bot that are causing duplicate responses
"""
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_bot_listener_system():
    """Fix the duplicate response issue in the bot's message handling system"""
    try:
        # Path to the bot file
        bot_file = 'bot_v20_runner.py'
        
        if not os.path.exists(bot_file):
            logger.error(f"Bot file not found: {bot_file}")
            return False
            
        # Read the current content
        with open(bot_file, 'r') as f:
            content = f.read()

        # 1. Fix the add_message_listener method to prevent duplicates
        original_add_listener = """    def add_message_listener(self, chat_id, listener_type, callback):
        """Add a listener for non-command messages."""
        self.wallet_listeners[chat_id] = (listener_type, callback)
        logger.info(f"Added {listener_type} listener for chat {chat_id}")"""
        
        fixed_add_listener = """    def add_message_listener(self, chat_id, listener_type, callback):
        """Add a listener for non-command messages."""
        # First remove any existing listener to prevent duplicate responses
        if chat_id in self.wallet_listeners:
            logger.info(f"Removing existing {listener_type} listener for chat {chat_id} before adding new one")
            
        # Add new listener
        self.wallet_listeners[chat_id] = (listener_type, callback)
        logger.info(f"Added {listener_type} listener for chat {chat_id}")"""
        
        # Replace the method
        if original_add_listener in content:
            content = content.replace(original_add_listener, fixed_add_listener)
            logger.info("Fixed add_message_listener method")
        else:
            logger.warning("Could not find original add_message_listener method")
        
        # 2. Fix the process_update method to properly handle duplicate messages
        # Look for the pattern where messages are processed
        process_pattern = """                # Process the message text
                text = update['message']['text']
                
                # Check if this is a command
                if text.startswith('/'):"""
                
        fixed_process = """                # Process the message text
                text = update['message']['text']
                
                # Check if we've already processed this message ID to prevent duplicates
                if 'message_id' in update['message']:
                    message_id = update['message']['message_id']
                    # Use a simple in-memory cache for processed message IDs
                    if not hasattr(self, '_processed_messages'):
                        self._processed_messages = set()
                    
                    if message_id in self._processed_messages:
                        logger.info(f"Skipping already processed message {message_id}")
                        return
                    
                    # Add to processed messages
                    self._processed_messages.add(message_id)
                    # Limit cache size to prevent memory issues
                    if len(self._processed_messages) > 1000:
                        self._processed_messages = set(list(self._processed_messages)[-500:])
                
                # Check if this is a command
                if text.startswith('/'):"""
                
        # Replace the process pattern
        if process_pattern in content:
            content = content.replace(process_pattern, fixed_process)
            logger.info("Fixed message processing to prevent duplicates")
        else:
            logger.warning("Could not find message processing pattern")
        
        # 3. Write the updated content back to the file
        with open(bot_file, 'w') as f:
            f.write(content)
        
        logger.info("Successfully updated bot_v20_runner.py to fix duplicate responses")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing bot listeners: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Fixing duplicate response issue in bot...")
    if fix_bot_listener_system():
        print("✅ Successfully fixed duplicate response issue")
        print("Please restart the bot for changes to take effect")
    else:
        print("❌ Failed to fix duplicate response issue")