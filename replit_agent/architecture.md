# Architecture Documentation

## Overview

The Solana Memecoin Trading Bot is a Telegram-based application that provides a simulated environment for trading Solana memecoins. The system consists of a Telegram bot interface and a Flask web application backend, with PostgreSQL for data persistence. The bot allows users to simulate memecoin trading activities without actual financial risk, track profits, and participate in a referral program.

## System Architecture

The system follows a modular architecture with clear separation of concerns:

1. **Telegram Bot Interface**: Handles user interactions through Telegram's messaging platform
2. **Flask Web Application**: Provides HTTP endpoints and serves as the container for the application
3. **SQLAlchemy ORM**: Manages database interactions and object mapping
4. **PostgreSQL Database**: Stores all persistent data including user information, transactions, and profits

### Architecture Diagram (Logical)

```
+------------------+     +-------------------+     +------------------+
|                  |     |                   |     |                  |
|  Telegram Users  <----->  Telegram Bot     <----->  Flask Web App  |
|                  |     |  (Python-Telegram-|     |                  |
+------------------+     |   Bot Library)    |     +--------^---------+
                         |                   |              |
                         +-------------------+              |
                                                           |
                                                           v
                         +-------------------+     +------------------+
                         |                   |     |                  |
                         |  Background Jobs  <----->  PostgreSQL DB  |
                         |  (Scheduler)      |     |                  |
                         +-------------------+     +------------------+
```

## Key Components

### 1. Telegram Bot

The bot is implemented using the `python-telegram-bot` library and provides the primary interface for users. It supports multiple operation modes:

- **Polling Mode**: The primary mode used for reliable operation, continuously polling Telegram's API for updates
- **Webhook Mode**: An alternative mode that receives updates via webhooks (less used in this implementation)

Key files:
- `bot_polling_runner.py`: Main entry point for the bot in polling mode
- `bot_runner.py`: Alternative entry point with more configuration options
- `handlers/`: Directory containing all command and callback handlers

### 2. Web Application

A Flask application serves as both a container for the application logic and provides HTTP endpoints for health checks and possible webhook integration.

Key files:
- `app.py`: Defines the Flask application and database connection
- `main.py`: Entry point that integrates bot functionality with the web application

### 3. Database Layer

The application uses SQLAlchemy ORM with PostgreSQL:

Key files:
- `models.py`: Defines all database models and relationships

Key models:
- `User`: Stores user information and balances
- `Transaction`: Records all user transactions
- `Profit`: Tracks daily profit/loss information
- `ReferralCode`: Manages the referral system

### 4. Utility Services

Various utility modules handle specific functionality:

- `utils/solana.py`: Interfaces with Solana blockchain (simulated in this version)
- `utils/trading.py`: Implements trading simulation logic
- `utils/scheduler.py`: Manages scheduled tasks like daily updates
- `utils/notifications.py`: Handles user notifications
- `utils/engagement.py`: Manages user engagement features

### 5. Handler Modules

Command and callback handlers are organized by functionality:

- `handlers/start.py`: Handles user onboarding
- `handlers/deposit.py`: Manages deposit functionality
- `handlers/dashboard.py`: Implements profit dashboard
- `handlers/admin.py`: Provides admin functionality
- `handlers/referral.py`: Handles the referral system
- `handlers/settings.py`: Manages user settings
- `handlers/help.py`: Provides help information

## Data Flow

1. **User Registration Flow**:
   - User starts bot with `/start` command
   - Bot creates user record in database
   - User provides Solana wallet address
   - Bot generates referral code for user

2. **Deposit Flow**:
   - User requests deposit instructions
   - Bot provides simulated Solana wallet address
   - User confirms deposit
   - Bot updates user balance and status

3. **Trading Simulation Flow**:
   - Scheduled job simulates daily trading activity
   - System calculates profit/loss based on configurable parameters
   - Results are stored in the database
   - User receives notifications about trading activity

4. **Dashboard Flow**:
   - User requests dashboard
   - Bot queries database for trading history and profit information
   - Information is presented with interactive elements for withdrawals or reinvestment

5. **Referral Flow**:
   - User shares unique referral code
   - New users join with referral code
   - System tracks referral relationships
   - Referrer earns percentage of referred users' profits

## External Dependencies

The application relies on the following key external dependencies:

1. **Telegram Bot API**: Primary interface for user interaction
2. **Solana Blockchain**: Simulated in the current implementation, but designed for eventual integration
3. **PostgreSQL**: Primary data store
4. **Flask**: Web application framework
5. **SQLAlchemy**: ORM for database interactions
6. **Python-Telegram-Bot**: Library for Telegram Bot API integration
7. **Gunicorn**: WSGI HTTP server for running the Flask application

## Deployment Strategy

The application is configured for deployment on Replit:

1. **Containerization**: Replit handles containerization implicitly
2. **Database**: Replit provides PostgreSQL integration
3. **Process Management**:
   - Main web application is run using Gunicorn
   - Bot runs in polling mode for reliability
   - `start_telegram_bot.sh` script ensures proper startup

Configuration:
- Environment variables stored in `.env` file for local development
- Replit deployment configuration in `.replit` file
- `gunicorn` configured to bind to port 5000

Deployment workflow:
1. Code is pushed to Replit
2. Replit builds the application
3. `gunicorn` starts the Flask application
4. The Flask application starts the Telegram bot in polling mode
5. Background jobs are scheduled for periodic tasks

## Security Considerations

1. **Environment Variables**: Sensitive information (bot tokens, API keys) stored in environment variables
2. **Admin Restrictions**: Admin functionality restricted by user ID
3. **Simulated Trading**: No actual cryptocurrency transactions occur, minimizing financial risk
4. **Database Security**: Relies on Replit's PostgreSQL security measures

## Future Architectural Considerations

1. **Real Solana Integration**: Move from simulation to actual Solana blockchain integration
2. **Scalability**: Improve scheduler for handling larger user base
3. **Analytics**: Add more comprehensive analytics for trading performance
4. **Advanced Trading Algorithms**: Implement more sophisticated trading simulation algorithms
5. **Security Enhancements**: Add more robust authentication and authorization mechanisms