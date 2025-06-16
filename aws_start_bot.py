#!/usr/bin/env python3
"""
AWS Bot Starter - Simplified startup for AWS deployment
=====================================================
This script ensures proper environment setup and starts the bot on AWS
"""

import os
import sys
import logging
import time
from pathlib import Path

def setup_aws_environment():
    """Setup environment for AWS deployment"""
    print("Setting up AWS environment...")
    
    # Load .env file if it exists
    env_file = Path('.env')
    if env_file.exists():
        print("Loading .env file...")
        from dotenv import load_dotenv
        load_dotenv()
        print("Environment variables loaded from .env")
    else:
        print("Warning: .env file not found - using system environment variables")
    
    # Verify required environment variables
    required_vars = ['TELEGRAM_BOT_TOKEN', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        if env_file.exists():
            print("Please check your .env file contains:")
            for var in missing_vars:
                print(f"  {var}=your_value_here")
        else:
            print("Please create a .env file with:")
            for var in missing_vars:
                print(f"  {var}=your_value_here")
        sys.exit(1)
    
    print("All required environment variables found")
    return True

def test_database_connection():
    """Test database connectivity"""
    print("Testing database connection...")
    
    try:
        # Import Flask app and test database
        from app import app, db
        from models import User
        
        with app.app_context():
            # Try to query the database
            user_count = User.query.count()
            print(f"Database connected successfully - {user_count} users found")
            return True
            
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Please check your DATABASE_URL in the .env file")
        return False

def start_bot():
    """Start the Telegram bot"""
    print("Starting Telegram bot...")
    
    try:
        # Import and run the bot
        from bot_v20_runner import main
        main()
        
    except KeyboardInterrupt:
        print("Bot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"Bot failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main AWS startup function"""
    print("=" * 60)
    print("AWS Solana Memecoin Trading Bot Startup")
    print("=" * 60)
    
    # Setup environment
    if not setup_aws_environment():
        sys.exit(1)
    
    # Test database
    if not test_database_connection():
        sys.exit(1)
    
    # Start bot
    print("All systems ready - starting bot...")
    print("Press Ctrl+C to stop the bot")
    print("=" * 60)
    
    start_bot()

if __name__ == '__main__':
    main()