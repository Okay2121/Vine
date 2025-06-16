#!/usr/bin/env python3
"""
Test production AWS configuration
"""

import os
import sys
import requests
from dotenv import load_dotenv

def test_production_env():
    """Test the production environment configuration"""
    print("Testing production AWS configuration...")
    
    # Load production environment
    load_dotenv('.env.aws_production', override=True)
    
    # Test required variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL',
        'SESSION_SECRET',
        'ADMIN_USER_ID'
    ]
    
    print("\n1. Environment Variables Check:")
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            if var == 'TELEGRAM_BOT_TOKEN':
                print(f"   ✓ {var}: {value[:10]}...{value[-5:]}")
            elif var == 'DATABASE_URL':
                print(f"   ✓ {var}: postgresql://...{value.split('@')[1] if '@' in value else 'configured'}")
            elif var == 'SESSION_SECRET':
                print(f"   ✓ {var}: {len(value)} characters")
            else:
                print(f"   ✓ {var}: {value}")
        else:
            print(f"   ✗ {var}: Missing")
            return False
    
    return True

def test_telegram_token():
    """Test Telegram bot token validity"""
    print("\n2. Telegram Bot Token Validation:")
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("   ✗ No bot token found")
        return False
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                username = bot_info.get('username', 'unknown')
                first_name = bot_info.get('first_name', 'unknown')
                print(f"   ✓ Bot token valid: @{username} ({first_name})")
                return True
            else:
                print(f"   ✗ Telegram API error: {data.get('description')}")
                return False
        else:
            print(f"   ✗ HTTP {response.status_code} from Telegram API")
            return False
            
    except requests.exceptions.Timeout:
        print("   ✗ Telegram API timeout")
        return False
    except Exception as e:
        print(f"   ✗ Telegram API error: {e}")
        return False

def test_database_url():
    """Test database URL format"""
    print("\n3. Database URL Validation:")
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("   ✗ No database URL found")
        return False
    
    # Check URL format
    if not db_url.startswith('postgresql://'):
        print("   ✗ Database URL should start with postgresql://")
        return False
    
    # Check for required components
    if '@' not in db_url:
        print("   ✗ Database URL missing credentials")
        return False
    
    if 'neon.tech' in db_url:
        print("   ✓ Neon database URL format valid")
        if 'sslmode=require' in db_url:
            print("   ✓ SSL mode configured")
        else:
            print("   ⚠ SSL mode not explicitly set")
    else:
        print("   ✓ Database URL format appears valid")
    
    return True

def test_config_loading():
    """Test configuration loading"""
    print("\n4. Configuration Loading Test:")
    
    try:
        # Test config.py loading
        import config
        
        print(f"   ✓ BOT_TOKEN loaded: {'Yes' if config.BOT_TOKEN else 'No'}")
        print(f"   ✓ DATABASE_URL loaded: {'Yes' if config.DATABASE_URL else 'No'}")
        print(f"   ✓ ADMIN_USER_ID: {config.ADMIN_USER_ID}")
        print(f"   ✓ MIN_DEPOSIT: {config.MIN_DEPOSIT}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Configuration loading failed: {e}")
        return False

def test_aws_startup_readiness():
    """Test AWS startup script readiness"""
    print("\n5. AWS Startup Readiness:")
    
    try:
        # Test aws_start_bot.py imports
        import aws_start_bot
        print("   ✓ AWS startup script imports successfully")
        
        # Test environment detector
        from environment_detector import get_environment_info
        env_info = get_environment_info()
        print(f"   ✓ Environment detection working: {env_info['environment_type']}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ AWS startup test failed: {e}")
        return False

def main():
    """Run production configuration tests"""
    print("Production AWS Configuration Test")
    print("=" * 50)
    
    tests = [
        test_production_env,
        test_telegram_token,
        test_database_url,
        test_config_loading,
        test_aws_startup_readiness
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"Test failed with error: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    print("PRODUCTION CONFIG TEST RESULTS")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ Production configuration is ready for AWS deployment!")
        print("\nYou can now run on AWS:")
        print("  python3 aws_start_bot.py")
    else:
        print(f"\n⚠️ {total - passed} tests failed - review configuration")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)