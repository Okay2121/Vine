#!/usr/bin/env python3
"""
AWS Deployment Readiness Checker
---------------------------------
This script verifies that your bot is ready for AWS deployment
"""

import os
import sys
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check that all required environment variables are present"""
    logger.info("Checking environment variables...")
    
    required_vars = {
        'TELEGRAM_BOT_TOKEN': 'Telegram bot authentication token',
        'ADMIN_USER_ID': 'Administrator Telegram user ID'
    }
    
    optional_vars = {
        'DATABASE_URL': 'PostgreSQL database connection (has fallback)',
        'SESSION_SECRET': 'Flask session security key (has fallback)'
    }
    
    missing_required = []
    present_vars = []
    
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            present_vars.append(f"✓ {var}: {description}")
        else:
            missing_required.append(f"✗ {var}: {description}")
    
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            present_vars.append(f"✓ {var}: {description}")
        else:
            present_vars.append(f"⚠ {var}: {description} (using fallback)")
    
    for var in present_vars:
        logger.info(var)
    
    if missing_required:
        logger.error("Missing required environment variables:")
        for var in missing_required:
            logger.error(var)
        return False
    
    return True

def check_database_connection():
    """Check database connectivity via health endpoint"""
    logger.info("Checking database connection...")
    
    try:
        response = requests.get('http://localhost:5000/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy' and data.get('database') == 'connected':
                logger.info("✓ Database connection: Healthy")
                return True
            else:
                logger.error(f"✗ Database connection: {data}")
                return False
        else:
            logger.error(f"✗ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Database connection check failed: {e}")
        return False

def check_database_details():
    """Check detailed database information"""
    logger.info("Checking database details...")
    
    try:
        response = requests.get('http://localhost:5000/db-status', timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ PostgreSQL Version: {data.get('postgresql_version', 'Unknown')[:50]}...")
            logger.info(f"✓ Database Tables: {data.get('table_count', 0)} tables created")
            logger.info(f"✓ Database URL: {data.get('database_url_prefix', 'Unknown')}")
            return True
        else:
            logger.error(f"✗ Database status check failed with status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Database status check failed: {e}")
        return False

def check_telegram_bot():
    """Verify Telegram bot configuration"""
    logger.info("Checking Telegram bot configuration...")
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    admin_id = os.environ.get('ADMIN_USER_ID')
    
    if not bot_token:
        logger.error("✗ TELEGRAM_BOT_TOKEN not configured")
        return False
    
    if not admin_id:
        logger.error("✗ ADMIN_USER_ID not configured")
        return False
    
    logger.info("✓ Telegram bot token: Configured")
    logger.info(f"✓ Admin user ID: {admin_id}")
    
    return True

def check_deployment_files():
    """Check that deployment files are present"""
    logger.info("Checking deployment files...")
    
    required_files = [
        'main.py',
        'app.py',
        'models.py',
        'config.py',
        '.env',
        'aws_deployment_guide.md'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            logger.info(f"✓ {file}: Present")
        else:
            missing_files.append(file)
            logger.error(f"✗ {file}: Missing")
    
    return len(missing_files) == 0

def main():
    """Run all deployment readiness checks"""
    logger.info("=== AWS Deployment Readiness Check ===")
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Database Connection", check_database_connection),
        ("Database Details", check_database_details),
        ("Telegram Bot Config", check_telegram_bot),
        ("Deployment Files", check_deployment_files)
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check_name, check_function in checks:
        logger.info(f"\n--- {check_name} ---")
        if check_function():
            passed_checks += 1
            logger.info(f"✓ {check_name}: PASSED")
        else:
            logger.error(f"✗ {check_name}: FAILED")
    
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Checks passed: {passed_checks}/{total_checks}")
    
    if passed_checks == total_checks:
        logger.info("🎉 Your bot is ready for AWS deployment!")
        logger.info("📖 Follow the instructions in aws_deployment_guide.md")
        return True
    else:
        logger.error("⚠️  Please fix the failed checks before deploying")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)