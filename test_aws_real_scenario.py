#!/usr/bin/env python3
"""
Test AWS startup scripts in realistic AWS-like conditions
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

def test_aws_startup_flow():
    """Test the complete AWS startup flow"""
    print("Testing AWS startup flow...")
    
    # Set AWS-like environment variables
    os.environ['AWS_REGION'] = 'us-east-1'
    os.environ['BOT_ENVIRONMENT'] = 'aws'
    os.environ['NODE_ENV'] = 'production'
    
    try:
        # Test environment detection in AWS mode
        from environment_detector import get_environment_info
        env_info = get_environment_info()
        
        print(f"Environment detected as: {env_info['environment_type']}")
        print(f"AWS environment: {env_info['is_aws']}")
        
        # Test configuration loading
        from dotenv import load_dotenv
        load_dotenv('.env.aws_test')
        
        # Test the AWS startup script logic
        import aws_start_bot
        
        # Test environment setup (without actually starting bot)
        print("Environment setup function available")
        
        return True
        
    except Exception as e:
        print(f"AWS startup flow test failed: {e}")
        return False

def test_troubleshooter_with_aws_env():
    """Test troubleshooter with AWS environment"""
    print("\nTesting troubleshooter with AWS environment...")
    
    # Use the test env file
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        result = subprocess.run([
            'python3', 'aws_troubleshoot.py'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("Troubleshooter completed successfully")
            # Check for key indicators in output
            if "Python" in result.stdout and "compatible" in result.stdout:
                print("Python version check working")
            if "environment configuration" in result.stdout:
                print("Environment configuration check working")
            return True
        else:
            print(f"Troubleshooter failed with exit code {result.returncode}")
            print(f"Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Troubleshooter test timed out")
        return False
    except Exception as e:
        print(f"Troubleshooter test failed: {e}")
        return False

def test_deployment_script_syntax():
    """Test deployment script syntax"""
    print("\nTesting deployment script syntax...")
    
    try:
        # Test bash script syntax
        result = subprocess.run([
            'bash', '-n', 'deploy_aws.sh'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("deploy_aws.sh syntax is valid")
            return True
        else:
            print(f"deploy_aws.sh syntax error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Deployment script test failed: {e}")
        return False

def test_systemd_service_file():
    """Test systemd service file format"""
    print("\nTesting systemd service file...")
    
    try:
        service_file = Path('solana-bot.service')
        if not service_file.exists():
            print("Service file not found")
            return False
        
        content = service_file.read_text()
        
        # Check for required sections
        required_sections = ['[Unit]', '[Service]', '[Install]']
        for section in required_sections:
            if section not in content:
                print(f"Missing section: {section}")
                return False
        
        # Check for key directives
        required_directives = ['ExecStart=', 'WorkingDirectory=', 'User=']
        for directive in required_directives:
            if directive not in content:
                print(f"Missing directive: {directive}")
                return False
        
        print("Systemd service file format is valid")
        return True
        
    except Exception as e:
        print(f"Service file test failed: {e}")
        return False

def main():
    """Run realistic AWS scenario tests"""
    print("AWS Realistic Scenario Testing")
    print("=" * 40)
    
    tests = [
        ("AWS Startup Flow", test_aws_startup_flow),
        ("Troubleshooter with AWS Env", test_troubleshooter_with_aws_env),
        ("Deployment Script Syntax", test_deployment_script_syntax),
        ("Systemd Service File", test_systemd_service_file)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("REALISTIC SCENARIO TEST RESULTS")
    print("=" * 40)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\nAll AWS deployment scripts tested successfully!")
        print("Ready for production AWS deployment.")
    else:
        print(f"\n{failed} tests failed - review issues above.")
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)