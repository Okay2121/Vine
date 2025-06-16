# AWS Deployment Startup Guide

## Quick Start Commands

### Option 1: Simplified Startup (Recommended)
```bash
python3 aws_start_bot.py
```

### Option 2: Full Deployment Setup
```bash
chmod +x deploy_aws.sh
sudo ./deploy_aws.sh
```

### Option 3: Manual Commands
```bash
# Load environment
source .env

# Start bot directly
python3 bot_v20_runner.py
```

## Why `python bot_v20_runner.py` Fails on AWS

The original command fails because:

1. **Missing Environment Setup**: AWS requires explicit .env file loading
2. **Database Connection**: PostgreSQL needs proper configuration
3. **Dependencies**: Missing python-dotenv and other packages
4. **Permissions**: File execution permissions not set
5. **Service Management**: No process management for production

## Step-by-Step AWS Setup

### 1. System Requirements
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib
```

### 2. Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### 3. Database Configuration
```bash
# Setup PostgreSQL
sudo -u postgres createdb solana_bot
sudo -u postgres psql -c "CREATE USER solana_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE solana_bot TO solana_user;"
```

### 4. Environment Variables
Create `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_actual_bot_token
DATABASE_URL=postgresql://solana_user:your_password@localhost/solana_bot
SESSION_SECRET=your_session_secret
ADMIN_USER_ID=your_telegram_id
```

### 5. Start the Bot

#### Method A: Direct Start (Testing)
```bash
python3 aws_start_bot.py
```

#### Method B: System Service (Production)
```bash
# Copy service file
sudo cp solana-bot.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable solana-bot
sudo systemctl start solana-bot

# Check status
sudo systemctl status solana-bot
```

## Troubleshooting

### Run Diagnostics
```bash
python3 aws_troubleshoot.py
```

### Common Issues and Fixes

#### 1. "ModuleNotFoundError: No module named 'dotenv'"
```bash
pip install python-dotenv
```

#### 2. "TELEGRAM_BOT_TOKEN not found"
```bash
# Check .env file exists
ls -la .env

# Verify content
cat .env | grep TELEGRAM_BOT_TOKEN
```

#### 3. Database Connection Failed
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U solana_user -d solana_bot
```

#### 4. Permission Denied
```bash
chmod +x aws_start_bot.py
chmod +x deploy_aws.sh
```

#### 5. Port Already in Use
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill process if needed
sudo kill -9 <PID>
```

### View Logs
```bash
# For systemd service
sudo journalctl -u solana-bot -f

# For direct execution
python3 aws_start_bot.py 2>&1 | tee bot.log
```

## Startup Command Summary

| Command | Use Case | Requirements |
|---------|----------|--------------|
| `python3 aws_start_bot.py` | Quick testing | .env file, dependencies |
| `sudo ./deploy_aws.sh` | Full production setup | Fresh AWS server |
| `systemctl start solana-bot` | Production service | After deploy_aws.sh |
| `python3 aws_troubleshoot.py` | Diagnostics | Any time |

## Environment Detection

The bot automatically detects the environment:
- **Replit**: Uses built-in environment variables
- **AWS**: Loads from .env file
- **Local**: Uses system environment

## Security Notes

1. Never commit .env file to git
2. Use strong passwords for database
3. Configure firewall appropriately
4. Run as non-root user
5. Use systemd for process management

## Support

If issues persist:
1. Run the troubleshooter: `python3 aws_troubleshoot.py`
2. Check logs: `sudo journalctl -u solana-bot -f`
3. Verify all environment variables are set correctly
4. Ensure database is accessible