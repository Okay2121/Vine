# AWS Deployment Guide - Solana Memecoin Trading Bot

## Critical Database Configuration

Your bot is now configured to **always use PostgreSQL** with these safeguards:

- **Primary Database**: `postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require`
- **Fallback Protection**: If environment variable is missing, automatically uses the production database
- **Connection Pooling**: 10 connections with 20 overflow, 30-second timeout
- **SSL Security**: Required SSL mode for all connections

## Environment Variables for AWS Deployment

### Required Environment Variables

```bash
# Database (Auto-configured with fallback)
DATABASE_URL=postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require

# Telegram Bot
TELEGRAM_BOT_TOKEN=7562541416:AAGxe-j7r26pO7ku1m5kunmwes0n0e3p2XQ
ADMIN_USER_ID=5488280696

# Security
SESSION_SECRET=your-production-secret-key-here

# Bot Configuration
MIN_DEPOSIT=0.5
GLOBAL_DEPOSIT_WALLET=Soa8DkfSzZEmXLJ2AWEqm76fgrSWYxT5iPg6kDdZbKmx
SUPPORT_USERNAME=SolanaMemoBotAdmin
```

## AWS Deployment Steps

### 1. EC2 Instance Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx -y

# Clone your repository
git clone <your-repo-url>
cd <your-project>
```

### 2. Environment Configuration
```bash
# Copy environment template
cp aws_deployment_env.example .env

# Edit with your production values
nano .env
```

### 3. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Run Application
```bash
# Start with Gunicorn
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### 5. Process Management (Optional)
```bash
# Create systemd service
sudo nano /etc/systemd/system/solana-bot.service
```

Add this configuration:
```ini
[Unit]
Description=Solana Memecoin Trading Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/your-project
Environment=PATH=/home/ubuntu/your-project/venv/bin
ExecStart=/home/ubuntu/your-project/venv/bin/gunicorn --bind 0.0.0.0:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable solana-bot
sudo systemctl start solana-bot
```

## Health Monitoring

Your application includes these monitoring endpoints:

- **Health Check**: `http://your-domain/health`
- **Database Status**: `http://your-domain/db-status`

## Security Features

- **SSL Database Connection**: Required for all database communications
- **Connection Pooling**: Prevents connection exhaustion
- **Automatic Reconnection**: Pool pre-ping ensures connection validity
- **Environment Variable Protection**: Sensitive data stored in environment variables

## Troubleshooting

### Database Connection Issues
1. Check health endpoint: `curl http://localhost:5000/health`
2. Verify environment variables are set
3. Test direct database connection

### Bot Not Responding
1. Check application logs: `sudo journalctl -u solana-bot -f`
2. Verify Telegram bot token is correct
3. Ensure admin user ID is configured

## Production Checklist

- [ ] Environment variables configured
- [ ] Database connection tested
- [ ] Health endpoints responding
- [ ] Bot responding to Telegram commands
- [ ] SSL certificates configured (if using custom domain)
- [ ] Firewall rules configured
- [ ] Backup strategy implemented