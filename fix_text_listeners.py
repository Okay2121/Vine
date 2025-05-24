"""
Fix Text Listeners - Prevent Duplicate Responses
This script prevents duplicate message responses by ensuring only one text listener 
is active for each chat at any time
"""
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_text_listeners():
    """
    Updates the add_text_listener and remove_listener methods in the bot to prevent
    duplicate responses when handling messages
    """
    try:
        # Get the full path to the bot file
        bot_file_path = 'bot_v20_runner.py'
        
        if not os.path.exists(bot_file_path):
            logger.error(f"Bot file not found at {bot_file_path}")
            return False
            
        # Read the current content
        with open(bot_file_path, 'r') as file:
            content = file.read()
            
        # 1. Find the existing text_listeners dictionary declaration
        if 'text_listeners = {}' not in content:
            # Add text_listeners dictionary if it doesn't exist
            text_listeners_declaration = (
                "# Global variables for tracking message state\n"
                "pending_broadcast_id = None\n"
                "broadcast_target = \"all\"     # Default broadcast target (\"all\" or \"active\")\n"
                "broadcast_recipients = []    # List of recipient IDs for the current broadcast\n"
                "dm_recipient_id = None\n"
                "dm_content = None\n"
                "dm_image_url = None\n"
                "dm_image_caption = None\n"
                "admin_target_user_id = None\n"
                "text_listeners = {}    # Dictionary to track active text message listeners\n"
            )
            
            # Replace the existing message state block
            content = content.replace(
                "# Global variables for tracking message state\n"
                "pending_broadcast_id = None\n"
                "broadcast_target = \"all\"     # Default broadcast target (\"all\" or \"active\")\n"
                "broadcast_recipients = []    # List of recipient IDs for the current broadcast\n"
                "dm_recipient_id = None\n"
                "dm_content = None\n"
                "dm_image_url = None\n"
                "dm_image_caption = None\n"
                "admin_target_user_id = None\n",
                text_listeners_declaration
            )
        
        # 2. Add/fix the add_text_listener method
        add_text_listener_method = """
    def add_text_listener(self, chat_id, callback):
        # Add a listener for text messages
        global text_listeners
        # Remove existing listener if any to prevent duplicate responses
        if chat_id in text_listeners:
            logger.info(f"Removing existing listener for chat {chat_id} before adding new one")
            text_listeners[chat_id] = []
            
        # Initialize the list if needed
        if chat_id not in text_listeners:
            text_listeners[chat_id] = []
            
        text_listeners[chat_id].append(callback)
        logger.info(f"Added text listener for chat {chat_id}")
"""
        
        # Find the add_text_listener method and replace it
        if "def add_text_listener(self, chat_id, callback):" in content:
            # Find the beginning and end of the method
            method_start = content.find("def add_text_listener(self, chat_id, callback):")
            method_end = content.find("def ", method_start + 1)
            if method_end == -1:  # If it's the last method
                method_end = content.find("\n\n", method_start + 1)
                
            # Extract the current method
            current_method = content[method_start:method_end]
            
            # Replace with the fixed method
            content = content.replace(current_method, add_text_listener_method)
        else:
            # If method doesn't exist, add it after the last method in the SimpleTelegramBot class
            last_method_end = content.find("    def run(self):")
            if last_method_end != -1:
                # Find the end of the run method
                run_method_end = content.find("def ", last_method_end + 1)
                if run_method_end == -1:
                    run_method_end = len(content)
                
                # Insert the add_text_listener method before the next def
                content = content[:run_method_end] + add_text_listener_method + content[run_method_end:]
        
        # 3. Make sure the remove_listener method also cleans up text_listeners
        remove_listener_method = """
    def remove_listener(self, chat_id):
        """Remove a listener for a chat."""
        global text_listeners
        if chat_id in self.wallet_listeners:
            del self.wallet_listeners[chat_id]
            logger.info(f"Removed wallet listener for chat {chat_id}")
        
        if chat_id in text_listeners:
            del text_listeners[chat_id]
            logger.info(f"Removed text listener for chat {chat_id}")
"""
        
        # Find and replace the remove_listener method
        if "def remove_listener(self, chat_id):" in content:
            # Find the beginning and end of the method
            method_start = content.find("def remove_listener(self, chat_id):")
            method_end = content.find("def ", method_start + 1)
            if method_end == -1:
                method_end = content.find("\n\n", method_start + 1)
                
            # Extract the current method
            current_method = content[method_start:method_end]
            
            # Replace with the fixed method
            content = content.replace(current_method, remove_listener_method)
        
        # 4. Fix the process_message method to properly handle text listeners
        process_message_text_handling = """
        # Check for text listeners
        if chat_id in text_listeners and text_listeners[chat_id]:
            for callback in text_listeners[chat_id]:
                callback(update)
                
            # Clear listeners after processing to prevent duplicates
            text_listeners[chat_id] = []
            logger.info(f"Processed and cleared text listeners for chat {chat_id}")
            return  # Skip further processing
"""
        
        # Find a good place to insert the text listener handling in process_message
        process_callback_position = content.find("def process_callback_query(self, update):")
        if process_callback_position != -1:
            # Insert before the process_callback_query method
            insert_position = content.rfind("\n\n", 0, process_callback_position)
            if insert_position != -1:
                content = content[:insert_position] + process_message_text_handling + content[insert_position:]
        
        # 5. Save the modified content
        with open(bot_file_path, 'w') as file:
            file.write(content)
            
        logger.info("Successfully fixed text listeners to prevent duplicate responses")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing text listeners: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Fixing text listeners to prevent duplicate responses...")
    
    if fix_text_listeners():
        print("✅ Successfully fixed text listeners")
        print("Please restart the bot for changes to take effect")
    else:
        print("❌ Failed to fix text listeners")