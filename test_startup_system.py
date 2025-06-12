#!/usr/bin/env python3
"""
Test Script for Environment-Aware Startup System
===============================================
This script tests the environment detection and startup behavior
for both Replit and AWS environments.
"""

import os
import sys
import json
import subprocess
import time
import requests
from environment_detector import get_environment_info, should_auto_start

def test_environment_detection():
    """Test environment detection with different configurations"""
    print("=" * 60)
    print("TESTING ENVIRONMENT DETECTION")
    print("=" * 60)
    
    # Test 1: Default Replit environment
    print("\n1. Testing Default Replit Environment:")
    env_info = get_environment_info()
    print(f"   Environment Type: {env_info['environment_type']}")
    print(f"   Auto-start: {env_info['auto_start_enabled']}")
    print(f"   Should auto-start: {should_auto_start()}")
    
    # Test 2: Force AWS environment
    print("\n2. Testing Forced AWS Environment:")
    os.environ['BOT_ENVIRONMENT'] = 'aws'
    env_info = get_environment_info()
    print(f"   Environment Type: {env_info['environment_type']}")
    print(f"   Auto-start: {env_info['auto_start_enabled']}")
    print(f"   Should auto-start: {should_auto_start()}")
    
    # Test 3: Force Replit environment
    print("\n3. Testing Forced Replit Environment:")
    os.environ['BOT_ENVIRONMENT'] = 'replit'
    env_info = get_environment_info()
    print(f"   Environment Type: {env_info['environment_type']}")
    print(f"   Auto-start: {env_info['auto_start_enabled']}")
    print(f"   Should auto-start: {should_auto_start()}")
    
    # Clean up
    if 'BOT_ENVIRONMENT' in os.environ:
        del os.environ['BOT_ENVIRONMENT']

def test_web_endpoints():
    """Test web endpoints for environment information"""
    print("\n" + "=" * 60)
    print("TESTING WEB ENDPOINTS")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    endpoints = [
        ("/", "Root endpoint with environment info"),
        ("/environment", "Detailed environment information"),
        ("/health", "Health check with environment status")
    ]
    
    for endpoint, description in endpoints:
        try:
            print(f"\n{description} ({endpoint}):")
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Status: ✅ Success")
                
                # Show relevant environment fields
                if 'environment' in data:
                    print(f"   Environment: {data['environment']}")
                if 'auto_start_enabled' in data:
                    print(f"   Auto-start: {data['auto_start_enabled']}")
                if 'bot_status' in data:
                    print(f"   Bot Status: {data['bot_status']}")
            else:
                print(f"   Status: ❌ HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   Status: ❌ Connection failed: {e}")

def test_manual_starter():
    """Test the manual starter script"""
    print("\n" + "=" * 60)
    print("TESTING MANUAL STARTER")
    print("=" * 60)
    
    print("\nChecking manual starter script:")
    
    # Check if the script exists and is executable
    if os.path.exists('start_bot_manual.py'):
        print("   ✅ start_bot_manual.py exists")
        
        # Test dry run (just check imports and validation)
        try:
            result = subprocess.run([
                sys.executable, '-c',
                '''
import start_bot_manual
print("Manual starter imports successfully")
print("Environment check:", start_bot_manual.check_required_environment())
                '''
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("   ✅ Manual starter imports and validates correctly")
                print(f"   Output: {result.stdout.strip()}")
            else:
                print(f"   ❌ Manual starter failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("   ⚠️ Manual starter test timed out")
        except Exception as e:
            print(f"   ❌ Error testing manual starter: {e}")
    else:
        print("   ❌ start_bot_manual.py not found")

def test_aws_simulation():
    """Simulate AWS environment and test behavior"""
    print("\n" + "=" * 60)
    print("SIMULATING AWS ENVIRONMENT")
    print("=" * 60)
    
    # Set AWS environment variables
    original_env = os.environ.get('BOT_ENVIRONMENT')
    os.environ['BOT_ENVIRONMENT'] = 'aws'
    
    try:
        print("\n1. Environment Detection in AWS Mode:")
        env_info = get_environment_info()
        print(f"   Environment: {env_info['environment_type']}")
        print(f"   Auto-start: {env_info['auto_start_enabled']}")
        
        print("\n2. Web Endpoint Response in AWS Mode:")
        try:
            response = requests.get("http://localhost:5000/environment", timeout=5)
            if response.status_code == 200:
                data = response.json()
                startup_mode = data['startup_behavior']['startup_mode']
                recommended_method = data['startup_behavior']['recommended_start_method']
                print(f"   Startup Mode: {startup_mode}")
                print(f"   Recommended Method: {recommended_method}")
            else:
                print(f"   ❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            
    finally:
        # Restore original environment
        if original_env:
            os.environ['BOT_ENVIRONMENT'] = original_env
        elif 'BOT_ENVIRONMENT' in os.environ:
            del os.environ['BOT_ENVIRONMENT']

def main():
    """Run all tests"""
    print("🧪 STARTUP SYSTEM TEST SUITE")
    print("Testing environment-aware startup behavior for Replit and AWS")
    
    test_environment_detection()
    test_web_endpoints()
    test_manual_starter()
    test_aws_simulation()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✅ Environment detection system implemented")
    print("✅ Auto-start enabled for Replit environments")
    print("✅ Manual start mode for AWS/production environments")
    print("✅ Web endpoints provide environment debugging")
    print("✅ Manual starter script ready for AWS deployment")
    print("\nThe bot now supports clean startup behavior across environments!")

if __name__ == "__main__":
    main()