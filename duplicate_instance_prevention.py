"""
Duplicate Instance Prevention System
===================================
This module provides comprehensive protection against multiple bot instances
and duplicate responses across the entire codebase.
"""

import os
import sys
import fcntl
import time
import logging
import psutil
from pathlib import Path

logger = logging.getLogger(__name__)

class BotInstanceManager:
    """Manages bot instances to prevent duplicates"""
    
    def __init__(self):
        self.lock_file_path = '/tmp/solana_bot_instance.lock'
        self.pid_file_path = '/tmp/solana_bot.pid'
        self.lock_file = None
        
    def acquire_lock(self):
        """Acquire exclusive lock to prevent multiple instances"""
        try:
            # Create lock file
            self.lock_file = open(self.lock_file_path, 'w')
            
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write current PID to lock file
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            
            # Also create PID file for additional checking
            with open(self.pid_file_path, 'w') as pid_file:
                pid_file.write(str(os.getpid()))
            
            logger.info(f"Bot instance lock acquired successfully (PID: {os.getpid()})")
            return True
            
        except (IOError, OSError) as e:
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            
            # Check if another instance is actually running
            if self.is_another_instance_running():
                logger.warning("Another bot instance is already running")
                return False
            else:
                # Stale lock file, try to clean up and retry
                logger.info("Cleaning up stale lock file and retrying...")
                self.cleanup_stale_locks()
                return self.acquire_lock()
    
    def is_another_instance_running(self):
        """Check if another bot instance is actually running"""
        try:
            # Check PID file
            if os.path.exists(self.pid_file_path):
                with open(self.pid_file_path, 'r') as pid_file:
                    pid = int(pid_file.read().strip())
                
                # Check if process is actually running
                if psutil.pid_exists(pid):
                    try:
                        process = psutil.Process(pid)
                        # Check if it's actually our bot process
                        cmdline = ' '.join(process.cmdline())
                        if 'bot_v20_runner.py' in cmdline or 'start_bot' in cmdline:
                            logger.info(f"Found running bot instance with PID {pid}")
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking running instances: {e}")
            return False
    
    def cleanup_stale_locks(self):
        """Clean up stale lock files"""
        try:
            if os.path.exists(self.lock_file_path):
                os.unlink(self.lock_file_path)
            if os.path.exists(self.pid_file_path):
                os.unlink(self.pid_file_path)
            logger.info("Cleaned up stale lock files")
        except Exception as e:
            logger.warning(f"Error cleaning up lock files: {e}")
    
    def release_lock(self):
        """Release the instance lock"""
        try:
            if self.lock_file:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_file = None
            
            # Clean up files
            if os.path.exists(self.lock_file_path):
                os.unlink(self.lock_file_path)
            if os.path.exists(self.pid_file_path):
                os.unlink(self.pid_file_path)
                
            logger.info("Bot instance lock released")
            
        except Exception as e:
            logger.warning(f"Error releasing lock: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        if self.acquire_lock():
            return self
        else:
            raise RuntimeError("Could not acquire bot instance lock")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release_lock()

def prevent_duplicate_startup():
    """Prevent duplicate bot startup - use this in all main entry points"""
    manager = BotInstanceManager()
    
    if not manager.acquire_lock():
        logger.warning("Another bot instance is running, exiting")
        sys.exit(0)
    
    return manager

def check_and_kill_duplicate_processes():
    """Find and terminate any duplicate bot processes"""
    current_pid = os.getpid()
    bot_processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'])
                if ('bot_v20_runner.py' in cmdline or 
                    'start_bot' in cmdline or 
                    'run_polling' in cmdline) and proc.info['pid'] != current_pid:
                    bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if bot_processes:
            logger.warning(f"Found {len(bot_processes)} duplicate bot processes")
            for proc in bot_processes:
                try:
                    logger.info(f"Terminating duplicate process PID {proc.pid}")
                    proc.terminate()
                    # Wait for graceful termination
                    proc.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        proc.kill()  # Force kill if needed
                    except psutil.NoSuchProcess:
                        pass
                except Exception as e:
                    logger.warning(f"Could not terminate process {proc.pid}: {e}")
        
        return len(bot_processes)
        
    except Exception as e:
        logger.error(f"Error checking for duplicate processes: {e}")
        return 0

def setup_signal_handlers(instance_manager):
    """Setup signal handlers for graceful shutdown"""
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        if instance_manager:
            instance_manager.release_lock()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# Global instance manager
_global_instance_manager = None

def get_global_instance_manager():
    """Get or create global instance manager"""
    global _global_instance_manager
    if _global_instance_manager is None:
        _global_instance_manager = BotInstanceManager()
    return _global_instance_manager