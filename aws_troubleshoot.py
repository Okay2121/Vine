#!/usr/bin/env python3
"""
AWS Startup Troubleshooter
=========================
Diagnoses common AWS deployment issues and provides fixes
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("1. Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        print(f"   ✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
        return False

def check_environment_file():
    """Check if .env file exists and has required variables"""
    print("2. Checking environment configuration...")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("   ✗ .env file not found")
        print("   → Create .env file with required variables")
        return False
    
    print("   ✓ .env file exists")
    
    # Check required variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL', 
        'SESSION_SECRET'
    ]
    
    # Load .env content to check
    try:
        content = env_file.read_text()
        missing_vars = []
        
        for var in required_vars:
            if f"{var}=" not in content or f"{var}=your_" in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"   ✗ Missing or placeholder values: {', '.join(missing_vars)}")
            return False
        else:
            print("   ✓ All required environment variables present")
            return True
            
    except Exception as e:
        print(f"   ✗ Error reading .env file: {e}")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    print("3. Checking Python dependencies...")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'python_dotenv', 
        'psycopg2',
        'requests',
        'telegram'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"   ✓ {package}")
        except ImportError:
            print(f"   ✗ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"   → Install missing packages: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_database_connection():
    """Test database connectivity"""
    print("4. Checking database connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from app import app, db
        from models import User
        
        with app.app_context():
            user_count = User.query.count()
            print(f"   ✓ Database connected ({user_count} users)")
            return True
            
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        print("   → Check DATABASE_URL in .env file")
        print("   → Ensure PostgreSQL is running")
        return False

def check_telegram_token():
    """Verify Telegram bot token"""
    print("5. Checking Telegram bot token...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("   ✗ TELEGRAM_BOT_TOKEN not found")
            return False
        
        if bot_token.startswith('your_'):
            print("   ✗ Bot token is placeholder value")
            return False
        
        # Test token format
        if ':' not in bot_token or len(bot_token) < 40:
            print("   ✗ Bot token format invalid")
            return False
        
        # Test token with Telegram API
        import requests
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"   ✓ Bot token valid (@{bot_info.get('username', 'unknown')})")
                return True
            else:
                print(f"   ✗ Telegram API error: {data.get('description')}")
                return False
        else:
            print(f"   ✗ HTTP {response.status_code} from Telegram API")
            return False
            
    except Exception as e:
        print(f"   ✗ Token verification failed: {e}")
        return False

def check_file_permissions():
    """Check file permissions"""
    print("6. Checking file permissions...")
    
    files_to_check = [
        'aws_start_bot.py',
        'bot_v20_runner.py', 
        'deploy_aws.sh'
    ]
    
    issues = []
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            if os.access(file_path, os.R_OK):
                print(f"   ✓ {file_path} readable")
            else:
                print(f"   ✗ {file_path} not readable")
                issues.append(f"chmod +r {file_path}")
        else:
            print(f"   ✗ {file_path} not found")
            issues.append(f"File {file_path} missing")
    
    if issues:
        print("   → Fix permissions with:", "; ".join(issues))
        return False
    
    return True

def check_port_availability():
    """Check if required ports are available"""
    print("7. Checking port availability...")
    
    try:
        import socket
        
        # Check port 5000 (Flask)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        
        if result == 0:
            print("   ✗ Port 5000 already in use")
            print("   → Stop other services using port 5000")
            return False
        else:
            print("   ✓ Port 5000 available")
            return True
            
    except Exception as e:
        print(f"   ✗ Port check failed: {e}")
        return False

def generate_fixes():
    """Generate common fixes for AWS deployment"""
    print("\n" + "="*50)
    print("COMMON FIXES FOR AWS DEPLOYMENT")
    print("="*50)
    
    print("\n1. Install dependencies:")
    print("   pip install -r requirements.txt")
    
    print("\n2. Create proper .env file:")
    print("   cp .env.production .env")
    print("   nano .env  # Edit with your values")
    
    print("\n3. Setup database:")
    print("   sudo -u postgres createdb solana_bot")
    print("   python -c \"from app import app, db; app.app_context().push(); db.create_all()\"")
    
    print("\n4. Use the simplified starter:")
    print("   python3 aws_start_bot.py")
    
    print("\n5. For production deployment:")
    print("   sudo ./deploy_aws.sh")
    
    print("\n6. Enable as system service:")
    print("   sudo systemctl enable solana-bot")
    print("   sudo systemctl start solana-bot")

def main():
    """Run comprehensive AWS troubleshooting"""
    print("AWS Deployment Troubleshooter")
    print("="*50)
    
    checks = [
        check_python_version,
        check_environment_file,
        check_dependencies, 
        check_database_connection,
        check_telegram_token,
        check_file_permissions,
        check_port_availability
    ]
    
    passed = 0
    failed = 0
    
    for check in checks:
        try:
            if check():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ✗ Check failed with error: {e}")
            failed += 1
        print()
    
    print("="*50)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*50)
    
    if failed > 0:
        generate_fixes()
        print(f"\nFix the {failed} failed checks above, then try:")
        print("python3 aws_start_bot.py")
    else:
        print("\nAll checks passed! Your bot should start with:")
        print("python3 aws_start_bot.py")

if __name__ == '__main__':
    main()