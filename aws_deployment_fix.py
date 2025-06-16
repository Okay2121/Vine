#!/usr/bin/env python3
"""
AWS Deployment Fix for Solana Trading Bot
========================================
This script fixes common deployment issues when moving from Replit to AWS
"""

import os
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_encoding_issues():
    """Fix encoding and line ending issues for AWS compatibility"""
    try:
        # Read the original file
        with open('bot_v20_runner.py', 'rb') as f:
            content = f.read()
        
        # Decode and normalize line endings
        content = content.decode('utf-8', errors='ignore')
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Write back with proper encoding
        with open('bot_v20_runner.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ Fixed encoding and line endings")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix encoding: {e}")
        return False

def fix_syntax_issues():
    """Fix specific syntax issues that may cause problems on AWS"""
    try:
        with open('bot_v20_runner.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix any potential Unicode character issues in strings
        unicode_fixes = [
            ('━', '-'),  # Replace Unicode box drawing characters
            ('▰', '#'),  # Replace Unicode block characters
            ('▱', '-'),  # Replace Unicode block characters
            ('🚀', '[ROCKET]'),  # Replace emoji that might cause issues
            ('🥇', '[GOLD]'),
            ('🥈', '[SILVER]'),
            ('🥉', '[BRONZE]'),
            ('💎', '[DIAMOND]'),
        ]
        
        for old, new in unicode_fixes:
            content = content.replace(old, new)
        
        # Write the fixed content
        with open('bot_v20_runner.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ Fixed potential Unicode issues")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix syntax issues: {e}")
        return False

def create_aws_starter():
    """Create a simple AWS starter script that bypasses potential issues"""
    starter_content = '''#!/usr/bin/env python3
"""
AWS Starter for Solana Trading Bot
=================================
Simple starter that loads environment and runs the bot
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env file"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Environment variables loaded from .env")
        return True
    except ImportError:
        logger.error("❌ python-dotenv not installed. Run: pip install python-dotenv")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to load .env: {e}")
        return False

def verify_requirements():
    """Verify all required environment variables are present"""
    required_vars = ['TELEGRAM_BOT_TOKEN', 'DATABASE_URL', 'SESSION_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file")
        return False
    
    logger.info("✅ All required environment variables found")
    return True

def main():
    """Main entry point for AWS deployment"""
    logger.info("🚀 Starting Solana Trading Bot on AWS")
    
    # Load environment
    if not load_environment():
        sys.exit(1)
    
    # Verify requirements
    if not verify_requirements():
        sys.exit(1)
    
    # Import and run the bot
    try:
        logger.info("📥 Importing bot module...")
        from bot_v20_runner import main as bot_main
        logger.info("🤖 Starting bot...")
        bot_main()
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
    
    try:
        with open('aws_bot_starter.py', 'w', encoding='utf-8') as f:
            f.write(starter_content)
        
        # Make executable
        os.chmod('aws_bot_starter.py', 0o755)
        
        logger.info("✅ Created AWS starter script: aws_bot_starter.py")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create starter script: {e}")
        return False

def main():
    """Run all AWS deployment fixes"""
    logger.info("🔧 Running AWS deployment fixes...")
    
    success = True
    success &= fix_encoding_issues()
    success &= fix_syntax_issues()
    success &= create_aws_starter()
    
    if success:
        logger.info("✅ All fixes applied successfully!")
        logger.info("Try running: python3 aws_bot_starter.py")
    else:
        logger.error("❌ Some fixes failed")
    
    return success

if __name__ == '__main__':
    main()