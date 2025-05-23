#!/usr/bin/env python
"""
Bot Trade Integration Script
----------------------------
This script updates the bot_v20_runner.py file to integrate the new trade message handler
that processes messages in the format: Buy $TOKEN PRICE TX_LINK or Sell $TOKEN PRICE TX_LINK
"""

import os
import sys
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_bot():
    """Update the bot_v20_runner.py file to add trade message handling"""
    try:
        # Check if files exist
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("bot_v20_runner.py not found")
            return False
            
        if not os.path.exists('trade_message_handler.py'):
            logger.error("trade_message_handler.py not found")
            return False
            
        print("Files found, proceeding with update...")
        
        # Read the bot file
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
            
        # 1. Add import for trade_message_handler
        import_line = "import trade_message_handler"
        if import_line not in content:
            # Find a good spot to add the import
            import_section = "import os\nimport sys\nimport requests\nimport time\nimport json\nimport random"
            new_import_section = import_section + "\n" + import_line
            content = content.replace(import_section, new_import_section)
            print("Added import for trade_message_handler")
        
        # 2. Find the process_message function to add trade handling
        process_pattern = r'def process_message\(update\):'
        process_match = re.search(process_pattern, content)
        
        if not process_match:
            logger.error("Could not find process_message function")
            return False
            
        # Find a good spot to insert the code in the process_message function
        # Look for the section where text messages are handled
        insert_pattern = r'(\s+# Handle text messages.*?\n\s+)(if\s+message\.get\(\'text\'\)\s+and\s+message\[\'text\'\]\.startswith\(\'/\'\):)'
        insert_match = re.search(insert_pattern, content)
        
        if not insert_match:
            # Alternative pattern if first one doesn't match
            insert_pattern = r'(\s+# Process update based on type.*?\n\s+message\s*=\s*update\.get.*?\n\s+)(if\s+\'callback_query\'\s+in\s+update:)'
            insert_match = re.search(insert_pattern, content)
            
        if not insert_match:
            logger.error("Could not find insertion point in process_message function")
            return False
            
        # Create code to insert for trade message handling
        trade_handler_code = """
        # Check for trade messages (Buy/Sell format)
        if message and message.get('text') and 'from' in message:
            text = message['text']
            chat_id = str(message['chat']['id'])
            user_id = message['from']['id']
            
            # Check if this is a trade message and user is admin
            is_admin_user = is_admin(user_id)
            is_trade, success, response = trade_message_handler.process_trade_message(text, is_admin_user)
            
            if is_trade:
                # Send response back to user
                bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)
                return  # Skip further processing
                
        """
        
        # Insert the trade handler code
        modified_content = content[:insert_match.end(1)] + trade_handler_code + content[insert_match.end(1):]
        
        # Write the updated content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(modified_content)
            
        print("Successfully updated bot_v20_runner.py with trade message handling")
        
        # Create a simple help file for the admin to understand the new feature
        with open('TRADE_SYSTEM_HELP.md', 'w') as help_file:
            help_file.write("""# Simple Trade System Guide

## New Format
Just type a message with the following format:

```
Buy $TOKEN PRICE TX_LINK
```

or

```
Sell $TOKEN PRICE TX_LINK
```

## Examples
```
Buy $ZING 0.0041 https://solscan.io/tx/abc123
```
```
Sell $ZING 0.0065 https://solscan.io/tx/def456
```

## How It Works
1. BUY orders are stored for matching
2. SELL orders auto-match with the oldest BUY
3. ROI calculated as ((Sell - Buy) / Buy) × 100
4. Profit applied to all active users' balances
5. Users receive personalized trade notifications

*Note: Timestamps are recorded automatically*
""")
        print("Created TRADE_SYSTEM_HELP.md with instructions")
        
        return True
    except Exception as e:
        logger.error(f"Error updating bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Updating bot with trade message handling...")
    if update_bot():
        print("✅ Update successful")
        print("To restart the bot with the new functionality:")
        print("1. Kill any running bot process")
        print("2. Run 'python bot_v20_runner.py'")
    else:
        print("❌ Update failed")