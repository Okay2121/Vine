#!/usr/bin/env python3
"""
Auto-start bot when project is remixed
This script ensures the bot starts immediately with embedded credentials
"""
import os
import sys
import subprocess
import time

def start_bot():
    """Start the bot with embedded token"""
    # Set the token in environment
    os.environ['TELEGRAM_BOT_TOKEN'] = '7562541416:AAGxe-j7r26pO7ku1m5kunmwes0n0e3p2XQ'
    
    print("🚀 Starting Telegram bot automatically...")
    
    try:
        # Start the bot process
        bot_process = subprocess.Popen([
            sys.executable, 
            'bot_v20_runner.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✅ Bot started with PID: {bot_process.pid}")
        print("🤖 Your Telegram bot is now running!")
        print("💬 Users can now interact with your bot on Telegram")
        
        return bot_process
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return None

if __name__ == "__main__":
    start_bot()