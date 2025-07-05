"""
Complete Enhanced Trade Broadcast System Fix
===========================================
Cleans up corrupted bot_v20_runner.py and implements clean enhanced trade broadcast system
"""

import os
import re

def clean_and_fix_bot_file():
    """
    Clean up corrupted bot_v20_runner.py and implement proper enhanced trade broadcast system
    """
    
    # Read the current file
    with open('bot_v20_runner.py', 'r') as f:
        content = f.read()
    
    # Find the point where corruption starts (after admin_broadcast_trade_message_handler)
    lines = content.split('\n')
    
    # Find the end of the clean admin_broadcast_trade_message_handler function
    clean_end_line = -1
    for i, line in enumerate(lines):
        if 'bot.send_message(chat_id, f"❌ Error processing trade: {str(e)}")' in line:
            clean_end_line = i
            break
    
    if clean_end_line == -1:
        print("Could not find the end of clean function")
        return False
    
    # Find the start of clean functions that should remain
    time_selection_start = -1
    for i in range(clean_end_line + 1, len(lines)):
        if 'def time_selection_handler(update, chat_id):' in line and '"Handle time selection for admin trade broadcasts"' in lines[i+1] if i+1 < len(lines) else False:
            time_selection_start = i
            break
    
    if time_selection_start == -1:
        print("Could not find clean time_selection_handler")
        return False
    
    # Find the end of the clean functions we want to keep
    clean_functions_end = -1
    for i in range(time_selection_start, len(lines)):
        if 'def admin_broadcast_announcement_message_handler(update, chat_id, text):' in line:
            # This should be a clean function, find its proper start
            clean_functions_end = i
            break
    
    if clean_functions_end == -1:
        print("Could not find end of clean functions")
        return False
    
    # Keep everything before corruption and after clean functions
    clean_content_before = '\n'.join(lines[:clean_end_line + 1])
    clean_functions = '\n'.join(lines[time_selection_start:clean_functions_end])
    remaining_content = '\n'.join(lines[clean_functions_end:])
    
    # Create the cleaned file content
    final_content = clean_content_before + '\n\n' + clean_functions + '\n\n' + remaining_content
    
    # Write the cleaned file
    with open('bot_v20_runner_clean.py', 'w') as f:
        f.write(final_content)
    
    print(f"Created clean file with {len(final_content.split())} lines")
    return True

def add_missing_enhanced_components():
    """
    Add any missing enhanced trade broadcast components
    """
    
    # Enhanced trade broadcast handler implementation
    enhanced_handler = '''
def admin_broadcast_announcement_message_handler(update, chat_id, text):
    """
    Handle admin announcement broadcasts using enhanced position formatting
    """
    try:
        with app.app_context():
            from models import User, UserStatus, BroadcastMessage
            from datetime import datetime
            
            # Validate text
            if not text or len(text.strip()) < 5:
                bot.send_message(chat_id, "❌ Announcement message is too short. Please provide a meaningful message.")
                return
            
            # Query all active users
            active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
            
            if not active_users:
                bot.send_message(chat_id, "❌ No active users found to send the announcement.")
                return
            
            broadcast_count = 0
            
            # Create broadcast record
            broadcast_record = BroadcastMessage(
                admin_id=str(update['message']['from']['id']),
                message_content=text,
                recipient_count=len(active_users),
                broadcast_time=datetime.utcnow(),
                message_type="announcement"
            )
            db.session.add(broadcast_record)
            
            # Send to all active users
            for user in active_users:
                try:
                    formatted_message = f"📢 *System Announcement*\\n\\n{text}"
                    bot.send_message(user.telegram_id, formatted_message, parse_mode="Markdown")
                    broadcast_count += 1
                except Exception as e:
                    import logging
                    logging.error(f"Error sending announcement to user {user.id}: {e}")
                    continue
            
            # Commit changes
            db.session.commit()
            
            # Send confirmation to admin
            success_message = (
                "✅ *Announcement Broadcast Complete*\\n\\n"
                f"• *Users Reached:* {broadcast_count} of {len(active_users)}\\n"
                f"• *Message:* {text[:50]}...\\n\\n"
                "*All active users have been notified.*"
            )
            
            bot.send_message(chat_id, success_message, parse_mode="Markdown")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_broadcast_announcement_message_handler: {str(e)}")
        bot.send_message(chat_id, f"❌ Error sending announcement: {str(e)}")
'''
    
    return enhanced_handler

if __name__ == "__main__":
    print("Starting enhanced trade system fix...")
    
    if clean_and_fix_bot_file():
        print("✅ Bot file cleaned successfully")
        
        # Replace the original file with the clean version
        os.rename('bot_v20_runner.py', 'bot_v20_runner_backup.py')
        os.rename('bot_v20_runner_clean.py', 'bot_v20_runner.py')
        
        print("✅ Enhanced trade broadcast system restored")
    else:
        print("❌ Failed to clean bot file")