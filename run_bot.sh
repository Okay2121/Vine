#!/bin/bash

# Startup script for Solana Memecoin Trading Bot
echo "Starting Solana Memecoin Trading Bot..."

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install aiohttp alembic email-validator flask flask-sqlalchemy gunicorn pillow psutil psycopg2-binary python-dotenv python-telegram-bot qrcode requests schedule sqlalchemy telegram trafilatura werkzeug

# Start the bot
echo "Starting the bot..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app