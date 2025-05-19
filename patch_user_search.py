#!/usr/bin/env python
"""
Script to patch the bot_v20_runner.py file to add case-insensitive
username search in the admin_adjust_balance_user_id_handler function
"""
import re
import logging
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def patch_file():
    """Patch the bot_v20_runner.py file"""
    # Path to the file
    file_path = 'bot_v20_runner.py'
    
    try:
        # Read the file
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Find the pattern to replace
        pattern = r"""            # If not found, try by username
            if not user and text.startswith\('@'\):
                username = text\[1:\]  # Remove @ prefix
                user = User.query.filter_by\(username=username\).first\(\)
            elif not user:
                # Try with username anyway \(in case they forgot the @\)
                user = User.query.filter_by\(username=text\).first\(\)"""
        
        # Replacement with case-insensitive search
        replacement = """            # Import function for case-insensitive search
            from sqlalchemy import func
            
            # If not found, try by username (case-insensitive)
            if not user and text.startswith('@'):
                username = text[1:]  # Remove @ prefix
                user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
            elif not user:
                # Try with username anyway (in case they forgot the @)
                user = User.query.filter(func.lower(User.username) == func.lower(text)).first()"""
        
        # Replace the pattern
        if re.search(pattern, content):
            new_content = re.sub(pattern, replacement, content)
            
            # Write the modified content back to the file
            with open(file_path, 'w') as file:
                file.write(new_content)
                
            logger.info(f"Successfully patched {file_path} with case-insensitive username search")
            return True
        else:
            logger.error(f"Pattern not found in {file_path}")
            return False
        
    except Exception as e:
        logger.error(f"Error patching file: {e}")
        return False

if __name__ == "__main__":
    # Patch the file
    success = patch_file()
    sys.exit(0 if success else 1)