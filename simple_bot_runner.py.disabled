#!/usr/bin/env python
"""
Simple Bot Runner - Starts the bot and keeps it running
"""
import os
import sys
import time
import signal
import subprocess

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

def signal_handler(sig, frame):
    print("\nStopping bot...")
    sys.exit(0)

def run_bot():
    """Run the bot with proper error handling"""
    signal.signal(signal.SIGINT, signal_handler)
    
    while True:
        try:
            print("Starting bot...")
            # Import and run the bot
            import bot_v20_runner
            break
        except KeyboardInterrupt:
            print("Bot stopped by user")
            break
        except Exception as e:
            print(f"Bot error: {e}")
            print("Restarting bot in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()