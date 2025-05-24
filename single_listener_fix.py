"""
Simple Fix for Duplicate Bot Responses
This script adds a global dictionary to track text listeners and ensures
that only one listener is active for each chat ID at a time
"""
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_duplicate_responses():
    """Add code to ensure only one listener per chat ID"""
    try:
        # Path to the bot file
        bot_file = 'bot_v20_runner.py'
        
        if not os.path.exists(bot_file):
            logger.error(f"Bot file not found: {bot_file}")
            return False
            
        # Read the current content
        with open(bot_file, 'r') as f:
            content = f.read()
            
        # Add text_listeners dictionary if it doesn't exist
        if 'text_listeners = {}' not in content:
            # Find a good place to add it (after other global variables)
            after_line = '# Global variables for balance adjustment'
            new_global = 'text_listeners = {}  # Track text message listeners'
            
            # Add the new global dictionary
            content = content.replace(
                after_line, 
                after_line + '\n' + new_global
            )
        
        # Check if the file has an add_text_listener function
        if '__main__.add_text_listener' in content:
            # Find the function and update it
            # Look for patterns like:
            old_func = 'def add_text_listener(chat_id, callback):'
            
            if old_func in content:
                # Find the function implementation
                start_pos = content.find(old_func)
                end_pos = content.find('def ', start_pos + 1)
                if end_pos == -1:
                    end_pos = len(content)
                
                # Extract the current function
                current_func = content[start_pos:end_pos]
                
                # Create a new function that prevents duplicates
                new_func = '''def add_text_listener(chat_id, callback):
    """Add a text message listener"""
    global text_listeners
    
    # Check if there's already a listener for this chat
    if chat_id in text_listeners:
        # Clear existing listeners to prevent duplicates
        logger.info(f"Removed listener for chat {chat_id}")
        text_listeners[chat_id] = []
    else:
        text_listeners[chat_id] = []
        
    # Add the new listener
    text_listeners[chat_id].append(callback)
    logger.info(f"Added text listener for chat {chat_id}")
'''
                
                # Replace the function
                content = content.replace(current_func, new_func)
                
                # Write the updated content
                with open(bot_file, 'w') as f:
                    f.write(content)
                    
                logger.info("Successfully updated add_text_listener function")
                return True
                
            else:
                logger.error("Could not find add_text_listener function implementation")
                return False
        else:
            logger.error("Bot does not use text_listeners")
            return False
            
    except Exception as e:
        logger.error(f"Error fixing duplicate responses: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Fixing duplicate response issue...")
    if fix_duplicate_responses():
        print("✅ Successfully fixed duplicate response issue")
        print("Please restart the bot for changes to take effect")
    else:
        print("❌ Failed to fix duplicate response issue")