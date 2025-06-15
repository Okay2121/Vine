#!/usr/bin/env python3

from app import app
from models import User

with app.app_context():
    user = User.query.filter_by(telegram_id='7611754415').first()
    if user:
        print(f'User found: {user.telegram_id}')
        print(f'Username: {repr(user.username)}')
        print(f'Balance: {user.balance}')
        print(f'Username type: {type(user.username)}')
        
        if user.username:
            special_chars = ['_', '*', '[', ']', '`']
            has_special = any(char in user.username for char in special_chars)
            print(f'Username contains special chars: {has_special}')
            if has_special:
                for char in special_chars:
                    if char in user.username:
                        print(f'Contains: {char}')
        
        # Test message formatting
        username_display = f"@{user.username}" if user.username else "No username"
        
        # Test both safe and unsafe formatting
        print("\n=== Testing message formats ===")
        
        # Original format (might cause issues)
        original_msg = (
            f"📊 *User Found*\n\n"
            f"*User:* {username_display}\n"
            f"*Telegram ID:* `{user.telegram_id}`\n"
            f"*Current Balance:* {user.balance:.4f} SOL\n\n"
        )
        print("Original message:")
        print(repr(original_msg))
        
        # Safe format
        if user.username:
            safe_username = user.username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            safe_username_display = f"@{safe_username}"
        else:
            safe_username_display = "No username"
            
        safe_msg = (
            f"📊 *User Found*\n\n"
            f"*User:* {safe_username_display}\n"
            f"*Telegram ID:* `{user.telegram_id}`\n"
            f"*Current Balance:* {user.balance:.4f} SOL\n\n"
        )
        print("\nSafe message:")
        print(repr(safe_msg))
        
    else:
        print('User not found')