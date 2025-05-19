# Solana Memecoin Trading Bot

A sophisticated Telegram-based Solana memecoin trading platform that provides automated, user-friendly blockchain trading capabilities with advanced engagement features.

## Features

- **Telegram Bot Integration**: Seamless user interaction through Telegram
- **Solana Blockchain Simulation**: Realistic trading environment
- **PostgreSQL Database**: Robust data storage for user information and transactions
- **Real-time Transaction Tracking**: Monitor deposits, trades, and withdrawals
- **User Management**: Complete user lifecycle management
- **Admin Dashboard**: Comprehensive tools for administrators
- **Referral System**: Built-in user acquisition mechanism
- **Auto-Deletion**: Messages auto-delete after 30 seconds for clean chats

## Quick Start

This repository is designed for immediate deployment with minimal setup:

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

## Environment Configuration

All necessary environment variables are already configured in the `.env` file, which is intentionally included in this repository for ease of deployment:

- `TELEGRAM_BOT_TOKEN`: The bot's authentication token
- `ADMIN_USER_ID`: Telegram user ID for administrator access
- `DATABASE_URL`: PostgreSQL connection string

## Database Setup

The application is configured to use PostgreSQL. The database schema will be automatically created on first run.

## Architecture

- **Flask Web Application**: Serves as the backend framework
- **SQLAlchemy ORM**: Database abstraction layer
- **Telegram Bot API**: User interface through Telegram
- **Gunicorn WSGI Server**: Production-ready web server

## Files and Directories

- `main.py`: Entry point for the application
- `app.py`: Flask application and database configuration
- `bot_polling.py`: Telegram bot polling implementation
- `bot_v20_runner.py`: Alternative bot implementation for python-telegram-bot v20+
- `config.py`: Application configuration variables
- `models.py`: Database models
- `handlers/`: Telegram command handlers
- `utils/`: Utility functions for various operations

## Security Note

For production environments, review and update security settings in the `.env` file before deployment.

## Admin Commands

Administrator has access to special commands:
- `/admin`: Access admin panel
- User management tools
- Transaction monitoring
- Balance adjustments
- Broadcast messaging

## License

This project is proprietary software.