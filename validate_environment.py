#!/usr/bin/env python3
"""
Environment Variables Validation for Deposit Detection System
============================================================
Validates all required environment variables and configuration settings.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_environment():
    """Validate all environment variables and configuration."""
    print("ENVIRONMENT VALIDATION REPORT")
    print("=" * 50)
    
    # Core environment variables
    env_vars = {
        'DATABASE_URL': os.environ.get('DATABASE_URL'),
        'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN'),
        'ADMIN_USER_ID': os.environ.get('ADMIN_USER_ID'),
        'ADMIN_CHAT_ID': os.environ.get('ADMIN_CHAT_ID'),
        'SESSION_SECRET': os.environ.get('SESSION_SECRET'),
        'MIN_DEPOSIT': os.environ.get('MIN_DEPOSIT'),
        'BOT_ENVIRONMENT': os.environ.get('BOT_ENVIRONMENT'),
        'SOLANA_RPC_URL': os.environ.get('SOLANA_RPC_URL'),
        'GLOBAL_DEPOSIT_WALLET': os.environ.get('GLOBAL_DEPOSIT_WALLET')
    }
    
    print("Environment Variables Status:")
    print("-" * 30)
    
    all_configured = True
    for var_name, var_value in env_vars.items():
        if var_value:
            # Mask sensitive values
            if 'TOKEN' in var_name or 'SECRET' in var_name or 'DATABASE_URL' in var_name:
                display_value = var_value[:10] + "..." if len(var_value) > 10 else "***"
            else:
                display_value = var_value
            print(f"✅ {var_name}: {display_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            all_configured = False
    
    print("\n" + "-" * 30)
    
    # Check config.py values
    try:
        import config
        print("Config.py Values:")
        print(f"✅ SOLANA_RPC_URL: {config.SOLANA_RPC_URL}")
        print(f"✅ GLOBAL_DEPOSIT_WALLET: {config.GLOBAL_DEPOSIT_WALLET}")
        print(f"✅ MIN_DEPOSIT: {config.MIN_DEPOSIT}")
        print(f"✅ ADMIN_USER_ID: {config.ADMIN_USER_ID}")
        print(f"✅ DEFAULT_WALLET: {config.DEFAULT_WALLET}")
    except Exception as e:
        print(f"❌ Config.py import failed: {e}")
        all_configured = False
    
    print("\n" + "=" * 50)
    if all_configured:
        print("✅ ALL REQUIRED VARIABLES CONFIGURED")
        print("Deposit detection system is ready for operation")
    else:
        print("⚠️  MISSING CONFIGURATION DETECTED")
        print("Some environment variables need to be set")
    
    return all_configured

if __name__ == "__main__":
    validate_environment()