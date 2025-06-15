#!/usr/bin/env python3
"""
Debug script to check user statuses and fix active user counting
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Flask app and models
from app import app, db
from models import User, UserStatus

def check_user_statuses():
    """Check current user statuses in the database"""
    with app.app_context():
        try:
            # Get all users
            all_users = User.query.all()
            
            print(f"Total users in database: {len(all_users)}")
            print("\nUser Status Breakdown:")
            print("-" * 50)
            
            for user in all_users:
                status_name = user.status.name if user.status else "None"
                print(f"ID: {user.telegram_id}, Username: {user.username or 'N/A'}, Status: {status_name}")
            
            # Count by status
            active_count = User.query.filter_by(status=UserStatus.ACTIVE).count()
            inactive_count = User.query.filter_by(status=UserStatus.INACTIVE).count()
            banned_count = User.query.filter_by(status=UserStatus.BANNED).count()
            
            print(f"\nStatus Counts:")
            print(f"Active: {active_count}")
            print(f"Inactive: {inactive_count}")
            print(f"Banned: {banned_count}")
            
            # Check if any users have None status
            none_status_count = User.query.filter(User.status.is_(None)).count()
            print(f"None status: {none_status_count}")
            
            return {
                'total': len(all_users),
                'active': active_count,
                'inactive': inactive_count,
                'banned': banned_count,
                'none_status': none_status_count
            }
            
        except Exception as e:
            print(f"Error checking user statuses: {e}")
            import traceback
            traceback.print_exc()
            return None

def fix_user_statuses():
    """Fix any users with None status by setting them to ACTIVE"""
    with app.app_context():
        try:
            # Find users with None status
            users_with_none_status = User.query.filter(User.status.is_(None)).all()
            
            if users_with_none_status:
                print(f"Found {len(users_with_none_status)} users with None status. Fixing...")
                
                for user in users_with_none_status:
                    user.status = UserStatus.ACTIVE
                    print(f"Set user {user.telegram_id} ({user.username or 'N/A'}) to ACTIVE")
                
                db.session.commit()
                print("✅ Fixed user statuses successfully!")
            else:
                print("No users with None status found.")
                
        except Exception as e:
            print(f"Error fixing user statuses: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    print("Checking user statuses...")
    status_info = check_user_statuses()
    
    if status_info and status_info['none_status'] > 0:
        print(f"\nFound {status_info['none_status']} users with None status. Fixing...")
        fix_user_statuses()
        
        print("\nRechecking after fix...")
        check_user_statuses()
    else:
        print("\nAll users have proper status values.")