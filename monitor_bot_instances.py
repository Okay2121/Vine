#!/usr/bin/env python3
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
        '/tmp/solana_bot_instance.lock',
        '/tmp/solana_bot.pid',
        '/tmp/bot_lock.txt'
    ]
    
    print("\nLock Files:")
    for lock_file in lock_files:
        if Path(lock_file).exists():
            print(f"  ✓ {lock_file} exists")
        else:
            print(f"  ✗ {lock_file} not found")

if __name__ == "__main__":
    main()
