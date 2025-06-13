#!/bin/bash
# AWS Deployment Startup Script
# Make this file executable: chmod +x start_aws.sh

echo "Starting Solana Memecoin Bot on AWS..."

# Ensure we're in the correct directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(cat .env | grep -v ^# | xargs)
else
    echo "Warning: .env file not found"
fi

# Set production environment
export BOT_ENVIRONMENT=aws
export NODE_ENV=production

# Install/update dependencies if needed
if [ -f requirements.txt ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Run database migrations if needed
echo "Setting up database..."
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database setup complete')"

# Start the Flask application
echo "Starting Flask application..."
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --keep-alive 5 main:app &

# Start the Telegram bot
echo "Starting Telegram bot..."
python bot_v20_runner.py &

# Wait for all background processes
wait

echo "Application started successfully!"
