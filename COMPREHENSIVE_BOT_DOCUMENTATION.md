# Solana Memecoin Trading Bot - Complete Documentation

## 📖 Table of Contents
1. [Project Overview](#project-overview)
2. [Folder & File Structure](#folder--file-structure)
3. [Dependencies](#dependencies)
4. [Environment Variables](#environment-variables)
5. [Bot Logic & Architecture](#bot-logic--architecture)
6. [Database Schema](#database-schema)
7. [Commands & Features](#commands--features)
8. [APIs & External Integrations](#apis--external-integrations)
9. [Security Considerations](#security-considerations)
10. [Setup & Deployment](#setup--deployment)

---

## 1. Project Overview

### Main Purpose
A sophisticated Telegram-integrated cryptocurrency trading platform specializing in Solana blockchain memecoin trading. The bot provides realistic trading simulation with real-time performance tracking, profit/loss analytics, and comprehensive admin controls for trade broadcasting.

### Primary Features & Capabilities
- **Real-time Solana blockchain monitoring** - Tracks actual transaction data and memecoin movements
- **Advanced trading simulation** - Generates authentic-feeling trading experiences with realistic ROI (targeting ~160%)
- **Comprehensive admin trade broadcasting** - Admins can broadcast Buy/Sell trades that affect all users proportionally
- **Performance analytics dashboard** - Real-time P/L tracking, streak calculations, and trading metrics
- **Referral system** - Direct ID-based referrals with 5% commission structure
- **Dynamic wallet management** - Secure deposit/withdrawal system with automatic transaction monitoring
- **User lifecycle management** - Complete onboarding, activation, and trading state management
- **Production-ready scalability** - Optimized for 500+ concurrent users with connection pooling

---

## 2. Folder & File Structure

### Core Application Files
```
📁 Root Directory
├── 🚀 main.py                    # Flask application entry point
├── 🤖 bot_v20_runner.py         # Main Telegram bot implementation (8000+ lines)
├── 🗄️ app.py                    # Flask app with database configuration
├── 📊 models.py                 # SQLAlchemy database models
├── ⚙️ config.py                 # Configuration management and environment loading
└── 📋 requirements.txt          # Python dependencies
```

### Handler System
```
📁 handlers/                     # Modular command handlers
├── 🏠 start.py                  # User onboarding and registration
├── 📊 dashboard.py              # Performance analytics display
├── 💰 deposit.py                # Deposit monitoring and processing
├── 👥 referral.py               # Referral system management
├── 👑 admin.py                  # Administrative controls
├── ⚙️ settings.py               # User preferences and configuration
└── 📞 help.py                   # User assistance and guides
```

### Utility Modules
```
📁 utils/                        # Core utility functions
├── 🔗 solana.py                 # Solana blockchain integration
├── 📈 auto_trading_history.py   # Background trading simulation
├── 👁️ deposit_monitor.py        # Real-time deposit tracking
├── 📢 notifications.py          # Message broadcasting system
├── 💹 roi_system.py             # ROI calculation engine
└── 📅 scheduler.py              # Background task management
```

### AWS Deployment Infrastructure
```
📁 AWS Deployment Files
├── 🚀 aws_start_bot.py          # AWS-specific startup script
├── 📋 aws_deployment_guide.md   # Complete deployment instructions
├── 🔍 aws_deployment_audit.py   # Deployment compatibility scanner
├── ⚙️ .env.example              # Environment configuration template
└── 🛠️ aws_deployment_setup.py   # Automated setup utilities
```

### Database & Performance
```
📁 Database Management
├── 🔌 database_connection_handler.py    # Connection pooling and retry logic
├── 📊 database_monitoring.py           # Health checks and maintenance
├── 🛡️ database_stability_system.py     # Error-resistant operations
├── ⚡ performance_tracking.py          # Real-time analytics
└── 🎯 query_performance_booster.py     # Query optimization
```

### Trading System
```
📁 Trading Components
├── 📈 simple_trade_handler.py          # Trade message parsing
├── 🎯 smart_balance_allocator.py       # Proportional profit distribution
├── 📡 enhanced_trade_broadcast.py      # Advanced trade broadcasting
├── 👨‍💼 admin_trade_handler.py          # Admin trade management
└── 📊 trade_broadcast_handler.py       # Trade execution logic
```

---

## 3. Dependencies

### Core Python Packages (requirements.txt)
```python
# Web Framework & Database
flask>=2.3.0                    # Main web application framework
flask-sqlalchemy>=3.0.0         # Database ORM integration
sqlalchemy>=2.0.0               # Core database toolkit
psycopg2-binary>=2.9.0          # PostgreSQL adapter
alembic>=1.12.0                 # Database migrations

# Telegram Bot Framework
python-telegram-bot>=20.0       # Primary bot implementation
telegram>=0.0.1                 # Additional Telegram utilities

# HTTP & Network
requests>=2.31.0                # External API communication
aiohttp>=3.8.0                  # Async HTTP requests
gunicorn>=21.0.0                # Production WSGI server

# Utilities & Tools
python-dotenv>=1.0.0            # Environment variable management
schedule>=1.2.0                 # Background task scheduling
qrcode>=7.4.0                   # QR code generation for wallets
pillow>=10.0.0                  # Image processing
trafilatura>=1.6.0              # Web content extraction
psutil>=5.9.0                   # System performance monitoring
email-validator>=2.0.0          # Email validation utilities
werkzeug>=2.3.0                 # WSGI utilities
```

### External Services & APIs
- **Telegram Bot API** - Primary user interface and messaging
- **PostgreSQL Database** - Production data storage (Neon.tech compatible)
- **Solana RPC API** - Blockchain transaction monitoring
- **Pump.fun API** - Real memecoin data integration
- **Birdeye.so API** - Token information and market links

---

## 4. Environment Variables

### Required Core Variables
```bash
# ================================
# TELEGRAM BOT CONFIGURATION
# ================================
TELEGRAM_BOT_TOKEN=6123456789:AAF...  # From @BotFather
ADMIN_USER_ID=123456789               # Your Telegram user ID for admin access

# ================================
# DATABASE CONFIGURATION
# ================================
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require

# ================================
# FLASK SECURITY
# ================================
SESSION_SECRET=your_32_char_random_key_here  # Strong random string

# ================================
# BOT CORE SETTINGS
# ================================
MIN_DEPOSIT=0.5                       # Minimum deposit in SOL
GLOBAL_DEPOSIT_WALLET=2pWHfMgp...     # Solana wallet for deposits
SUPPORT_USERNAME=your_support_user     # Telegram support contact
```

### Optional Advanced Settings
```bash
# Environment Control
BOT_ENVIRONMENT=aws                    # Force AWS mode (auto-detected)
NODE_ENV=production                    # Production environment flag
LOG_LEVEL=INFO                         # Logging verbosity

# Trading Configuration
MAX_DEPOSIT=5000                       # Maximum deposit limit
SOLANA_NETWORK=mainnet-beta           # Solana network selection
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# ROI Simulation Parameters
SIMULATED_DAILY_ROI_MIN=0.5           # Minimum daily ROI %
SIMULATED_DAILY_ROI_MAX=2.2           # Maximum daily ROI %
SIMULATED_LOSS_PROBABILITY=0.15        # Loss probability (15%)

# Notification Settings
DAILY_UPDATE_HOUR=9                    # Hour for daily updates (0-23)
```

---

## 5. Bot Logic & Architecture

### Core Architecture Pattern
The bot implements a **dual-layer architecture** with clear separation between the Telegram interface and business logic:

```
User Message → Telegram Bot API → Command Router → Handler Functions → Database Operations → Response Generation
```

### Main Components

#### 1. SimpleTelegramBot Class (bot_v20_runner.py)
- **Singleton pattern** prevents multiple bot instances
- **Enhanced polling** with 30-second timeout and graceful error handling
- **Duplicate message protection** with HTTP 409 handling
- **Command routing** to appropriate handler functions

#### 2. Database Layer (models.py + app.py)
- **SQLAlchemy ORM** with PostgreSQL production backend
- **Connection pooling** with NullPool for serverless compatibility
- **Retry logic** for database operations with exponential backoff
- **Health monitoring** with automated cleanup

#### 3. Trade Broadcasting System
- **Admin command parsing** - "Buy $TOKEN 0.0041 https://solscan.io/tx/..."
- **Authentic ROI calculation** - Uses actual entry/exit price differences (~160% returns)
- **Proportional distribution** - Allocates profits based on user balance ratios (15-25%)
- **Real-time updates** - Instant position feed updates for all users

#### 4. Performance Tracking Engine
- **Real-time P/L calculation** - Separates deposits from trading profits
- **Streak tracking** - Consecutive profitable days with UserMetrics synchronization
- **Daily snapshots** - Historical performance data retention
- **Multi-dashboard sync** - Consistent data across autopilot, performance, and withdrawal screens

### Message Flow Architecture
```
1. User Input → Telegram API
2. Bot Polling → Message Reception
3. Command Detection → Handler Dispatch
4. Database Query → Business Logic
5. Response Generation → Message Formatting
6. Telegram API → User Response
```

### Error Handling Strategy
- **Graceful degradation** for network failures
- **Database retry logic** with connection recreation
- **Duplicate instance prevention** with process checking
- **HTTP error recovery** with automatic retries
- **User-friendly error messages** without technical details

---

## 6. Database Schema

### Core User Management
```sql
-- User table - Central user information
CREATE TABLE user (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64),
    first_name VARCHAR(64),
    last_name VARCHAR(64),
    joined_at TIMESTAMP DEFAULT NOW(),
    status user_status DEFAULT 'onboarding',
    wallet_address VARCHAR(64) UNIQUE,      -- Payout wallet
    deposit_wallet VARCHAR(64),             -- Deposit wallet (shared)
    balance FLOAT DEFAULT 0.0,
    initial_deposit FLOAT DEFAULT 0.0,
    last_activity TIMESTAMP DEFAULT NOW(),
    referrer_code_id INTEGER REFERENCES referral_code(id),
    referral_bonus FLOAT DEFAULT 0.0
);

-- Transaction history with enhanced tracking
CREATE TABLE transaction (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    transaction_type VARCHAR(20) NOT NULL,  -- deposit, withdraw, trade_profit, admin_credit
    amount FLOAT NOT NULL,
    token_name VARCHAR(64),                 -- For trading transactions
    price FLOAT,                           -- Token price for trades
    timestamp TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending',   -- pending, completed, failed
    notes TEXT,                            -- Additional information
    tx_hash VARCHAR(128) UNIQUE,           -- Prevents duplicate processing
    processed_at TIMESTAMP,               -- Actual processing time
    related_trade_id INTEGER               -- Links to TradingPosition
);
```

### Trading & Performance Tracking
```sql
-- Trading positions with comprehensive tracking
CREATE TABLE trading_position (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    token_name VARCHAR(64) NOT NULL,
    amount FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    current_price FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'open',     -- open, closed
    trade_type VARCHAR(20),                -- scalp, snipe, dip, reversal
    buy_tx_hash VARCHAR(128),              -- Buy transaction hash
    sell_tx_hash VARCHAR(128),             -- Sell transaction hash
    buy_timestamp TIMESTAMP,               -- Buy execution time
    sell_timestamp TIMESTAMP,              -- Sell execution time
    roi_percentage FLOAT,                  -- Calculated ROI
    paired_position_id INTEGER             -- Links buy/sell pairs
);

-- Profit tracking for P/L calculations
CREATE TABLE profit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    amount FLOAT NOT NULL,                 -- Profit amount in SOL
    percentage FLOAT NOT NULL,             -- ROI percentage
    date DATE NOT NULL                     -- Date of profit
);

-- User metrics for dashboard displays
CREATE TABLE user_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    current_streak INTEGER DEFAULT 0,     -- Consecutive profitable days
    best_streak INTEGER DEFAULT 0,        -- Best streak achieved
    last_streak_update DATE,              -- Last streak calculation
    total_trades INTEGER DEFAULT 0,       -- Total completed trades
    winning_trades INTEGER DEFAULT 0,     -- Profitable trades count
    average_roi FLOAT DEFAULT 0.0         -- Average return on investment
);
```

### Referral & Admin Systems
```sql
-- Referral code management
CREATE TABLE referral_code (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    code VARCHAR(32) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    total_referrals INTEGER DEFAULT 0,
    total_earnings FLOAT DEFAULT 0.0
);

-- Administrative features
CREATE TABLE admin_message (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(64) NOT NULL,        -- Admin Telegram ID
    message_type VARCHAR(20) NOT NULL,    -- broadcast, direct, trade
    content TEXT NOT NULL,
    target_users TEXT,                    -- User targeting criteria
    sent_at TIMESTAMP DEFAULT NOW(),
    delivery_count INTEGER DEFAULT 0      -- Successful deliveries
);

-- System settings and configuration
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_name VARCHAR(64) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(64)                -- Admin who made the change
);
```

### Indexes for Performance
```sql
-- Critical indexes for query optimization
CREATE INDEX idx_transaction_user_type ON transaction(user_id, transaction_type);
CREATE INDEX idx_transaction_status ON transaction(status);
CREATE INDEX idx_trading_position_user ON trading_position(user_id);
CREATE INDEX idx_trading_position_status ON trading_position(status);
CREATE INDEX idx_profit_user_date ON profit(user_id, date);
CREATE INDEX idx_user_status ON user(status);
CREATE INDEX idx_user_telegram_id ON user(telegram_id);
```

---

## 7. Commands & Features

### User Commands
| Command | Description | Arguments | Example |
|---------|-------------|-----------|---------|
| `/start` | User registration and onboarding | Optional referral code | `/start ref_123456789` |
| `/help` | Display available commands and guidance | None | `/help` |
| `/deposit` | Show deposit instructions with QR code | None | `/deposit` |
| `/dashboard` | Display autopilot performance metrics | None | `/dashboard` |
| `/performance` | Detailed trading analytics | None | `/performance` |
| `/positions` | View current trading positions | None | `/positions` |
| `/history` | Trading history and completed trades | None | `/history` |
| `/withdraw` | Withdrawal interface with P/L summary | None | `/withdraw` |
| `/referral` | Referral system and earnings | None | `/referral` |
| `/settings` | User preferences and wallet management | None | `/settings` |

### Admin Commands
| Command | Description | Access Level | Example |
|---------|-------------|--------------|---------|
| `/admin` | Main admin panel | Admin only | `/admin` |
| **Trade Broadcasting** |
| `Buy $TOKEN PRICE AMOUNT TX_LINK` | Broadcast buy trade to users | Admin | `Buy $ZING 0.004107 812345 https://solscan.io/tx/abc` |
| `Sell $TOKEN PRICE AMOUNT TX_LINK` | Broadcast sell trade with profit calc | Admin | `Sell $ZING 0.006834 812345 https://solscan.io/tx/def` |
| **User Management** |
| View Active Users | List users with deposits | Admin | Button in admin panel |
| View All Users | Complete user database | Admin | Button in admin panel |
| Search User | Find user by ID/username | Admin | Button → Enter criteria |
| Adjust Balance | Modify user balance safely | Admin | Button → User → Amount |
| Reset User | Clear user data and restart | Admin | Button → Confirm |
| Remove User | Permanently delete user | Admin | Button → Confirm |
| **System Management** |
| Export CSV | Download user data | Admin | Button in admin panel |
| Broadcast Message | Send message to all users | Admin | Button → Type message |
| View Statistics | System performance metrics | Admin | Button in admin panel |
| Manage Withdrawals | Process withdrawal requests | Admin | Button in admin panel |

### Callback Handlers (Inline Buttons)
```python
# Dashboard navigation
dashboard_performance    # Performance analytics view
dashboard_positions     # Current positions display
dashboard_history       # Trade history view

# Referral system
copy_referral          # Copy referral link
share_referral         # Share referral link
referral_stats         # View referral earnings

# Settings management
change_wallet          # Update payout wallet
toggle_notifications   # Enable/disable updates
view_support          # Contact support

# Admin callbacks
admin_broadcast_trade  # Trade broadcasting interface
admin_user_management  # User administration
admin_view_stats      # System statistics
admin_adjust_balance  # Balance modification tools
```

### Automated Features
- **Daily Performance Updates** - Sent at configured hour with P/L summary
- **Deposit Monitoring** - Real-time Solana blockchain scanning
- **Trade History Generation** - Background realistic trading simulation
- **Profit Streak Calculation** - Automatic consecutive day tracking
- **Database Cleanup** - Scheduled maintenance and optimization
- **Error Recovery** - Automatic retry for failed operations

---

## 8. APIs & External Integrations

### Telegram Bot API Integration
```python
# Primary bot communication
Base URL: https://api.telegram.org/bot{TOKEN}/
Methods Used:
- getUpdates          # Polling for new messages
- sendMessage         # Text message delivery
- editMessageText     # Inline message updates
- sendPhoto           # QR code and image sharing
- answerCallbackQuery # Inline button responses
```

### Solana Blockchain Integration
```python
# Real-time transaction monitoring
RPC Endpoint: https://api.mainnet-beta.solana.com
Functions:
- getAccountInfo      # Wallet balance checking
- getSignaturesForAddress  # Transaction history
- getTransaction      # Detailed transaction data
- getLatestBlockhash  # Network status verification

# Transaction monitoring flow
utils/solana.py:
- monitor_deposits()     # Scans for incoming transactions
- verify_transaction()   # Validates transaction authenticity
- get_wallet_balance()   # Real-time balance checking
```

### Database API Layer
```python
# PostgreSQL with connection pooling
Database URL: postgresql://user:pass@host:port/db
Connection Features:
- NullPool configuration  # Serverless compatibility
- Automatic retry logic   # Network failure recovery
- Health monitoring      # Connection status tracking
- Query optimization     # Performance monitoring

# Key database operations
models.py:
- User management        # Registration, status updates
- Transaction logging    # All financial operations
- Profit tracking       # P/L calculations
- Trading positions     # Position management
```

### External Market Data (Optional)
```python
# Pump.fun API integration
Purpose: Real memecoin data for authentic trading simulation
Endpoints:
- /api/coins           # Current memecoin listings
- /api/trades          # Recent trading activity

# Birdeye.so API integration  
Purpose: Token information and market links
Endpoints:
- /defi/token_overview # Token metadata
- /defi/price          # Current pricing data
```

### Admin Integration Points
```python
# Trade broadcasting system
Format: "Buy $TOKEN PRICE AMOUNT TX_LINK"
Processing:
1. Regex parsing       # Extract trade components
2. Price calculation   # ROI determination
3. User distribution   # Proportional profit allocation
4. Database updates    # Transaction and profit logging
5. Notification send   # Real-time user updates

# User management API
Functions:
- Balance adjustments  # Safe balance modifications
- User lifecycle      # Status management
- System monitoring   # Performance tracking
```

---

## 9. Security Considerations

### Authentication & Authorization
```python
# Admin access control
ADMIN_USER_ID verification    # Only authorized Telegram IDs
Session management           # Flask session security
Command validation          # Input sanitization
Callback verification       # Inline button security
```

### Database Security
```python
# SQL injection prevention
SQLAlchemy ORM usage        # Parameterized queries
Input validation           # User data sanitization
Connection encryption      # SSL/TLS database connections
Sensitive data handling    # No plaintext storage of secrets
```

### Financial Transaction Security
```python
# Duplicate prevention
tx_hash uniqueness         # Prevents double processing
Balance verification       # Ensures sufficient funds
Transaction logging        # Complete audit trail
Admin-only operations      # Balance adjustments restricted
```

### Environment Security
```python
# Secure configuration
SESSION_SECRET generation   # Strong random keys required
Environment variable protection  # No hardcoded secrets
Database credential security     # Encrypted connections
API key management              # Environment-based storage
```

### Telegram Security
```python
# Bot token protection
Token validation           # Verified bot identity
Rate limiting             # 10 messages per user per minute
Message validation        # Input sanitization
Callback query verification  # Prevent unauthorized actions
```

### Critical Security Notes
1. **Never expose SESSION_SECRET** - Generate 32+ character random string
2. **Secure database credentials** - Use strong passwords and SSL connections
3. **Limit admin access** - Only add trusted Telegram IDs to ADMIN_USER_ID
4. **Monitor logs regularly** - Check for unauthorized access attempts
5. **Keep dependencies updated** - Regularly update requirements.txt packages
6. **Validate all inputs** - Sanitize user data before database operations
7. **Use HTTPS only** - All external API calls use encrypted connections

---

## 10. Setup & Deployment

### Local Development Setup
```bash
# 1. Clone repository
git clone <repository-url>
cd solana-memecoin-bot

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 5. Setup database
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database setup complete')"

# 6. Run locally
python bot_v20_runner.py
```

### AWS Production Deployment
```bash
# 1. Server preparation
sudo apt update && sudo apt upgrade -y
sudo apt install python3.11 python3.11-pip python3.11-venv git -y

# 2. Application setup
git clone <repository-url> /home/ubuntu/solana-memecoin-bot
cd /home/ubuntu/solana-memecoin-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Environment configuration
# Create .env file with production variables
# Set BOT_ENVIRONMENT=aws

# 4. Database initialization
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database setup complete')"

# 5. Service installation
sudo cp solana-memecoin-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable solana-memecoin-bot
sudo systemctl start solana-memecoin-bot

# 6. Verification
sudo systemctl status solana-memecoin-bot
sudo journalctl -u solana-memecoin-bot -f
```

### Replit Deployment
```bash
# 1. Fork/Import repository to Replit
# 2. Environment variables in Secrets tab:
TELEGRAM_BOT_TOKEN=your_token
ADMIN_USER_ID=your_id
DATABASE_URL=your_database_url
SESSION_SECRET=your_secret

# 3. Auto-start configuration
# main.py handles automatic startup
# No manual intervention required

# 4. Verification
# Check console for startup logs
# Test bot commands in Telegram
```

### Environment-Specific Configurations

#### AWS Production
```bash
BOT_ENVIRONMENT=aws
NODE_ENV=production
LOG_LEVEL=INFO
# PostgreSQL database with SSL
# Gunicorn WSGI server
# Systemd service management
```

#### Replit Development
```bash
# Auto-detected environment
# Built-in database integration
# Automatic restarts
# Web-based console monitoring
```

### Monitoring & Maintenance
```bash
# Health check endpoints
GET /health              # Basic system status
GET /performance         # Performance metrics
GET /database/health     # Database status
GET /bot-optimization    # Bot-specific metrics

# Log monitoring
sudo journalctl -u solana-memecoin-bot -f     # Real-time logs
sudo journalctl -u solana-memecoin-bot -n 50  # Recent logs

# Process management
ps aux | grep python                          # Check running processes
sudo systemctl restart solana-memecoin-bot   # Restart service
```

### Troubleshooting Common Issues
```bash
# Database connection issues
python -c "from app import app, db; app.app_context().push(); print('Database connected:', db.engine.execute('SELECT 1').scalar() == 1)"

# Environment variable verification
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Bot Token:', 'LOADED' if os.getenv('TELEGRAM_BOT_TOKEN') else 'MISSING')"

# Service status checking
sudo systemctl status solana-memecoin-bot
sudo journalctl -u solana-memecoin-bot --no-pager -l

# Process cleanup
sudo pkill -f bot_v20_runner.py
sudo pkill -f gunicorn
```

---

## 🎯 Special Features & Architecture Highlights

### Production-Ready Scalability
- **500+ user optimization** with connection pooling and query optimization
- **Memory efficiency** under 100MB with intelligent caching
- **CPU optimization** through long polling (75% reduction in API calls)
- **Database optimization** with batch operations and connection recycling

### Authentic Trading Experience
- **Real ROI calculations** using actual entry/exit price differences (~160% returns)
- **Proportional profit distribution** based on user balance ratios (15-25% allocation)
- **Realistic trade timing** with authentic memecoin pump-and-dump patterns
- **Historical trade generation** for new users with believable trading backgrounds

### Advanced Admin Controls
- **Simple trade format** - "Buy $TOKEN PRICE TX_LINK" for easy broadcasting
- **Instant user impact** - Trades affect all users immediately with real-time updates
- **Comprehensive user management** - Balance adjustments, user lifecycle, system monitoring
- **Performance analytics** - Real-time system metrics and user engagement tracking

### Robust Error Handling
- **Duplicate instance prevention** with singleton pattern implementation
- **Database resilience** with retry logic and connection recreation
- **Graceful HTTP error handling** including 409 conflict resolution
- **Automatic recovery** from network failures and API timeouts

This documentation provides a complete technical overview of the Solana memecoin trading bot system, covering all aspects from setup to production deployment.