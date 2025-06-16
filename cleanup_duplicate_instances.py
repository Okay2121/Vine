#!/usr/bin/env python3
import tempfile
"""
Final Cleanup for Duplicate Bot Instances
========================================
This script performs the final cleanup to eliminate all duplicate bot instances
and ensure only the environment-aware startup system is active.
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def disable_problematic_files():
    """Disable all problematic startup files"""
    files_to_disable = [
        'bot.py',
        'fix_bot_commands.py', 
        'simple_bot_runner.py',
        'bot_runner.py',
        'run_bot_persistent.py',
        'optimized_bot.py'
    ]
    
    for filename in files_to_disable:
        filepath = Path(filename)
        if filepath.exists():
            try:
                content = filepath.read_text()
                
                # Check if already disabled
                if 'DEPRECATED' in content or 'disabled' in content.lower():
                    logger.info(f"{filename} already disabled")
                    continue
                
                # Create disabled version
                disabled_content = f'''#!/usr/bin/env python3
"""
DEPRECATED: This file has been disabled to prevent duplicate bot instances.
Use the environment-aware startup system instead:
- Replit: Auto-start enabled automatically via main.py
- AWS/Production: Use 'python start_bot_manual.py'
"""
import sys
print("⚠️ This script is deprecated. Use environment-aware startup system.")
print("For manual start: python start_bot_manual.py")
sys.exit(1)

# Original content disabled to prevent duplicate instances
'''
                
                # Backup original and replace
                backup_path = filepath.with_suffix('.py.disabled')
                backup_path.write_text(content)
                filepath.write_text(disabled_content)
                
                logger.info(f"Disabled {filename} (backup saved as {backup_path})")
                
            except Exception as e:
                logger.error(f"Could not disable {filename}: {e}")

def clean_duplicate_handlers():
    """Remove duplicate handler registrations from production files"""
    files_to_clean = [
        'production_handlers.py',
        'production_bot.py', 
        'main_production.py'
    ]
    
    for filename in files_to_clean:
        filepath = Path(filename)
        if filepath.exists():
            try:
                content = filepath.read_text()
                
                # Comment out duplicate handler registrations
                lines = content.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    if 'add_callback_handler' in line and any(handler in line for handler in ['dashboard', 'deposit', 'how_it_works', 'copy_address']):
                        cleaned_lines.append(f"# DISABLED: {line}  # Duplicate handler - use bot_v20_runner.py instead")
                        logger.info(f"Disabled duplicate handler in {filename}: {line.strip()}")
                    else:
                        cleaned_lines.append(line)
                
                filepath.write_text('\n'.join(cleaned_lines))
                
            except Exception as e:
                logger.error(f"Could not clean {filename}: {e}")

def update_main_py_safety():
    """Add additional safety checks to main.py"""
    main_path = Path('main.py')
    if main_path.exists():
        try:
            content = main_path.read_text()
            
            # Check if safety checks already added
            if 'BotInstanceManager' in content:
                logger.info("main.py already has safety checks")
                return
            
            # Add import at the top
            lines = content.split('\n')
            import_index = None
            for i, line in enumerate(lines):
                if line.startswith('from environment_detector'):
                    import_index = i
                    break
            
            if import_index is not None:
                lines.insert(import_index + 1, 'from duplicate_instance_prevention import get_global_instance_manager')
                
                # Find the start_bot_thread function and add safety check
                for i, line in enumerate(lines):
                    if 'def start_bot_thread():' in line:
                        # Add safety check after the function definition
                        lines.insert(i + 3, '    # Additional duplicate prevention')
                        lines.insert(i + 4, '    instance_manager = get_global_instance_manager()')
                        lines.insert(i + 5, '    if not instance_manager.acquire_lock():')
                        lines.insert(i + 6, '        logger.warning("Another bot instance detected in start_bot_thread, aborting")')
                        lines.insert(i + 7, '        return False')
                        lines.insert(i + 8, '')
                        break
                
                main_path.write_text('\n'.join(lines))
                logger.info("Added additional safety checks to main.py")
                
        except Exception as e:
            logger.error(f"Could not update main.py: {e}")

def create_instance_monitor():
    """Create a monitoring script to check for duplicate instances"""
    monitor_script = '''#!/usr/bin/env python3
"""
Bot Instance Monitor
==================
Monitors for duplicate bot instances and provides status information.
"""

import psutil
import os
import sys
from pathlib import Path

def check_bot_instances():
    """Check for running bot instances"""
    current_pid = os.getpid()
    bot_processes = []
    
    for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
        try:
            cmdline = ' '.join(proc.info['cmdline'])
            if ('bot_v20_runner.py' in cmdline or 
                'start_bot_manual.py' in cmdline) and proc.info['pid'] != current_pid:
                bot_processes.append({
                    'pid': proc.info['pid'],
                    'cmdline': cmdline,
                    'create_time': proc.info['create_time']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return bot_processes

def main():
    print("Bot Instance Monitor")
    print("=" * 40)
    
    instances = check_bot_instances()
    
    if not instances:
        print("✅ No duplicate bot instances detected")
    else:
        print(f"⚠️ Found {len(instances)} bot instances:")
        for instance in instances:
            print(f"  PID {instance['pid']}: {instance['cmdline']}")
    
    # Check lock files
    lock_files = [
        os.path.join(tempfile.gettempdir(), 'solana_bot_instance.lock',
        os.path.join(tempfile.gettempdir(), 'solana_bot.pid',
        os.path.join(tempfile.gettempdir(), 'bot_lock.txt'
    ]
    
    print("\\nLock Files:")
    for lock_file in lock_files:
        if Path(lock_file).exists():
            print(f"  ✓ {lock_file} exists")
        else:
            print(f"  ✗ {lock_file} not found")

if __name__ == "__main__":
    main()
'''
    
    monitor_path = Path('monitor_bot_instances.py')
    monitor_path.write_text(monitor_script)
    logger.info("Created bot instance monitor script")

def main():
    """Run the cleanup process"""
    logger.info("Starting final cleanup of duplicate bot instances...")
    
    disable_problematic_files()
    clean_duplicate_handlers()
    update_main_py_safety()
    create_instance_monitor()
    
    logger.info("Cleanup complete!")
    logger.info("Remaining active startup methods:")
    logger.info("  1. Environment-aware auto-start (Replit)")
    logger.info("  2. Manual start script (AWS): python start_bot_manual.py")
    logger.info("  3. All other startup methods have been disabled")
    logger.info("Use 'python monitor_bot_instances.py' to check for duplicates")

if __name__ == "__main__":
    main()