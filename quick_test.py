#!/usr/bin/env python3
import sys
sys.path.append('.')

from app import app, db
from models import User, UserStatus

def clean_username(username):
    if not username:
        return "No username"
    clean = username.replace('_', '').replace('.', '').replace('*', '').replace('[', '').replace(']', '').replace('`', '').replace('(', '').replace(')', '').replace('~', '').replace('>', '').replace('#', '').replace('+', '').replace('=', '').replace('|', '').replace('{', '').replace('}', '').replace('!', '')
    return f"@{clean}"

with app.app_context():
    try:
        users = User.query.filter_by(status=UserStatus.ACTIVE).all()
        print(f"Found {len(users)} active users")
        
        for user in users[:2]:
            username_display = clean_username(user.username)
            display_text = f"ID {user.telegram_id} - {username_display} - Balance {user.balance:.0f} SOL"
            print(f"Display: {display_text}")
            
            # Check for problematic characters
            problematic = ['*', '_', '[', ']', '`', '(', ')', '~', '>', '#', '+', '=', '|', '{', '}', '.', '!']
            issues = [char for char in problematic if char in display_text]
            
            if issues:
                print(f"  WARNING: Found {issues}")
            else:
                print("  ✅ Safe message")
        
        print("Test completed")
        
    except Exception as e:
        print(f"Error: {e}")