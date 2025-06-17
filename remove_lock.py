#!/usr/bin/env python3
import os
import sys

# Remove the Git lock file
lock_file = ".git/index.lock"
if os.path.exists(lock_file):
    try:
        os.remove(lock_file)
        print(f"Successfully removed {lock_file}")
    except Exception as e:
        print(f"Error removing {lock_file}: {e}")
        sys.exit(1)
else:
    print(f"{lock_file} does not exist")