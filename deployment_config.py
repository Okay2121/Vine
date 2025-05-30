"""
Production Deployment Configuration
----------------------------------
This configuration ensures reliable PostgreSQL connectivity for AWS deployment
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DeploymentConfig:
    """Configuration class for production deployment"""
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require')
    
    # Enhanced database connection settings for AWS deployment
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 30,
            'application_name': 'solana_memecoin_bot'
        }
    }
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'production-secret-key-change-this')
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID')
    
    # Production Settings
    DEBUG = False
    TESTING = False
    
    @staticmethod
    def validate_config():
        """Validate that all required configuration is present"""
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'ADMIN_USER_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

# Production database URL validation
def get_production_database_url():
    """Get and validate the production database URL"""
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        # Fallback to the provided Neon database
        db_url = 'postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require'
    
    # Ensure PostgreSQL URL format
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    return db_url