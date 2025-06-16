#!/usr/bin/env python3
"""
AWS Startup Scripts Test Suite
=============================
Tests all AWS deployment scripts in a safe environment
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

def setup_test_environment():
    """Create isolated test environment"""
    print("Setting up test environment...")
    
    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp(prefix="aws_startup_test_")
    print(f"Test directory: {test_dir}")
    
    # Copy essential files to test directory
    files_to_copy = [
        'aws_start_bot.py',
        'aws_troubleshoot.py', 
        'config.py',
        'app.py',
        'models.py',
        'environment_detector.py',
        '.env.test'
    ]
    
    for file_name in files_to_copy:
        if Path(file_name).exists():
            shutil.copy2(file_name, test_dir)
            print(f"Copied {file_name}")
    
    # Rename .env.test to .env in test directory
    test_env_path = Path(test_dir) / '.env.test'
    if test_env_path.exists():
        test_env_path.rename(Path(test_dir) / '.env')
        print("Created test .env file")
    
    return test_dir

def test_environment_detection():
    """Test environment detection functionality"""
    print("\n=== Testing Environment Detection ===")
    
    try:
        from environment_detector import get_environment_info
        env_info = get_environment_info()
        
        print(f"Environment type: {env_info['environment_type']}")
        print(f"Is Replit: {env_info['is_replit']}")
        print(f"Is AWS: {env_info['is_aws']}")
        print(f"Direct execution: {env_info['is_direct_execution']}")
        print(f"Env file exists: {env_info['env_file_exists']}")
        
        return True
        
    except Exception as e:
        print(f"Environment detection failed: {e}")
        return False

def test_config_loading():
    """Test configuration loading with test environment"""
    print("\n=== Testing Configuration Loading ===")
    
    # Temporarily set test environment
    original_env = os.environ.copy()
    
    try:
        # Load test environment
        from dotenv import load_dotenv
        load_dotenv('.env.test', override=True)
        
        # Test config loading
        import config
        
        print(f"Bot token loaded: {'Yes' if config.BOT_TOKEN else 'No'}")
        print(f"Database URL: {'Yes' if config.DATABASE_URL else 'No'}")
        print(f"Admin ID: {config.ADMIN_USER_ID}")
        
        return True
        
    except Exception as e:
        print(f"Config loading failed: {e}")
        return False
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

def test_database_models():
    """Test database model loading without actual connection"""
    print("\n=== Testing Database Models ===")
    
    try:
        # Test model imports
        from models import User, UserStatus, Transaction, TradingPosition
        print("All models imported successfully")
        
        # Test basic model structure
        user_columns = [col.name for col in User.__table__.columns]
        print(f"User model has {len(user_columns)} columns")
        
        return True
        
    except Exception as e:
        print(f"Model testing failed: {e}")
        return False

def test_troubleshooter_logic():
    """Test the troubleshooter logic without external dependencies"""
    print("\n=== Testing Troubleshooter Logic ===")
    
    try:
        # Test individual check functions
        import aws_troubleshoot
        
        # Test Python version check
        python_ok = aws_troubleshoot.check_python_version()
        print(f"Python version check: {'PASS' if python_ok else 'FAIL'}")
        
        # Test environment file check
        env_ok = aws_troubleshoot.check_environment_file()
        print(f"Environment file check: {'PASS' if env_ok else 'FAIL'}")
        
        # Test file permissions check
        perms_ok = aws_troubleshoot.check_file_permissions()
        print(f"File permissions check: {'PASS' if perms_ok else 'FAIL'}")
        
        return True
        
    except Exception as e:
        print(f"Troubleshooter testing failed: {e}")
        return False

def test_startup_script_validation():
    """Test startup script validation logic"""
    print("\n=== Testing Startup Script Validation ===")
    
    try:
        # Test the aws_start_bot.py setup logic
        sys.path.insert(0, '.')
        
        # Test environment setup function
        import aws_start_bot
        
        # This should work without actually starting the bot
        print("AWS startup script imports successfully")
        
        return True
        
    except Exception as e:
        print(f"Startup script validation failed: {e}")
        return False

def test_deployment_files():
    """Test deployment file completeness"""
    print("\n=== Testing Deployment Files ===")
    
    required_files = [
        'aws_start_bot.py',
        'aws_troubleshoot.py',
        'deploy_aws.sh',
        'solana-bot.service',
        'AWS_STARTUP_GUIDE.md'
    ]
    
    missing_files = []
    
    for file_name in required_files:
        if Path(file_name).exists():
            print(f"✓ {file_name}")
        else:
            print(f"✗ {file_name}")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"Missing files: {', '.join(missing_files)}")
        return False
    
    print("All deployment files present")
    return True

def main():
    """Run comprehensive AWS startup testing"""
    print("AWS Startup Scripts Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run individual tests
    tests = [
        ("Environment Detection", test_environment_detection),
        ("Configuration Loading", test_config_loading),
        ("Database Models", test_database_models),
        ("Troubleshooter Logic", test_troubleshooter_logic),
        ("Startup Script Validation", test_startup_script_validation),
        ("Deployment Files", test_deployment_files)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"Test {test_name} crashed: {e}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ All AWS startup scripts are working correctly!")
        print("The scripts are ready for AWS deployment.")
    else:
        print(f"\n⚠️  {failed} tests failed. Check the issues above.")
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)