
This script ensures proper environment setup and starts the bot on AWS
"""

import os
import sys
from pathlib import Path

def setup_aws_environment():
    """Setup environment for AWS deployment"""
    print("Setting up AWS environment...")
    
    # Load .env file if it exists
    env_file = Path('.env')
    if env_file.exists():
        print("Loading .env file...")
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)  # Override existing environment variables
            print("Environment variables loaded from .env")
        except ImportError:
            print("Error: python-dotenv not installed. Run: pip install python-dotenv")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading .env file: {e}")
            sys.exit(1)
    else:
        print("Warning: .env file not found - using system environment variables")
    
    # Verify required environment variables
    required_vars = ['TELEGRAM_BOT_TOKEN', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            # Show partial value for verification (first 10 chars)
            print(f"Found {var}: {value[:20]}...")
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("\nDebugging info:")
        print(f".env file exists: {env_file.exists()}")
        if env_file.exists():
            print("Content of .env file (first few lines):")
            with open(env_file, 'r') as f:
                for i, line in enumerate(f):
                    if i < 5:  # Show first 5 lines
                        if any(var in line for var in required_vars):
                            print(f"  {line.strip()}")
        sys.exit(1)
    
    print("All required environment variables found")
    return True

def test_database_connection():
    """Test database connectivity"""
    print("Testing database connection...")
    
    try:
        # Import Flask app and test database
        from app import app
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
        # Set AWS environment flag before importing
        os.environ['BOT_ENVIRONMENT'] = 'aws'
        
        # Import and run the bot using direct execution mode
        from bot_v20_runner import run_polling
        
        print("Bot starting in AWS polling mode...")
        print("Press Ctrl+C to stop the bot")
        
        # Start the bot polling
        run_polling()
        
    except KeyboardInterrupt:
        print("\nBot stopped by user (Ctrl+C)")
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