#!/usr/bin/env python3
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
        print(f"\nChecking {name}...")
        if check_func():
            passed += 1
    
    print(f"\n{'='*50}")
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
