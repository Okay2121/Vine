"""
Production Database Setup and Migration Tool
===========================================
This script helps set up a robust production database solution that won't fail
after a week due to quota limits. It supports multiple database providers.
"""

import os
import logging
import time
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.exc import OperationalError
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionDatabaseSetup:
    """Setup production database with multiple provider options."""
    
    def __init__(self):
        self.supported_providers = {
            'aws_rds': self.setup_aws_rds,
            'digital_ocean': self.setup_digital_ocean,
            'railway': self.setup_railway,
            'render': self.setup_render,
            'supabase': self.setup_supabase,
            'planetscale': self.setup_planetscale
        }
    
    def setup_aws_rds(self):
        """Setup AWS RDS PostgreSQL database."""
        print("\n=== AWS RDS PostgreSQL Setup ===")
        print("1. Go to AWS RDS Console: https://console.aws.amazon.com/rds/")
        print("2. Click 'Create database'")
        print("3. Choose 'PostgreSQL'")
        print("4. Select 'Free tier' for testing or 'Production' for live use")
        print("5. Configure:")
        print("   - DB instance identifier: solana-trading-bot")
        print("   - Master username: postgres")
        print("   - Master password: [create strong password]")
        print("   - DB name: solana_trading")
        print("6. Security group: Allow inbound connections on port 5432")
        print("7. Your connection string will be:")
        print("   postgresql://username:password@endpoint:5432/database_name")
        
        return self.get_user_database_url("AWS RDS")
    
    def setup_digital_ocean(self):
        """Setup Digital Ocean Managed Database."""
        print("\n=== Digital Ocean Managed Database Setup ===")
        print("1. Go to Digital Ocean Control Panel")
        print("2. Click 'Create' -> 'Databases'")
        print("3. Choose 'PostgreSQL'")
        print("4. Select datacenter region closest to your users")
        print("5. Choose plan (Basic $15/month for production)")
        print("6. Database name: solana-trading-bot")
        print("7. After creation, get connection details from dashboard")
        
        return self.get_user_database_url("Digital Ocean")
    
    def setup_railway(self):
        """Setup Railway PostgreSQL database."""
        print("\n=== Railway PostgreSQL Setup ===")
        print("1. Go to https://railway.app")
        print("2. Create new project")
        print("3. Add PostgreSQL database")
        print("4. Go to database -> Connect tab")
        print("5. Copy the PostgreSQL connection URL")
        print("6. Railway provides $5/month free tier")
        
        return self.get_user_database_url("Railway")
    
    def setup_render(self):
        """Setup Render PostgreSQL database."""
        print("\n=== Render PostgreSQL Setup ===")
        print("1. Go to https://render.com")
        print("2. Create new PostgreSQL database")
        print("3. Choose plan (free tier available)")
        print("4. Database name: solana-trading-bot")
        print("5. Copy connection URL from dashboard")
        
        return self.get_user_database_url("Render")
    
    def setup_supabase(self):
        """Setup Supabase PostgreSQL database."""
        print("\n=== Supabase PostgreSQL Setup ===")
        print("1. Go to https://supabase.com")
        print("2. Create new project")
        print("3. Choose region")
        print("4. Go to Settings -> Database")
        print("5. Copy connection string")
        print("6. Supabase has generous free tier")
        
        return self.get_user_database_url("Supabase")
    
    def setup_planetscale(self):
        """Setup PlanetScale MySQL database."""
        print("\n=== PlanetScale MySQL Setup ===")
        print("Note: This would require schema modifications for MySQL compatibility")
        print("1. Go to https://planetscale.com")
        print("2. Create new database")
        print("3. Create branch (main)")
        print("4. Get connection details")
        print("Warning: Requires changing PostgreSQL-specific code to MySQL")
        
        return self.get_user_database_url("PlanetScale")
    
    def get_user_database_url(self, provider_name):
        """Get database URL from user input."""
        print(f"\nAfter setting up {provider_name}, please provide:")
        database_url = input("Enter the database connection URL: ").strip()
        
        if not database_url:
            print("No URL provided. Skipping this provider.")
            return None
        
        # Test the connection
        if self.test_database_connection(database_url):
            print(f"✓ Successfully connected to {provider_name} database!")
            return database_url
        else:
            print(f"✗ Failed to connect to {provider_name} database.")
            return None
    
    def test_database_connection(self, database_url):
        """Test database connection."""
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def migrate_data(self, source_url, target_url):
        """Migrate data from source to target database."""
        print(f"\n=== Migrating Data ===")
        print(f"Source: {source_url[:30]}...")
        print(f"Target: {target_url[:30]}...")
        
        try:
            # Create engines
            source_engine = create_engine(source_url)
            target_engine = create_engine(target_url)
            
            # Get table names from source
            with source_engine.connect() as source_conn:
                metadata = MetaData()
                metadata.reflect(bind=source_engine)
                tables = metadata.tables.keys()
                
                print(f"Found {len(tables)} tables to migrate: {list(tables)}")
                
                # Migrate each table
                for table_name in tables:
                    try:
                        # Read data from source
                        result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
                        rows = result.fetchall()
                        
                        if rows:
                            # Get column names
                            columns = result.keys()
                            
                            # Insert into target
                            with target_engine.connect() as target_conn:
                                # Create table structure first
                                table = Table(table_name, metadata, autoload_with=source_engine)
                                table.create(target_engine, checkfirst=True)
                                
                                # Insert data
                                for row in rows:
                                    row_dict = dict(zip(columns, row))
                                    target_conn.execute(table.insert().values(row_dict))
                                
                                target_conn.commit()
                            
                            print(f"✓ Migrated {len(rows)} rows from {table_name}")
                        else:
                            print(f"✓ Table {table_name} is empty, creating structure only")
                    
                    except Exception as table_error:
                        print(f"✗ Failed to migrate table {table_name}: {table_error}")
            
            print("✓ Data migration completed!")
            return True
            
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            return False
    
    def update_environment_config(self, database_url):
        """Update environment configuration with new database URL."""
        config_updates = f"""
# Add this to your environment variables or .env file:
DATABASE_URL={database_url}

# For Railway deployment:
railway variables:set DATABASE_URL="{database_url}"

# For AWS deployment:
aws ssm put-parameter --name "/solana-bot/database-url" --value "{database_url}" --type "SecureString"

# For Docker deployment:
docker run -e DATABASE_URL="{database_url}" your-app

# Update your config.py file:
PRODUCTION_DATABASE_URL = "{database_url}"
"""
        
        with open('database_config_update.txt', 'w') as f:
            f.write(config_updates)
        
        print(f"\n✓ Configuration saved to 'database_config_update.txt'")
        print("Apply these settings to your deployment environment.")
    
    def run_interactive_setup(self):
        """Run interactive database setup."""
        print("=== Production Database Setup for Solana Trading Bot ===")
        print("\nYour current Neon database is hitting quota limits.")
        print("Let's set up a reliable production database.\n")
        
        print("Available providers:")
        for i, (key, _) in enumerate(self.supported_providers.items(), 1):
            provider_name = key.replace('_', ' ').title()
            print(f"{i}. {provider_name}")
        
        print("\nRecommended providers for production:")
        print("• AWS RDS (most reliable, scalable)")
        print("• Digital Ocean (good balance of price/performance)")
        print("• Railway (developer-friendly)")
        print("• Render (simple setup)")
        
        while True:
            try:
                choice = input("\nEnter provider number (1-6): ").strip()
                choice_idx = int(choice) - 1
                
                if 0 <= choice_idx < len(self.supported_providers):
                    provider_key = list(self.supported_providers.keys())[choice_idx]
                    setup_func = self.supported_providers[provider_key]
                    
                    # Run setup for chosen provider
                    new_database_url = setup_func()
                    
                    if new_database_url:
                        # Ask about data migration
                        current_db = "postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
                        
                        migrate = input("\nDo you want to migrate existing data? (y/n): ").strip().lower()
                        if migrate == 'y':
                            print("\nTesting current database connection...")
                            if self.test_database_connection(current_db):
                                self.migrate_data(current_db, new_database_url)
                            else:
                                print("Cannot connect to current database for migration.")
                        
                        # Update configuration
                        self.update_environment_config(new_database_url)
                        
                        print(f"\n✓ Database setup completed!")
                        print(f"✓ New database URL configured")
                        print(f"✓ Ready for production deployment")
                        
                        return new_database_url
                    else:
                        print("Setup failed. Try another provider?")
                        continue
                else:
                    print("Invalid choice. Please enter a number between 1-6.")
            
            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                print("\nSetup cancelled.")
                return None

def main():
    """Main function."""
    setup = ProductionDatabaseSetup()
    
    print("Starting production database setup...")
    print("This will help you move away from quota-limited databases.")
    
    result = setup.run_interactive_setup()
    
    if result:
        print(f"\n{'='*50}")
        print("SUCCESS! Your production database is ready.")
        print("Next steps:")
        print("1. Update your deployment with the new DATABASE_URL")
        print("2. Restart your application")
        print("3. Monitor the health endpoints to verify connectivity")
        print(f"{'='*50}")
    else:
        print("Setup was not completed. You can run this script again anytime.")

if __name__ == "__main__":
    main()