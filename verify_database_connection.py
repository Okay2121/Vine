#!/usr/bin/env python3
"""
Database Connection Verification Script
---------------------------------------
This script verifies the PostgreSQL connection and ensures all tables are created properly.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """
    Test the database connection and verify table creation
    """
    db_url = os.environ.get("DATABASE_URL")
    
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set")
        return False
    
    # Fix postgres:// to postgresql:// if needed
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    logger.info(f"Testing connection to: {db_url[:30]}...")
    
    try:
        # Create engine with enhanced connection settings
        engine = create_engine(
            db_url,
            pool_recycle=300,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            connect_args={
                "sslmode": "require",
                "connect_timeout": 30,
                "application_name": "solana_memecoin_bot_test"
            }
        )
        
        # Test basic connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
            
            # Test database info
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✓ PostgreSQL version: {version[:50]}...")
            
            # Check if our main tables exist
            tables_to_check = [
                'user', 'transaction', 'system_settings', 'trading_position',
                'referral', 'withdrawal_request', 'support_ticket'
            ]
            
            for table in tables_to_check:
                result = connection.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    )
                """))
                exists = result.fetchone()[0]
                if exists:
                    logger.info(f"✓ Table '{table}' exists")
                else:
                    logger.warning(f"⚠ Table '{table}' does not exist")
            
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False

def initialize_tables():
    """
    Initialize database tables using the app context
    """
    try:
        from app import app, db
        
        with app.app_context():
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("✓ Database tables created successfully")
            return True
            
    except Exception as e:
        logger.error(f"✗ Error creating tables: {e}")
        return False

def main():
    """
    Main verification function
    """
    logger.info("Starting database connection verification...")
    
    # Test connection
    if not test_database_connection():
        logger.error("Database connection test failed")
        sys.exit(1)
    
    # Initialize tables
    if not initialize_tables():
        logger.error("Table initialization failed")
        sys.exit(1)
    
    logger.info("✓ Database verification completed successfully!")
    logger.info("✓ Your application is ready for deployment!")

if __name__ == "__main__":
    main()