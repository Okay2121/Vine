# Solana Memecoin Trading Bot

A sophisticated Telegram-based Solana memecoin trading platform that provides automated, user-friendly blockchain trading capabilities with advanced engagement features and real-time performance monitoring.

## Features

- **Telegram Bot Integration**: Seamless user interaction through Telegram
- **Real-time Trading Simulation**: Advanced Solana blockchain trading environment
- **PostgreSQL Database**: Robust data storage with automated maintenance
- **Real-time Transaction Tracking**: Monitor deposits, trades, and withdrawals
- **User Management**: Complete user lifecycle with referral system
- **Admin Dashboard**: Comprehensive administrative tools
- **Performance Analytics**: Real-time trading performance tracking
- **Database Resilience**: Automated cleanup and monitoring systems
- **Auto-Deletion**: Messages auto-delete after 30 seconds for clean chats

## Quick Start

### Local Development (Replit)
1. Clone the repository
2. Environment variables are pre-configured in `.env`
3. Run: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`

### AWS Production Deployment
```bash
# 1. Server Setup
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx -y

# 2. Application Setup
git clone <your-repo-url> solana-memecoin-bot
cd solana-memecoin-bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Environment Configuration
cp .env.production .env
nano .env  # Configure your production values

# 4. Database Setup
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 5. Start Application
chmod +x start_aws.sh
./start_aws.sh
```

### Production Service Installation
```bash
# Install systemd service
sudo cp solana-memecoin-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable solana-memecoin-bot
sudo systemctl start solana-memecoin-bot

# Check status
sudo systemctl status solana-memecoin-bot
```

## Environment Configuration

For development, environment variables are pre-configured in `.env`. For production deployment, use `.env.production` as a template:

```bash
# Production Environment Variables
TELEGRAM_BOT_TOKEN=your_production_bot_token
ADMIN_USER_ID=your_telegram_user_id
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
MIN_DEPOSIT=0.5
GLOBAL_DEPOSIT_WALLET=your_solana_wallet_address
SUPPORT_USERNAME=YourSupportUsername
SESSION_SECRET=generate_strong_random_key_for_production
BOT_ENVIRONMENT=aws
NODE_ENV=production
```

### Required Environment Variables:
- `TELEGRAM_BOT_TOKEN`: Bot authentication token from @BotFather
- `ADMIN_USER_ID`: Your Telegram user ID for administrator access
- `DATABASE_URL`: PostgreSQL connection string
- `GLOBAL_DEPOSIT_WALLET`: Solana wallet address for receiving deposits
- `SUPPORT_USERNAME`: Admin support username
- `SESSION_SECRET`: Strong random key for Flask sessions
- `BOT_ENVIRONMENT`: Set to "aws" for production deployment

## Management Commands

### Service Control
```bash
# Start service
sudo systemctl start solana-memecoin-bot

# Stop service  
sudo systemctl stop solana-memecoin-bot

# Restart service
sudo systemctl restart solana-memecoin-bot

# View logs
sudo journalctl -u solana-memecoin-bot -f
```

### Development Commands
```bash
# Manual start for testing
python start_bot_manual.py

# Check deployment readiness
python aws_deployment_checklist.py

# Verify environment loading
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Bot Token:', 'LOADED' if os.getenv('TELEGRAM_BOT_TOKEN') else 'MISSING')"
```

## Architecture

- **Flask Web Application**: Backend API and health monitoring
- **Telegram Bot**: User interface with python-telegram-bot v20+
- **PostgreSQL Database**: Production-grade data storage with automated maintenance
- **Gunicorn WSGI Server**: Production web server with multiple workers
- **Systemd Service**: Process management and auto-restart capabilities
- **Environment Detection**: Automatic environment-aware startup behavior

## Key Components

### Core Files
- `main.py`: Flask application entry point with health endpoints
- `app.py`: Database configuration and connection handling
- `bot_v20_runner.py`: Telegram bot implementation
- `models.py`: SQLAlchemy database models
- `start_aws.sh`: Production startup script

### Handler Modules
- `handlers/`: Telegram command and callback handlers
- `utils/`: Core utilities (deposit monitoring, Solana integration, trading)
- `admin_*.py`: Admin management tools and trade systems

### Deployment Files
- `solana-memecoin-bot.service`: Systemd service configuration
- `.env.production`: Production environment template
- `AWS_DEPLOYMENT_COMMANDS.md`: Detailed deployment guide
- `requirements.txt`: Python dependencies

## Database Features

- **Automated Maintenance**: Scheduled cleanup and monitoring
- **Connection Resilience**: Retry logic and connection pooling
- **Performance Optimization**: Optimized for 500+ concurrent users
- **Real-time Monitoring**: Health checks and usage alerts

## Admin Features

Administrator access via Telegram user ID with comprehensive tools:
- `/admin`: Access admin control panel
- User management and balance adjustments
- Real-time transaction monitoring
- Broadcast messaging to users
- Trading position management
- ROI system administration

## Monitoring & Health Checks

The application provides several monitoring endpoints:
- `/health`: Basic health status
- `/database/health`: Detailed database metrics
- `/environment`: Environment detection information
- `/admin/deposit_logs`: Recent deposit transaction logs

## Security Features

- Environment-specific configuration loading
- Secure session management with Flask
- PostgreSQL connection with SSL requirements
- Admin user ID validation
- Automated message deletion for privacy

## License

This project is proprietary software.
