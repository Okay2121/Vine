# Solana Memecoin Trading Bot

## Overview
This is a sophisticated Telegram-based Solana memecoin trading bot that provides automated trading capabilities with a comprehensive user management system. The bot simulates realistic trading experiences while offering admin tools for trade broadcasting and user management. It's designed for production deployment with robust database handling and optimized performance for 500+ concurrent users.

## System Architecture

### Backend Architecture
- **Flask Web Application**: Main application server handling webhook endpoints and health monitoring
- **Telegram Bot API**: Direct API-based bot implementation using polling for better reliability
- **Database Layer**: PostgreSQL (production) with SQLite fallback, featuring connection pooling and retry logic
- **Auto-Trading Simulation**: Background system generating realistic trade histories for users

### Frontend Architecture
- **Telegram Interface**: Primary user interface through Telegram bot interactions
- **Admin Dashboard**: Telegram-based admin panel for user management and trade broadcasting
- **Performance Monitoring**: Real-time dashboards accessible via web endpoints

## Key Components

### 1. Bot Core (`bot_v20_runner.py`)
- Singleton pattern implementation preventing multiple bot instances
- Enhanced duplicate message protection with graceful HTTP 409 error handling
- Optimized polling with 30-second timeout and batch processing
- Smart trade message parsing for admin buy/sell commands

### 2. Database Management
- **Connection Handler** (`database_connection_handler.py`): Robust connection management with NullPool for production
- **Monitoring System** (`database_monitoring.py`): Proactive health checks and automated cleanup
- **Stability Layer** (`database_stability_system.py`): Error-resistant operations preventing SQLAlchemy crashes

### 3. Trading System
- **Simple Trade Handler** (`simple_trade_handler.py`): Parses "Buy $TOKEN PRICE TX_LINK" format
- **Smart Balance Allocator** (`smart_balance_allocator.py`): Distributes trade results proportionally to user balances
- **Auto Trading History** (`utils/auto_trading_history.py`): Generates realistic trading backgrounds for new users

### 4. User Management
- **Models** (`models.py`): Comprehensive database schema with user status, transactions, and trading positions
- **Balance Manager** (`balance_manager.py`): Safe balance adjustments with transaction logging
- **Admin Tools**: Complete user lifecycle management through Telegram interface

## Data Flow

### User Registration Flow
1. User starts bot with `/start` command
2. System creates user record with referral tracking
3. User deposits minimum amount to activate trading
4. Auto-trading history generation begins

### Trade Processing Flow
1. Admin sends trade in format: "Buy $TOKEN 0.0041 https://solscan.io/tx/abc123"
2. System parses and validates trade message
3. For sells, matches with existing buy positions
4. Calculates ROI and updates all user balances proportionally
5. Sends personalized notifications to users

### Database Operations Flow
1. All operations go through stability layer with retry logic
2. Health monitoring runs every 60 seconds
3. Automated cleanup removes old records to manage size
4. Connection pooling optimizes resource usage

## External Dependencies

### APIs and Services
- **Telegram Bot API**: Primary interface for user interactions
- **PostgreSQL**: Production database (Neon.tech integration)
- **Pump.fun API**: Real memecoin data for trade simulation
- **Birdeye.so API**: Token information and links

### Python Dependencies
- `python-telegram-bot`: Telegram bot framework
- `sqlalchemy`: Database ORM with PostgreSQL adapter
- `flask`: Web framework for health endpoints
- `psycopg2-binary`: PostgreSQL database adapter
- `requests`: HTTP client for external APIs
- `schedule`: Background task scheduling

## Deployment Strategy

### Production Configuration
- **Gunicorn WSGI Server**: Production-ready application server
- **Connection Pooling**: NullPool configuration for serverless environments
- **Environment Variables**: Secure configuration management
- **Health Monitoring**: Real-time system status endpoints

### Scalability Features
- **Memory Optimization**: <100MB usage for 500 users with caching
- **CPU Efficiency**: Long polling reduces API calls by 75%
- **Database Optimization**: Batch operations and connection recycling
- **Rate Limiting**: 10 messages per user per minute

### Monitoring Endpoints
- `/health`: Basic system and database status
- `/performance`: CPU, memory, and thread metrics  
- `/bot-optimization`: Bot-specific performance data
- `/database/health`: Detailed database metrics

## Recent Changes

### Environment-Aware Startup System (June 12, 2025)
- **Added automatic environment detection** for clean Replit/AWS startup behavior
- **Replit Environment**: Auto-start enabled for seamless remix functionality
- **AWS/Production Environment**: Manual start required to prevent conflicts
- **New Components**:
  - `environment_detector.py` - Detects environment via indicators and override settings
  - `start_bot_manual.py` - Clean manual starter for AWS/production environments
  - `startup_config.py` - Centralized startup configuration management
  - `/environment` endpoint - Detailed environment debugging information
- **Benefits**: Single codebase works everywhere, no duplicate instances, production-ready

### Deployment Strategy
- **Replit**: Auto-start on access (remix-friendly)
- **AWS**: Manual start via `python start_bot_manual.py` or environment override
- **Override**: Set `BOT_ENVIRONMENT=aws` to force manual mode even on Replit

## Changelog
- June 12, 2025. Initial setup and environment-aware startup implementation

## User Preferences

Preferred communication style: Simple, everyday language.