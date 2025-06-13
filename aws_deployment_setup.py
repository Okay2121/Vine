#!/usr/bin/env python3
"""
AWS Deployment Setup Script
===========================
Ensures proper environment variable loading and creates deployment files
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def ensure_env_loading():
    """Ensure .env loading is present in all critical files"""
    
    # Files that need .env loading
    critical_files = [
        'main.py',
        'app.py', 
        'bot_v20_runner.py',
        'deployment_config.py',
        'config.py'
    ]
    
    env_loading_code = """
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
"""
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if dotenv loading is already present
            if 'load_dotenv()' not in content:
                print(f"Adding .env loading to {file_path}")
                
                # Find the best place to insert (after imports but before main code)
                lines = content.split('\n')
                insert_index = 0
                
                # Find the last import line
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        insert_index = i + 1
                
                # Insert the env loading code
                lines.insert(insert_index, env_loading_code)
                
                # Write back to file
                with open(file_path, 'w') as f:
                    f.write('\n'.join(lines))
            else:
                print(f"✓ {file_path} already has .env loading")

def create_production_env():
    """Create .env.production template for AWS deployment"""
    
    production_env_content = """# Production Environment Variables for AWS Deployment
# Copy this file to .env on your AWS server

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_admin_user_id_here

# Database Configuration 
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require

# Bot Settings
MIN_DEPOSIT=0.5
GLOBAL_DEPOSIT_WALLET=your_solana_wallet_address_here
SUPPORT_USERNAME=YourSupportUsername

# Session Secret for Flask (generate a strong random key)
SESSION_SECRET=your_super_secret_session_key_here_change_in_production

# Production Environment Flag
BOT_ENVIRONMENT=aws
NODE_ENV=production

# Optional: Logging Level
LOG_LEVEL=INFO
"""
    
    with open('.env.production', 'w') as f:
        f.write(production_env_content)
    
    print("✓ Created .env.production template")

def create_aws_startup_script():
    """Create startup script for AWS deployment"""
    
    startup_script = """#!/bin/bash
# AWS Deployment Startup Script
# Make this file executable: chmod +x start_aws.sh

echo "Starting Solana Memecoin Bot on AWS..."

# Ensure we're in the correct directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(cat .env | grep -v ^# | xargs)
else
    echo "Warning: .env file not found"
fi

# Set production environment
export BOT_ENVIRONMENT=aws
export NODE_ENV=production

