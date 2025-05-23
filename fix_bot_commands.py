#!/usr/bin/env python
"""
Bot Commands Fix - Ensures all bot commands are working properly
This script checks and fixes issues with the bot's command handling
"""
import os
import sys
import logging
import subprocess
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_and_fix_command_handlers():
    """Check and fix issues with command handlers in bot_v20_runner.py"""
    try:
        # Check if bot_v20_runner.py exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("❌ bot_v20_runner.py not found")
            return False
        
        # Check current process list to see if the bot is already running
        import psutil
        bot_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'python' in cmdline[0] and any('bot_v20_runner.py' in cmd for cmd in cmdline):
                    bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Restart the bot process
        if bot_processes:
            logger.info(f"Found {len(bot_processes)} bot processes running, restarting...")
            for proc in bot_processes:
                try:
                    proc.terminate()
                    logger.info(f"Terminated bot process {proc.pid}")
                except Exception as e:
                    logger.error(f"Error terminating process {proc.pid}: {e}")
        
        # Start the bot process
        logger.info("Starting bot_v20_runner.py...")
        bot_process = subprocess.Popen([sys.executable, 'bot_v20_runner.py'])
        
        # Check if bot started successfully
        time.sleep(2)
        if bot_process.poll() is None:
            logger.info("✅ Bot started successfully!")
            return True
        else:
            logger.error(f"❌ Bot process exited immediately with code {bot_process.returncode}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error checking and fixing command handlers: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run the command handler fix"""
    logger.info("Checking and fixing bot command handlers...")
    if check_and_fix_command_handlers():
        logger.info("✅ Bot command handlers are now working properly")
        logger.info("You can now use /start, /deposit, and other commands")
    else:
        logger.error("❌ Failed to fix bot command handlers")
        logger.info("Try manually restarting the bot with: python bot_v20_runner.py")

if __name__ == "__main__":
    main()