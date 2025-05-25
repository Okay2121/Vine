#!/usr/bin/env python
"""
Simple Bot Starter - Ensures the bot runs continuously
"""
import subprocess
import sys
import time
import os

def start_bot():
    """Start the bot and keep it running"""
    print("Starting Telegram bot...")
    
    # Make sure we're in the right directory
    if not os.path.exists('bot_v20_runner.py'):
        print("Error: bot_v20_runner.py not found")
        return False
    
    try:
        # Start the bot process
        process = subprocess.Popen([sys.executable, 'bot_v20_runner.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        print(f"Bot started with PID: {process.pid}")
        
        # Monitor the process
        while True:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"Bot process ended. Output: {stdout}")
                if stderr:
                    print(f"Error: {stderr}")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping bot...")
        process.terminate()
    except Exception as e:
        print(f"Error starting bot: {e}")
        return False
    
    return True

if __name__ == "__main__":
    start_bot()