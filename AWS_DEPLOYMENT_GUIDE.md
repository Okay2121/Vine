# AWS Deployment Guide for Telegram Trading Bot

This guide will help you deploy your Telegram trading bot on an AWS EC2 instance with proper environment configuration.

## Prerequisites

1. AWS account with EC2 access
2. Basic knowledge of Linux command line
3. Your Telegram bot token from @BotFather
4. PostgreSQL database (AWS RDS recommended)

## Step 1: Launch AWS EC2 Instance

1. **Launch Instance**:
   - Go to AWS EC2 Console
   - Click "Launch Instance"
   - Choose Ubuntu Server 22.04 LTS (recommended)
   - Instance type: t3.medium or higher (for production)
   - Configure security group to allow:
     - SSH (port 22) from your IP
     - HTTP (port 80) - optional
     - HTTPS (port 443) - optional

2. **Connect to Instance**:
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

## Step 2: System Setup

1. **Update System**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python and Dependencies**:
   ```bash
   sudo apt install python3 python3-pip python3-venv git postgresql-client -y
   ```

3. **Install Python Development Tools**:
   ```bash
   sudo apt install python3-dev libpq-dev build-essential -y
   ```

## Step 3: Deploy Your Bot

1. **Clone/Upload Your Bot Code**:
   ```bash
   # If using git
   git clone your-repository-url bot-project
   cd bot-project
   
   # Or upload your files using scp
   # scp -i your-key.pem -r /local/bot/path ubuntu@your-ec2-ip:~/bot-project
   ```

2. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Environment Configuration

1. **Create Environment File**:
   ```bash
   cp .env.template .env
   nano .env
   ```

2. **Configure Your .env File**:
   ```env
   # Essential Configuration
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
   DATABASE_URL=postgresql://username:password@your-rds-endpoint:5432/database_name
   SESSION_SECRET=your_generated_session_secret_here
   
   # Production Settings
   FLASK_ENV=production
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   
   # AWS Settings (optional but recommended)
   AWS_REGION=us-east-1
   AWS_DEFAULT_REGION=us-east-1
   ```

3. **Generate Session Secret**:
   ```bash
   python3 -c "import secrets; print('SESSION_SECRET=' + secrets.token_hex(32))"
   ```
   Copy the output to your .env file.

## Step 5: Database Setup

### Option A: AWS RDS PostgreSQL

1. **Create RDS Instance**:
   - Go to AWS RDS Console
   - Create PostgreSQL database
   - Note the endpoint, username, and password

2. **Configure Database URL**:
   ```env
   DATABASE_URL=postgresql://username:password@your-rds-endpoint.region.rds.amazonaws.com:5432/database_name
   ```

### Option B: Local PostgreSQL

1. **Install PostgreSQL**:
   ```bash
   sudo apt install postgresql postgresql-contrib -y
   ```

2. **Setup Database**:
   ```bash
   sudo -u postgres createuser --interactive
   sudo -u postgres createdb your_database_name
   ```

## Step 6: Test Your Bot

1. **Test Environment Detection**:
   ```bash
   python3 environment_detector.py
   ```
   Expected output should show "aws" environment type.

2. **Test Bot Startup**:
   ```bash
   python3 bot_v20_runner.py
   ```
   
   You should see logs indicating:
   - AWS Environment detected
   - .env file loaded successfully
   - Database connection successful
   - Bot starting in polling mode

3. **Test Bot Functionality**:
   - Send `/start` to your bot on Telegram
   - Verify it responds correctly

## Step 7: Production Deployment

### Option A: Simple Screen Session

1. **Install Screen**:
   ```bash
   sudo apt install screen -y
   ```

2. **Start Bot in Screen**:
   ```bash
   screen -S telegram-bot
   source venv/bin/activate
   python3 bot_v20_runner.py
   ```

3. **Detach from Screen**: Press `Ctrl+A` then `D`

4. **Reattach Later**:
   ```bash
   screen -r telegram-bot
   ```

### Option B: Systemd Service (Recommended)

1. **Create Service File**:
   ```bash
   sudo nano /etc/systemd/system/telegram-bot.service
   ```

2. **Service Configuration**:
   ```ini
   [Unit]
   Description=Telegram Trading Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/bot-project
   Environment=PATH=/home/ubuntu/bot-project/venv/bin
   ExecStart=/home/ubuntu/bot-project/venv/bin/python bot_v20_runner.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and Start Service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable telegram-bot
   sudo systemctl start telegram-bot
   ```

4. **Check Service Status**:
   ```bash
   sudo systemctl status telegram-bot
   sudo journalctl -u telegram-bot -f  # View logs
   ```

## Step 8: Monitoring and Maintenance

### Log Management

1. **View Bot Logs**:
   ```bash
   # If using systemd
   sudo journalctl -u telegram-bot -f
   
   # If using screen
   screen -r telegram-bot
   ```

2. **Log Rotation** (for systemd):
   ```bash
   sudo nano /etc/systemd/journald.conf
   ```
   Add:
   ```ini
   SystemMaxUse=1G
   MaxRetentionSec=1week
   ```

### Database Maintenance

1. **Monitor Database Size**:
   Access the health endpoint: `http://your-ec2-ip:5000/health`

2. **Manual Cleanup** (if needed):
   ```bash
   curl -X POST http://localhost:5000/database/cleanup
   ```

### Security Updates

1. **Regular Updates**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo systemctl restart telegram-bot
   ```

## Troubleshooting

### Common Issues

1. **Bot Token Not Found**:
   - Verify `.env` file exists and contains `TELEGRAM_BOT_TOKEN`
   - Check file permissions: `chmod 600 .env`

2. **Database Connection Failed**:
   - Verify `DATABASE_URL` format
   - Test connection: `psql $DATABASE_URL`
   - Check security groups allow database access

3. **Permission Denied**:
   - Ensure correct file ownership: `chown -R ubuntu:ubuntu /home/ubuntu/bot-project`
   - Check service user in systemd configuration

4. **Bot Not Responding**:
   - Check bot logs for errors
   - Verify bot token is correct
   - Test with `curl https://api.telegram.org/bot<TOKEN>/getMe`

### Debug Commands

```bash
# Check environment detection
python3 -c "from environment_detector import get_environment_info; print(get_environment_info())"

# Test database connection
python3 -c "from app import app; from models import User; app.app_context().push(); print(User.query.count())"

# Check bot token
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Token length:', len(os.environ.get('TELEGRAM_BOT_TOKEN', '')))"
```

## Environment Comparison

| Feature | Replit | AWS |
|---------|--------|-----|
| Startup Method | Auto-start via web interface | Manual via `python bot_v20_runner.py` |
| Environment Variables | Built-in secrets manager | `.env` file |
| .env Loading | Not required | Required |
| Persistence | Session-based | Permanent |
| Scaling | Limited | Full control |

## Security Best Practices

1. **Environment File Security**:
   ```bash
   chmod 600 .env
   ```

2. **Firewall Configuration**:
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 5000  # Only if needed for web interface
   ```

3. **Regular Backups**:
   - Database backups
   - Configuration file backups
   - Code repository updates

## Support

If you encounter issues:

1. Check the logs first
2. Verify environment configuration
3. Test individual components
4. Review this guide's troubleshooting section

Your bot is now configured for AWS deployment with environment-aware startup!