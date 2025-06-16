#!/bin/bash
# Complete AWS Deployment Script for Solana Trading Bot
# Run this script on your AWS server to set up everything

set -e  # Exit on any error

echo "=================================="
echo "AWS Deployment Setup for Solana Bot"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root. Use a regular user with sudo privileges."
    exit 1
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git curl

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    print_warning "requirements.txt not found, installing basic dependencies..."
    pip install flask flask-sqlalchemy gunicorn python-dotenv psycopg2-binary requests python-telegram-bot
fi

# Setup PostgreSQL database
print_status "Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE solana_bot;" 2>/dev/null || print_warning "Database may already exist"
sudo -u postgres psql -c "CREATE USER solana_user WITH PASSWORD 'secure_password_123';" 2>/dev/null || print_warning "User may already exist"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE solana_bot TO solana_user;" 2>/dev/null || true

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_status "Creating .env file template..."
    cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_id_here

# Database Configuration
DATABASE_URL=postgresql://solana_user:secure_password_123@localhost/solana_bot

# Flask Configuration
SESSION_SECRET=$(openssl rand -base64 32)

# Solana Configuration
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
GLOBAL_DEPOSIT_WALLET=2pWHfMgpLtcnJpeFRzuRqXxAxBs2qjhU46xkdb5dCSzD

# Environment
BOT_ENVIRONMENT=aws
NODE_ENV=production
EOF
    print_warning "Please edit .env file with your actual values before starting the bot!"
else
    print_status ".env file already exists"
fi

# Make scripts executable
print_status "Making scripts executable..."
chmod +x aws_start_bot.py
chmod +x start_aws.sh 2>/dev/null || true

# Test database connection
print_status "Testing database connection..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from app import app, db
with app.app_context():
    db.create_all()
    print('Database setup complete!')
" || print_error "Database setup failed - please check your configuration"

# Setup systemd service
print_status "Setting up systemd service..."
sudo cp solana-bot.service /etc/systemd/system/
sudo sed -i "s|/home/ubuntu/solana-bot|$(pwd)|g" /etc/systemd/system/solana-bot.service
sudo sed -i "s|User=ubuntu|User=$(whoami)|g" /etc/systemd/system/solana-bot.service
sudo sed -i "s|Group=ubuntu|Group=$(whoami)|g" /etc/systemd/system/solana-bot.service
sudo systemctl daemon-reload

# Setup basic firewall
print_status "Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow 5000
sudo ufw --force enable

print_status "Deployment setup complete!"
echo ""
echo "=================================="
echo "Next Steps:"
echo "=================================="
echo "1. Edit .env file with your actual values:"
echo "   nano .env"
echo ""
echo "2. Start the bot manually to test:"
echo "   python3 aws_start_bot.py"
echo ""
echo "3. Or enable as system service:"
echo "   sudo systemctl enable solana-bot"
echo "   sudo systemctl start solana-bot"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status solana-bot"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u solana-bot -f"
echo "=================================="