"""
Production Configuration for Telegram Bot
========================================
Centralized configuration with environment variable validation
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ProductionConfig:
    """Production configuration with validation"""
    
    # Required environment variables
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    DATABASE_URL: str = os.getenv('DATABASE_URL', 
        'postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require'
    )
    
    # Optional configuration
    ADMIN_USER_ID: str = os.getenv('ADMIN_USER_ID', '5488280696')
    MIN_DEPOSIT: float = float(os.getenv('MIN_DEPOSIT', '0.1'))
    
    # Performance settings for 500+ users
    POLLING_TIMEOUT: int = 30
    READ_LATENCY: int = 5
    MAX_CONCURRENT_HANDLERS: int = 50
    CACHE_TTL_SECONDS: int = 300
    
    # Rate limiting
    RATE_LIMIT_MESSAGES: int = 10
    RATE_LIMIT_WINDOW: int = 60
    
    # Database optimization
    DB_POOL_SIZE: int = 0  # NullPool - no persistent connections
    DB_MAX_OVERFLOW: int = 0
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 600
    
    # Batch processing
    DB_BATCH_SIZE: int = 50
    MESSAGE_BATCH_SIZE: int = 20
    NOTIFICATION_BATCH_SIZE: int = 10
    
    # Background task intervals
    DB_QUEUE_INTERVAL: int = 2
    MESSAGE_QUEUE_INTERVAL: int = 1
    CACHE_CLEANUP_INTERVAL: int = 300
    
    # Webhook settings (for future scaling)
    WEBHOOK_URL: Optional[str] = os.getenv('WEBHOOK_URL')
    WEBHOOK_SECRET: Optional[str] = os.getenv('WEBHOOK_SECRET')
    WEBHOOK_PORT: int = int(os.getenv('WEBHOOK_PORT', '8443'))
    
    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'production-secret-key-change-this')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        missing = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append('TELEGRAM_BOT_TOKEN')
        
        if not cls.DATABASE_URL:
            missing.append('DATABASE_URL')
        
        if missing:
            print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def get_database_config(cls) -> dict:
        """Get optimized database configuration"""
        return {
            'poolclass': 'NullPool',  # No idle connections
            'pool_pre_ping': True,
            'pool_recycle': cls.DB_POOL_RECYCLE,
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 30,
                'application_name': 'telegram_bot_production',
                'keepalives_idle': 600,
                'keepalives_interval': 60,
                'keepalives_count': 3
            },
            'echo': False  # Disable SQL logging in production
        }
    
    @classmethod
    def print_config(cls) -> None:
        """Print sanitized configuration for debugging"""
        print("Production Configuration:")
        print(f"  Database: {cls.DATABASE_URL[:40]}...")
        print(f"  Bot Token: {cls.TELEGRAM_BOT_TOKEN[:10] + '...' if cls.TELEGRAM_BOT_TOKEN else 'NOT SET'}")
        print(f"  Admin User: {cls.ADMIN_USER_ID}")
        print(f"  Min Deposit: {cls.MIN_DEPOSIT} SOL")
        print(f"  Polling Timeout: {cls.POLLING_TIMEOUT}s")
        print(f"  Cache TTL: {cls.CACHE_TTL_SECONDS}s")
        print(f"  Rate Limit: {cls.RATE_LIMIT_MESSAGES} msgs/{cls.RATE_LIMIT_WINDOW}s")
        print(f"  Batch Sizes: DB={cls.DB_BATCH_SIZE}, MSG={cls.MESSAGE_BATCH_SIZE}")