#!/bin/bash
# Solana Memecoin Trading Bot - Startup Script
# This script installs all required dependencies and starts the bot

echo "========================================================"
echo "        Solana Memecoin Trading Bot Launcher            "
echo "========================================================"

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Check if database connection is available
echo "Checking database connection..."
python3 -c "
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Check if DATABASE_URL is set
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('WARNING: DATABASE_URL environment variable is not set!')
    print('Database operations will use SQLite as fallback')
else:
    print('Database URL found in environment')

# Check if Telegram token is available
token = os.environ.get('TELEGRAM_BOT_TOKEN')
if not token:
    print('ERROR: TELEGRAM_BOT_TOKEN environment variable is not set!')
    print('Bot cannot start without a valid token')
    sys.exit(1)
else:
    print('Telegram bot token found in environment')
"

# Start the bot if checks passed
if [ $? -eq 0 ]; then
    echo "Starting Solana Memecoin Trading Bot..."
    python3 bot.py
else
    echo "Startup checks failed. Please check the errors above."
    exit 1
fi