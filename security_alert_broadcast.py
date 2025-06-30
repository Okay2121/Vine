#!/usr/bin/env python3
"""
Emergency security alert to inform users about spam messages
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app import app
from models import User
from bot_v20_runner import SimpleTelegramBot

def send_security_alert():
    """Send security alert to all users about spam messages"""
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not found")
        return
    
    bot = SimpleTelegramBot(bot_token)
    
    security_message = (
        "🚨 *SECURITY ALERT*\n\n"
        "⚠️ We've detected that some users received spam messages promoting "
        "gambling games like 'Aviator' with fake promo codes.\n\n"
        "🛡️ *IMPORTANT*:\n"
        "• These messages are NOT from Thrive\n"
        "• Our official bot is @ThriveQuantbot only\n"
        "• We NEVER promote gambling or casino games\n"
        "• We NEVER send unsolicited promo codes\n\n"
        "✅ *Stay Safe*:\n"
        "• Block and report any suspicious messages\n"
        "• Only interact with @ThriveQuantbot\n"
        "• Never share your personal information\n\n"
        "💬 If you have questions, contact our support team through the official bot."
    )
    
    with app.app_context():
        users = User.query.all()
        sent_count = 0
        
        for user in users:
            try:
                bot.send_message(
                    user.telegram_id,
                    security_message,
                    parse_mode="Markdown"
                )
                sent_count += 1
                print(f"✅ Sent security alert to user {user.telegram_id}")
                
            except Exception as e:
                print(f"❌ Failed to send to user {user.telegram_id}: {e}")
        
        print(f"\n📊 Security alert sent to {sent_count} users")

if __name__ == "__main__":
    send_security_alert()