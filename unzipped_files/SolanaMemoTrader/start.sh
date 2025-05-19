#!/bin/bash

# Start the Telegram Bot with Solana Memecoin Trading Platform
# This script sets up and starts the complete application

echo "Starting Solana Memecoin Trading Bot..."

# Verify if .env file exists
if [ ! -f .env ]; then
  echo "Warning: .env file not found. Creating with default values (please update)."
  echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env
  echo "ADMIN_USER_ID=your_telegram_id_here" >> .env
fi

# Check if PostgreSQL database is accessible
if [[ -z "${DATABASE_URL}" ]]; then
  echo "Warning: DATABASE_URL environment variable not set."
  echo "The app will default to a SQLite database. For production, use PostgreSQL."
fi

# Start application using gunicorn
echo "Starting application with Gunicorn..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app