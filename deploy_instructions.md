# Deployment Instructions for Solana Memecoin Trading Bot

This repository contains a ready-to-deploy Telegram bot for Solana memecoin trading. The .env file is **intentionally included** to make deployment easier.

## Quick Deployment Steps

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```
   pip install aiohttp alembic email-validator flask flask-sqlalchemy gunicorn pillow psutil psycopg2-binary python-dotenv python-telegram-bot qrcode requests schedule sqlalchemy telegram trafilatura werkzeug
   ```

3. Run the bot:
   ```
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

## Features
- PostgreSQL database configuration
- Telegram Bot API integration
- Automatic message cleanup (30-second timeout)
- Admin dashboard and controls
- User transaction tracking
- Deposit and withdrawal management

## Environment Variables
All necessary environment variables are pre-configured in the .env file:
- TELEGRAM_BOT_TOKEN: The Telegram bot API token
- ADMIN_USER_ID: ID of the administrator account
- DATABASE_URL: PostgreSQL connection string

## Database Setup
The database will be automatically initialized when the application starts for the first time.

## Security Note
For production environments, consider updating the passwords and tokens in the .env file before deployment.

## Requirements
- Python 3.10+
- PostgreSQL
- An internet-accessible server (for Telegram webhooks)