# Install/update dependencies if needed
if [ -f requirements.txt ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Run database migrations if needed
echo "Setting up database..."
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database setup complete')"

# Start the Flask application
echo "Starting Flask application..."
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --keep-alive 5 main:app &

# Start the Telegram bot
echo "Starting Telegram bot..."
python bot_v20_runner.py &

# Wait for all background processes
wait

echo "Application started successfully!"
"""
    
    with open('start_aws.sh', 'w') as f:
        f.write(startup_script)
    
    # Make the script executable
    os.chmod('start_aws.sh', 0o755)
    
    print("✓ Created start_aws.sh startup script")

def create_systemd_service():
    """Create systemd service file for AWS deployment"""
    
    service_content = """[Unit]
Description=Solana Memecoin Trading Bot
After=network.target
Wants=network.target

[Service]
Type=forking
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/solana-memecoin-bot
Environment=BOT_ENVIRONMENT=aws
Environment=NODE_ENV=production
EnvironmentFile=/home/ubuntu/solana-memecoin-bot/.env
ExecStart=/home/ubuntu/solana-memecoin-bot/start_aws.sh
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    with open('solana-memecoin-bot.service', 'w') as f:
        f.write(service_content)
    
    print("✓ Created systemd service file")

def create_requirements_txt():
    """Ensure requirements.txt exists with all dependencies"""
    
    requirements = """flask>=2.3.0
flask-sqlalchemy>=3.0.0
python-telegram-bot>=20.0
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0
gunicorn>=21.0.0
sqlalchemy>=2.0.0
requests>=2.31.0
schedule>=1.2.0
pillow>=10.0.0
qrcode>=7.4.0
aiohttp>=3.8.0
trafilatura>=1.6.0
psutil>=5.9.0
alembic>=1.12.0
email-validator>=2.0.0
werkzeug>=2.3.0
"""
    
    if not os.path.exists('requirements.txt'):
        with open('requirements.txt', 'w') as f:
            f.write(requirements)
        print("✓ Created requirements.txt")
    else:
        print("✓ requirements.txt already exists")

def create_deployment_guide():
    """Create comprehensive AWS deployment guide"""
    
    guide_content = """# AWS Deployment Guide

## Prerequisites
1. AWS EC2 instance (Ubuntu 20.04+ recommended)
2. PostgreSQL database (AWS RDS or external like Neon)
3. Telegram Bot Token
4. Domain name (optional)

## Deployment Steps

### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx -y

# Create application user
sudo useradd -m -s /bin/bash botuser
sudo usermod -aG sudo botuser
```

### 2. Application Deployment
```bash
# Switch to bot user
sudo su - botuser

# Clone or upload your application
git clone <your-repo> solana-memecoin-bot
cd solana-memecoin-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
# Copy and configure environment file
cp .env.production .env

# Edit .env with your actual values
nano .env

# Make sure these variables are set:
# - TELEGRAM_BOT_TOKEN
# - ADMIN_USER_ID  
# - DATABASE_URL
# - SESSION_SECRET
```

### 4. Database Setup
```bash
# Test database connection
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database OK')"
```

### 5. Service Installation
```bash
# Copy service file
sudo cp solana-memecoin-bot.service /etc/systemd/system/

# Update service file paths if needed
sudo nano /etc/systemd/system/solana-memecoin-bot.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable solana-memecoin-bot
sudo systemctl start solana-memecoin-bot

# Check status
sudo systemctl status solana-memecoin-bot
```

### 6. Nginx Configuration (Optional)
```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/solana-memecoin-bot

# Add this configuration:
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/solana-memecoin-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Management Commands

### Start/Stop Service
```bash
sudo systemctl start solana-memecoin-bot
sudo systemctl stop solana-memecoin-bot
sudo systemctl restart solana-memecoin-bot
```

### View Logs
```bash
sudo journalctl -u solana-memecoin-bot -f
```

### Manual Start (for testing)
```bash
cd /home/botuser/solana-memecoin-bot
source venv/bin/activate
./start_aws.sh
```

## Troubleshooting

### Check Environment Loading
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('TOKEN:', os.getenv('TELEGRAM_BOT_TOKEN')[:10] if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT FOUND')"
```

### Test Database Connection
```bash
python aws_deployment_checklist.py
```

### Check Service Status
```bash
sudo systemctl status solana-memecoin-bot
sudo journalctl -u solana-memecoin-bot --no-pager -l
```
"""
    
    with open('AWS_DEPLOYMENT_COMMANDS.md', 'w') as f:
        f.write(guide_content)
    
    print("✓ Created AWS_DEPLOYMENT_COMMANDS.md")

def main():
    """Run all setup tasks"""
    print("=== AWS Deployment Setup ===")
    
    # Ensure environment loading in all files
    ensure_env_loading()
    
    # Create deployment files
    create_production_env()
    create_aws_startup_script()
    create_systemd_service()
    create_requirements_txt()
    create_deployment_guide()
    
    print("\n✅ AWS Deployment Setup Complete!")
    print("\nNext steps:")
    print("1. Review .env.production and update with your values")
    print("2. Copy your application to AWS server")
    print("3. Follow AWS_DEPLOYMENT_COMMANDS.md guide")
    print("4. Run: python aws_deployment_checklist.py to verify setup")

if __name__ == "__main__":
    main()