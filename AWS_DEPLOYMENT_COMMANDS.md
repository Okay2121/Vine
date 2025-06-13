# AWS Deployment Guide

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
