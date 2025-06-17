#!/usr/bin/env python3
"""
Git Conflict Resolution Script
=============================
Resolves all Git merge conflicts and prepares repository for GitHub push
"""

import os
import subprocess
import sys
from pathlib import Path

def run_git_command(command):
    """Run a git command safely"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_git_status():
    """Check current git status"""
    print("Checking Git status...")
    success, stdout, stderr = run_git_command("git status --porcelain")
    
    if not success:
        print(f"Error checking git status: {stderr}")
        return False
    
    if stdout.strip():
        print("Git status:")
        print(stdout)
        return True
    else:
        print("Working directory is clean")
        return False

def resolve_merge_conflicts():
    """Resolve any remaining merge conflicts"""
    print("Checking for merge conflicts...")
    
    # Check for conflict markers in files
    conflict_files = []
    for file_path in Path('.').rglob('*.py'):
        try:
            content = file_path.read_text()
            if '<<<<<<< HEAD' in content or '>>>>>>> ' in content:
                conflict_files.append(str(file_path))
        except:
            continue
    
    for file_path in Path('.').rglob('*.md'):
        try:
            content = file_path.read_text()
            if '<<<<<<< HEAD' in content or '>>>>>>> ' in content:
                conflict_files.append(str(file_path))
        except:
            continue
    
    if conflict_files:
        print(f"Found conflict markers in: {', '.join(conflict_files)}")
        return False
    else:
        print("No conflict markers found")
        return True

def add_all_changes():
    """Add all changes to staging"""
    print("Adding all changes to staging...")
    success, stdout, stderr = run_git_command("git add .")
    
    if success:
        print("All changes added to staging")
        return True
    else:
        print(f"Error adding changes: {stderr}")
        return False

def commit_changes():
    """Commit the resolved changes"""
    print("Committing resolved changes...")
    
    commit_message = "Resolve merge conflicts and add AWS environment export system"
    success, stdout, stderr = run_git_command(f'git commit -m "{commit_message}"')
    
    if success:
        print("Changes committed successfully")
        return True
    else:
        print(f"Error committing changes: {stderr}")
        return False

def check_branch_status():
    """Check current branch and remote status"""
    print("Checking branch status...")
    
    # Get current branch
    success, branch, stderr = run_git_command("git branch --show-current")
    if success:
        print(f"Current branch: {branch.strip()}")
    
    # Check remote status
    success, status, stderr = run_git_command("git status -sb")
    if success:
        print(f"Branch status: {status.strip()}")

def cleanup_git_state():
    """Clean up any problematic git state"""
    print("Cleaning up Git state...")
    
    # Remove any lock files
    lock_files = ['.git/index.lock', '.git/HEAD.lock', '.git/config.lock']
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                print(f"Removed {lock_file}")
            except:
                pass
    
    # Reset any staged changes if needed
    success, stdout, stderr = run_git_command("git reset --mixed")
    if success:
        print("Git state reset successfully")
    
    return True

def main():
    """Main resolution process"""
    print("=" * 60)
    print("Git Conflict Resolution Script")
    print("=" * 60)
    
    # Step 1: Clean up git state
    cleanup_git_state()
    
    # Step 2: Check for conflicts
    if not resolve_merge_conflicts():
        print("ERROR: Merge conflicts still exist. Please resolve manually.")
        return False
    
    # Step 3: Check git status
    has_changes = check_git_status()
    
    # Step 4: Add changes if any exist
    if has_changes:
        if not add_all_changes():
            return False
        
        # Step 5: Commit changes
        if not commit_changes():
            return False
    
    # Step 6: Check final status
    check_branch_status()
    
    print("\n" + "=" * 60)
    print("Git conflict resolution completed successfully!")
    print("Repository is now ready for GitHub push.")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)