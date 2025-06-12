# AWS Deployment Guide for Solana Memecoin Trading Bot

## Overview
This guide explains how to deploy your bot on AWS with the new environment-aware startup system that prevents conflicts and ensures clean operation.

## Environment-Aware Startup System

### How It Works
The bot now automatically detects its environment and adjusts startup behavior:

- **Replit Environment**: Auto-start enabled for remix compatibility
- **AWS/Production**: Manual start required to prevent conflicts

### Environment Detection
The system checks for these indicators:
- Replit: `REPLIT_CLUSTER`, `REPL_ID`, `REPLIT_DB_URL`
- AWS: `AWS_REGION`, `AWS_EXECUTION_ENV`
- Manual: `BOT_ENVIRONMENT=aws` (override)

## AWS Deployment Steps

### 1. Prepare Your Environment
```bash
# Set environment variable to disable auto-start
export BOT_ENVIRONMENT=aws

# Set required variables
export TELEGRAM_BOT_TOKEN=your_bot_token
export DATABASE_URL=your_postgresql_url
```

### 2. Manual Bot Startup Options

#### Option A: Using the Manual Starter (Recommended)
```bash
python start_bot_manual.py
```

This script:
- Sets environment to manual mode
- Prevents auto-start conflicts
- Includes health monitoring
- Handles shutdown gracefully

#### Option B: Direct Command
```bash
python main.py
```

#### Option C: Using Process Manager
```bash
# With PM2
pm2 start start_bot_manual.py --name "solana-bot"

# With systemd
sudo systemctl start solana-bot
```

### 3. Health Monitoring Endpoints

Check bot status via web endpoints:
- `/health` - Basic health check
- `/` - Environment and startup status
- `/database/health` - Database status

### 4. Production Configuration

#### Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_token
DATABASE_URL=postgresql://...

# Optional - Force environment detection
BOT_ENVIRONMENT=aws  # or 'replit'

# AWS-specific (if applicable)
AWS_REGION=us-east-1
```

#### Systemd Service (Ubuntu/CentOS)
Create `/etc/systemd/system/solana-bot.service`:
```ini
[Unit]
Description=Solana Memecoin Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/solana-bot
Environment=BOT_ENVIRONMENT=aws
Environment=TELEGRAM_BOT_TOKEN=your_token
Environment=DATABASE_URL=your_db_url
ExecStart=/usr/bin/python3 start_bot_manual.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable solana-bot
sudo systemctl start solana-bot
```

## Verification

### 1. Check Environment Detection
```bash
curl http://localhost:5000/
```

Should return:
```json
{
  "status": "online",
  "environment": "aws/manual",
  "auto_start_enabled": false,
  "bot_status": "manual start required"
}
```

### 2. Verify Bot is Running
```bash
curl http://localhost:5000/health
```

### 3. Test Telegram Commands
Send `/start` to your bot to verify it responds.

## Troubleshooting

### Bot Not Starting
1. Check environment variables: `env | grep -E "(TELEGRAM|DATABASE|BOT_)"`
2. Check logs: `tail -f /var/log/solana-bot.log`
3. Verify database connection: `curl http://localhost:5000/database/health`

### Multiple Instance Conflicts
The bot now prevents multiple instances automatically. If you see "Another bot instance is already running":
1. Stop all bot processes
2. Wait 30 seconds
3. Start using the manual starter

### Environment Detection Issues
Force environment detection:
```bash
export BOT_ENVIRONMENT=aws
python start_bot_manual.py
```

## Benefits of This System

### For Replit Users
- Auto-start works seamlessly for remixes
- No configuration required
- Instant deployment

### For AWS/Production Users
- No accidental auto-start conflicts
- Clean manual control
- Production-ready monitoring
- Proper shutdown handling

### For Developers
- Single codebase works everywhere
- No duplicate startup logic
- Clear environment separation
- Easy debugging and testing