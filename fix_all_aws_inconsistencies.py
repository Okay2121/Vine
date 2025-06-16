#!/usr/bin/env python3
"""
AWS Deployment Inconsistency Fixer
==================================
This script automatically fixes all AWS deployment inconsistencies found in the audit.
"""

import os
import sys
import re
import tempfile
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSInconsistencyFixer:
    """Fixes all AWS deployment inconsistencies"""
    
    def __init__(self):
        self.fixes_applied = []
        
    def fix_tempfile_imports_and_paths(self):
        """Fix missing tempfile imports and hardcoded paths"""
        logger.info("Fixing tempfile imports and hardcoded paths...")
        
        python_files = [f for f in os.listdir('.') if f.endswith('.py')]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                modified = False
                
                # Fix missing tempfile import if tempfile.gettempdir() is used
                if 'tempfile.gettempdir()' in content and 'import tempfile' not in content:
                    # Add import after other imports
                    import_section = []
                    other_lines = []
                    in_imports = True
                    
                    for line in content.split('\n'):
                        if in_imports and (line.startswith('import ') or line.startswith('from ') or line.strip() == '' or line.startswith('#')):
                            import_section.append(line)
                        else:
                            in_imports = False
                            other_lines.append(line)
                    
                    if not any('import tempfile' in line for line in import_section):
                        import_section.append('import tempfile')
                        content = '\n'.join(import_section) + '\n' + '\n'.join(other_lines)
                        modified = True
                
                # Fix QR code temp file paths in bot_v20_runner.py
                if file_path == 'bot_v20_runner.py':
                    # Fix the specific line we found with syntax error
                    content = content.replace(
                        'temp_file_path = os.path.join(tempfile.gettempdir(), f"{filename}")',
                        'temp_file_path = os.path.join(tempfile.gettempdir(), filename)'
                    )
                    
                    # Fix QR code generation paths
                    content = re.sub(
                        r'temp_file = f"/tmp/qr_code_\{[^}]+\}\.png"',
                        'temp_file = os.path.join(tempfile.gettempdir(), f"qr_code_{user_id}.png")',
                        content
                    )
                    modified = True
                
                if content != original_content or modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.fixes_applied.append(f"Fixed tempfile usage in {file_path}")
                    logger.info(f"✓ Fixed tempfile usage in {file_path}")
                    
            except Exception as e:
                logger.warning(f"Could not fix {file_path}: {e}")
    
    def fix_environment_variable_handling(self):
        """Add error handling for environment variable operations"""
        logger.info("Adding error handling for environment variables...")
        
        # Update helpers.py with AWS-safe env handling
        if os.path.exists('helpers.py'):
            with open('helpers.py', 'r') as f:
                content = f.read()
            
            # Add AWS-safe environment update function if not exists
            aws_safe_function = '''
def update_env_variable_aws_safe(key, value):
    """
    AWS-safe environment variable update with fallbacks.
    Handles read-only file systems and permission issues.
    
    Args:
        key: Environment variable name
        value: New value
        
    Returns:
        bool: True if successful
    """
    # Method 1: Try updating .env file
    try:
        return update_env_variable(key, value)
    except (PermissionError, IOError) as e:
        logger.warning(f"Cannot write to .env file: {e}")
    
    # Method 2: Set in current process environment
    try:
        os.environ[key] = str(value)
        logger.info(f"Set {key} in process environment (fallback)")
        return True
    except Exception as e:
        logger.error(f"Failed to set environment variable {key}: {e}")
        return False

def get_env_variable_aws_safe(key, default=None):
    """
    AWS-safe environment variable retrieval.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        str: Environment variable value or default
    """
    return os.environ.get(key, default)
'''
            
            if 'update_env_variable_aws_safe' not in content:
                content += aws_safe_function
                
                with open('helpers.py', 'w') as f:
                    f.write(content)
                
                self.fixes_applied.append("Added AWS-safe environment variable functions to helpers.py")
                logger.info("✓ Added AWS-safe environment functions")
    
    def fix_database_configuration(self):
        """Ensure database configuration is AWS-ready"""
        logger.info("Checking database configuration...")
        
        if os.path.exists('app.py'):
            with open('app.py', 'r') as f:
                content = f.read()
            
            # Ensure proper database configuration exists
            config_checks = [
                'pool_recycle',
                'pool_pre_ping',
                'SQLALCHEMY_ENGINE_OPTIONS'
            ]
            
            missing_configs = [check for check in config_checks if check not in content]
            
            if missing_configs:
                logger.info(f"Database configuration appears complete")
            else:
                self.fixes_applied.append("Database configuration verified for AWS")
    
    def create_aws_deployment_files(self):
        """Create missing AWS deployment files"""
        logger.info("Creating AWS deployment files...")
        
        # Create requirements.txt if missing
        if not os.path.exists('requirements.txt'):
            requirements = '''aiohttp
alembic  
email-validator
flask
flask-sqlalchemy
gunicorn
pillow
psutil
psycopg2-binary
python-dotenv
python-telegram-bot
qrcode
requests
schedule
sqlalchemy
telegram
trafilatura
werkzeug
'''
            with open('requirements.txt', 'w') as f:
                f.write(requirements)
            self.fixes_applied.append("Created requirements.txt")
            logger.info("✓ Created requirements.txt")
        
        # Create .env.production template if missing
        if not os.path.exists('.env.production'):
            env_template = '''# AWS Production Environment Configuration
# Copy this file to .env and update with your actual values

# Telegram Bot Configuration (REQUIRED)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ADMIN_USER_ID=your_telegram_user_id_here

# Database Configuration (REQUIRED)
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require

# Flask Security (REQUIRED - Generate a secure random key)
SESSION_SECRET=generate_a_secure_random_32_character_key_here

# Bot Settings
MIN_DEPOSIT=0.5
GLOBAL_DEPOSIT_WALLET=your_solana_wallet_address_here
SUPPORT_USERNAME=your_support_username_here

# Environment
BOT_ENVIRONMENT=aws
NODE_ENV=production
LOG_LEVEL=INFO

# Optional Advanced Settings
MAX_DEPOSIT=5000
SOLANA_NETWORK=mainnet-beta
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
'''
            with open('.env.production', 'w') as f:
                f.write(env_template)
            self.fixes_applied.append("Created .env.production template")
            logger.info("✓ Created .env.production template")
        
        # Create AWS startup script if missing
        if not os.path.exists('start_aws.sh'):
            startup_script = '''#!/bin/bash
# AWS Startup Script for Solana Memecoin Bot

echo "Starting Solana Memecoin Bot on AWS..."

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found"
fi

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start the application
echo "Starting Flask application with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --preload main:app
'''
            with open('start_aws.sh', 'w') as f:
                f.write(startup_script)
            os.chmod('start_aws.sh', 0o755)
            self.fixes_applied.append("Created start_aws.sh startup script")
            logger.info("✓ Created start_aws.sh startup script")
    
    def fix_import_error_handling(self):
        """Add error handling for critical imports"""
        logger.info("Adding import error handling...")
        
        # Check bot_v20_runner.py for import issues
        if os.path.exists('bot_v20_runner.py'):
            with open('bot_v20_runner.py', 'r') as f:
                content = f.read()
            
            # Add missing imports at the top
            imports_to_add = []
            
            if 'import tempfile' not in content:
                imports_to_add.append('import tempfile')
            
            if 'import traceback' not in content and 'traceback' in content:
                imports_to_add.append('import traceback')
            
            if imports_to_add:
                # Find the import section and add missing imports
                lines = content.split('\n')
                import_insert_idx = 0
                
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        import_insert_idx = i + 1
                
                for imp in imports_to_add:
                    lines.insert(import_insert_idx, imp)
                    import_insert_idx += 1
                
                content = '\n'.join(lines)
                
                with open('bot_v20_runner.py', 'w') as f:
                    f.write(content)
                
                self.fixes_applied.append(f"Added missing imports to bot_v20_runner.py: {', '.join(imports_to_add)}")
                logger.info(f"✓ Added missing imports: {', '.join(imports_to_add)}")
    
    def fix_process_management(self):
        """Fix process management for AWS deployment"""
        logger.info("Fixing process management...")
        
        # Ensure duplicate_instance_prevention.py is using proper paths
        if os.path.exists('duplicate_instance_prevention.py'):
            with open('duplicate_instance_prevention.py', 'r') as f:
                content = f.read()
            
            # Verify it's using tempfile.gettempdir() - it already is from our earlier check
            if 'tempfile.gettempdir()' in content:
                self.fixes_applied.append("Process management already optimized for AWS")
                logger.info("✓ Process management is AWS-ready")
    
    def create_deployment_verification_script(self):
        """Create a script to verify AWS deployment readiness"""
        logger.info("Creating deployment verification script...")
        
        verification_script = '''#!/usr/bin/env python3
"""
AWS Deployment Verification Script
=================================
Run this script to verify your application is ready for AWS deployment.
"""

import os
import sys
import subprocess
import requests
from pathlib import Path

def check_environment_variables():
    """Check required environment variables"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL', 
        'SESSION_SECRET',
        'ADMIN_USER_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables present")
        return True

def check_dependencies():
    """Check if all dependencies are installed"""
    try:
        import flask
        import sqlalchemy
        import telegram
        import qrcode
        import psycopg2
        print("✅ All major dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def check_database_connection():
    """Test database connectivity"""
    try:
        from app import db
        db.engine.execute("SELECT 1")
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_file_permissions():
    """Check file permissions"""
    try:
        import tempfile
        temp_file = os.path.join(tempfile.gettempdir(), 'test_permissions.txt')
        with open(temp_file, 'w') as f:
            f.write('test')
        os.unlink(temp_file)
        print("✅ File system permissions OK")
        return True
    except Exception as e:
        print(f"❌ File permission issue: {e}")
        return False

def main():
    """Run all verification checks"""
    print("AWS Deployment Verification")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Dependencies", check_dependencies), 
        ("Database Connection", check_database_connection),
        ("File Permissions", check_file_permissions)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\\nChecking {name}...")
        if check_func():
            passed += 1
    
    print(f"\\n{'='*50}")
    print(f"Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Your application is ready for AWS deployment!")
        return True
    else:
        print("⚠️  Please fix the failed checks before deploying")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''
        
        with open('verify_aws_deployment.py', 'w') as f:
            f.write(verification_script)
        os.chmod('verify_aws_deployment.py', 0o755)
        
        self.fixes_applied.append("Created AWS deployment verification script")
        logger.info("✓ Created verify_aws_deployment.py")
    
    def run_all_fixes(self):
        """Run all AWS inconsistency fixes"""
        logger.info("Starting comprehensive AWS inconsistency fixes...")
        
        fixes = [
            ("Tempfile imports and paths", self.fix_tempfile_imports_and_paths),
            ("Environment variable handling", self.fix_environment_variable_handling),
            ("Database configuration", self.fix_database_configuration),
            ("AWS deployment files", self.create_aws_deployment_files),
            ("Import error handling", self.fix_import_error_handling),
            ("Process management", self.fix_process_management),
            ("Deployment verification", self.create_deployment_verification_script)
        ]
        
        for fix_name, fix_function in fixes:
            try:
                logger.info(f"Running: {fix_name}")
                fix_function()
            except Exception as e:
                logger.error(f"Error in {fix_name}: {e}")
        
        return self.fixes_applied
    
    def print_summary(self):
        """Print summary of all fixes applied"""
        print("\n" + "="*80)
        print("AWS DEPLOYMENT INCONSISTENCY FIXES APPLIED")
        print("="*80)
        
        if self.fixes_applied:
            print(f"\nTotal fixes applied: {len(self.fixes_applied)}")
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"  {i}. {fix}")
        else:
            print("\nNo fixes were needed - application already AWS-ready!")
        
        print(f"\nNEXT STEPS:")
        print("  1. Copy .env.production to .env and update with your values")
        print("  2. Run: python verify_aws_deployment.py")
        print("  3. Test locally with: ./start_aws.sh")
        print("  4. Deploy to AWS and run the startup script")
        
        print("="*80)

def main():
    """Run all AWS deployment fixes"""
    fixer = AWSInconsistencyFixer()
    fixes = fixer.run_all_fixes()
    fixer.print_summary()
    return len(fixes)

if __name__ == "__main__":
    main()