# Clone and Run Instructions

This document provides step-by-step instructions for cloning and running the Solana Memecoin Trading Bot directly from GitHub to VSCode or any environment.

## 1. Clone the Repository

```bash
git clone https://github.com/Okay2121/Trading-engine-.git
cd Trading-engine-
```

## 2. Setup Options

### Option 1: Direct Run (Easiest)

Simply run the provided script:

```bash
chmod +x run_bot.sh
./run_bot.sh
```

This script will:
- Create a virtual environment
- Install all dependencies
- Start the bot

### Option 2: Manual Installation

If you prefer manual control:

```bash
# Create and activate virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install aiohttp alembic email-validator flask flask-sqlalchemy gunicorn pillow psutil psycopg2-binary python-dotenv python-telegram-bot qrcode requests schedule sqlalchemy telegram trafilatura werkzeug

# Start the application
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Option 3: Docker (For containerized deployment)

```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 3. Environment Variables

All environment variables are already configured in the included `.env` file:
- TELEGRAM_BOT_TOKEN: Telegram bot token
- ADMIN_USER_ID: Admin user ID for admin panel access
- DATABASE_URL: PostgreSQL database connection string

## 4. Verification

1. The bot should be running on http://localhost:5000
2. Check your Telegram bot by messaging it
3. Use the admin commands by sending /admin to your bot (if you're the admin)

## 5. Troubleshooting

If you encounter issues:

1. Check that PostgreSQL is running if using a local database
2. Ensure all dependencies are installed correctly
3. Verify your internet connection for Telegram API access
4. Make sure port 5000 is not already in use

## 6. Production Deployment Note

For production deployments, review and update the values in the `.env` file as needed.