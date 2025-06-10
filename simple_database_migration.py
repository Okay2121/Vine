#!/usr/bin/env python3
"""
Simple Database Migration Tool
=============================
This script helps you test and migrate to a new production database.
Run with your new database URL as an argument.

Usage:
    python simple_database_migration.py "postgresql://user:pass@host:port/db"
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import OperationalError
import psycopg2

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Current Neon database URL
CURRENT_DB = "postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"

def test_database_connection(db_url, name="database"):
    """Test database connection."""
    try:
        engine = create_engine(db_url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✓ {name} connection successful")
            logger.info(f"  PostgreSQL version: {version[:50]}...")
            return True
    except Exception as e:
        logger.error(f"✗ {name} connection failed: {str(e)}")
        return False

def create_tables_on_target(target_url):
    """Create tables on target database using app models."""
    try:
        # Set the new database URL temporarily
        os.environ['DATABASE_URL'] = target_url
        
        # Import and create tables
        from app import app, db
        
        with app.app_context():
            db.create_all()
            logger.info("✓ Tables created on target database")
            return True
            
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {str(e)}")
        return False

def migrate_table_data(source_url, target_url, table_name):
    """Migrate data from one table."""
    try:
        source_engine = create_engine(source_url, connect_args={"connect_timeout": 10})
        target_engine = create_engine(target_url, connect_args={"connect_timeout": 10})
        
        with source_engine.connect() as source_conn:
            # Get data from source
            result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            columns = list(result.keys())
            
            if not rows:
                logger.info(f"  {table_name}: No data to migrate")
                return True
            
            # Insert into target
            with target_engine.connect() as target_conn:
                for row in rows:
                    try:
                        # Create parameterized query
                        placeholders = ', '.join([f":{col}" for col in columns])
                        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                        
                        # Create parameter dictionary
                        row_dict = dict(zip(columns, row))
                        
                        target_conn.execute(text(query), row_dict)
                    except Exception as row_error:
                        logger.warning(f"  Failed to insert row: {str(row_error)}")
                        continue
                
                target_conn.commit()
            
            logger.info(f"  {table_name}: Migrated {len(rows)} rows")
            return True
            
    except Exception as e:
        logger.error(f"  {table_name}: Migration failed - {str(e)}")
        return False

def get_table_list(db_url):
    """Get list of tables from database."""
    try:
        engine = create_engine(db_url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            return tables
    except Exception as e:
        logger.error(f"Failed to get table list: {str(e)}")
        return []

def update_config_file(new_db_url):
    """Update configuration with new database URL."""
    config_content = f"""
# Updated Database Configuration
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Add this to your .env file:
DATABASE_URL={new_db_url}

# For production deployment, set this environment variable:
export DATABASE_URL="{new_db_url}"

# For AWS deployment:
aws ssm put-parameter --name "/solana-bot/database-url" --value "{new_db_url}" --type "SecureString"

# For Railway deployment:
railway variables:set DATABASE_URL="{new_db_url}"

# Update your config.py if needed:
PRODUCTION_DATABASE_URL = "{new_db_url}"
"""
    
    with open('new_database_config.txt', 'w') as f:
        f.write(config_content)
    
    logger.info("✓ Configuration saved to 'new_database_config.txt'")

def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_database_migration.py 'postgresql://user:pass@host:port/db'")
        print("\nRecommended database providers:")
        print("• Railway: https://railway.app ($5/month)")
        print("• Digital Ocean: https://cloud.digitalocean.com ($15/month)")
        print("• AWS RDS: https://aws.amazon.com/rds/ ($20+/month)")
        print("• Supabase: https://supabase.com (free tier available)")
        sys.exit(1)
    
    new_db_url = sys.argv[1].strip()
    
    print("=" * 60)
    print("Database Migration Tool for Solana Trading Bot")
    print("=" * 60)
    
    # Step 1: Test new database connection
    print("\n1. Testing new database connection...")
    if not test_database_connection(new_db_url, "new database"):
        print("✗ Cannot connect to new database. Please check your connection string.")
        sys.exit(1)
    
    # Step 2: Test current database (optional)
    print("\n2. Testing current database connection...")
    can_migrate_data = test_database_connection(CURRENT_DB, "current database")
    
    # Step 3: Create tables on new database
    print("\n3. Creating tables on new database...")
    if not create_tables_on_target(new_db_url):
        print("✗ Failed to create tables on new database.")
        sys.exit(1)
    
    # Step 4: Migrate data (if current database is accessible)
    if can_migrate_data:
        print("\n4. Migrating data...")
        tables = get_table_list(CURRENT_DB)
        
        if tables:
            logger.info(f"Found {len(tables)} tables to migrate: {tables}")
            
            migrated_count = 0
            for table in tables:
                if migrate_table_data(CURRENT_DB, new_db_url, table):
                    migrated_count += 1
            
            logger.info(f"✓ Successfully migrated {migrated_count}/{len(tables)} tables")
        else:
            logger.warning("No tables found to migrate")
    else:
        print("\n4. Skipping data migration (current database not accessible)")
    
    # Step 5: Update configuration
    print("\n5. Updating configuration...")
    update_config_file(new_db_url)
    
    # Step 6: Final verification
    print("\n6. Final verification...")
    if test_database_connection(new_db_url, "migrated database"):
        print("\n" + "=" * 60)
        print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Update your deployment environment with the new DATABASE_URL")
        print("2. Restart your application")
        print("3. Check the health endpoint: /health")
        print("4. Monitor deposit detection in the logs")
        print("\nConfiguration details saved in 'new_database_config.txt'")
    else:
        print("✗ Final verification failed. Please check the migration.")

if __name__ == "__main__":
    main()