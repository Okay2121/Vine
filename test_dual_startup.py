#!/usr/bin/env python3
"""
Test Script for Dual Startup System
===================================
This script verifies that the bot startup system works correctly in both environments.
"""

import os
import sys
import subprocess
import time

def test_environment_detection():
    """Test the environment detection logic"""
    print("=== ENVIRONMENT DETECTION TEST ===")
    
    # Test direct execution detection
    print("Testing direct execution detection...")
    result = subprocess.run([
        sys.executable, "-c", 
        "from bot_v20_runner import is_aws_execution; print(f'AWS execution mode: {is_aws_execution}')"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {result.stdout.strip()}")
    else:
        print(f"❌ Error: {result.stderr.strip()}")
    
    # Test .env file detection
    env_exists = os.path.exists('.env')
    print(f"✅ .env file exists: {env_exists}")
    
    # Test environment variables
    replit_indicators = ['REPLIT_CLUSTER', 'REPL_ID', 'REPLIT_DOMAIN']
    replit_detected = any(os.environ.get(indicator) for indicator in replit_indicators)
    print(f"✅ Replit environment detected: {replit_detected}")

def test_bot_token_loading():
    """Test that bot token loads correctly"""
    print("\n=== BOT TOKEN LOADING TEST ===")
    
    try:
        from config import BOT_TOKEN
        if BOT_TOKEN:
            print(f"✅ Bot token loaded successfully (ending in ...{BOT_TOKEN[-5:]})")
            return True
        else:
            print("❌ Bot token is empty")
            return False
    except Exception as e:
        print(f"❌ Error loading bot token: {e}")
        return False

def test_dotenv_functionality():
    """Test .env loading functionality"""
    print("\n=== DOTENV FUNCTIONALITY TEST ===")
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv is available")
        
        # Test loading a dummy .env
        test_env_content = "TEST_VAR=test_value\n"
        with open('.env.test', 'w') as f:
            f.write(test_env_content)
        
        load_dotenv('.env.test')
        test_value = os.environ.get('TEST_VAR')
        
        if test_value == 'test_value':
            print("✅ .env loading works correctly")
            os.remove('.env.test')
            return True
        else:
            print("❌ .env loading failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing dotenv: {e}")
        return False

def test_aws_startup_mode():
    """Test AWS startup mode simulation"""
    print("\n=== AWS STARTUP MODE TEST ===")
    
    # This simulates what happens when running `python bot_v20_runner.py`
    print("Simulating AWS startup mode...")
    
    # Test that the main function exists and is callable
    try:
        # Import without executing
        import importlib.util
        spec = importlib.util.spec_from_file_location("bot_runner", "bot_v20_runner.py")
        module = importlib.util.module_from_spec(spec)
        
        # Check if main function exists
        spec.loader.exec_module(module)
        if hasattr(module, 'main'):
            print("✅ AWS main() function exists and is importable")
            return True
        else:
            print("❌ AWS main() function not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing AWS mode: {e}")
        return False

def test_import_safety():
    """Test that importing bot_v20_runner doesn't auto-start the bot"""
    print("\n=== IMPORT SAFETY TEST ===")
    
    try:
        # This should not start the bot automatically
        print("Testing safe import...")
        result = subprocess.run([
            sys.executable, "-c", 
            "import bot_v20_runner; print('Import successful without auto-start')"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Bot module imports safely without auto-starting")
            return True
        else:
            print(f"❌ Import failed: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Import caused hanging (possible auto-start)")
        return False
    except Exception as e:
        print(f"❌ Error testing import safety: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 DUAL STARTUP SYSTEM TEST SUITE")
    print("Testing environment-aware startup behavior")
    print("=" * 60)
    
    tests = [
        test_environment_detection,
        test_bot_token_loading,
        test_dotenv_functionality,
        test_aws_startup_mode,
        test_import_safety
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! Dual startup system is working correctly.")
        print("\nStartup Instructions:")
        print("• Replit: Auto-start when remixed (handled by main.py)")
        print("• AWS: Execute `python bot_v20_runner.py` directly")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)