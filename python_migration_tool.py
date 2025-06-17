"""
Python-based Database Migration Tool
===================================
Direct Python migration from Neon to AWS RDS without external pg_dump dependency.
Handles table creation, data transfer, and verification.
"""

import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.exc import OperationalError
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PythonMigrator:
    """Python-based database migration tool"""
    
    def __init__(self):
        # Source database (Neon)
        self.source_url = os.environ.get('DATABASE_URL') or \
                         "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        
        # Target database (AWS RDS)
        self.target_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
        
        # Backup directory
        self.backup_dir = Path("migration_backup")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Tables to migrate in order (respecting foreign keys)
        self.table_order = [
            'referral_code',
            'user', 
            'transaction',
            'trading_position',
            'trading_cycle',
            'support_ticket',
            'sender_wallet',
            'referral_reward',
            'milestone_tracker',
            'profit',
            'broadcast_message',
            'admin_message',
            'system_settings',
            'user_metrics',
            'daily_snapshot'
        ]
    
    def test_connections(self):
        """Test both database connections"""
        logger.info("Testing database connections...")
        
        # Test source
        try:
            source_engine = create_engine(self.source_url, connect_args={'connect_timeout': 10})
            with source_engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                row = result.fetchone()
                version = row[0] if row else "Unknown"
                logger.info(f"✓ Source DB (Neon) connected: {version[:50]}...")
        except Exception as e:
            logger.error(f"✗ Source DB connection failed: {e}")
            return False
        
        # Test target
        try:
            target_engine = create_engine(self.target_url, connect_args={'connect_timeout': 10})
            with target_engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                row = result.fetchone()
                version = row[0] if row else "Unknown"
                logger.info(f"✓ Target DB (AWS RDS) connected: {version[:50]}...")
        except Exception as e:
            logger.error(f"✗ Target DB connection failed: {e}")
            return False
        
        return True
    
    def get_source_schema(self):
        """Get complete schema from source database"""
        logger.info("Analyzing source database schema...")
        
        try:
            source_engine = create_engine(self.source_url)
            inspector = inspect(source_engine)
            
            schema_info = {}
            existing_tables = inspector.get_table_names()
            
            with source_engine.connect() as conn:
                for table in existing_tables:
                    if table in self.table_order:
                        # Get row count
                        result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        row_count = result.fetchone()[0]
                        
                        # Get columns
                        columns = inspector.get_columns(table)
                        
                        schema_info[table] = {
                            'row_count': row_count,
                            'columns': [col['name'] for col in columns],
                            'exists': True
                        }
                        
                        logger.info(f"  {table}: {row_count} rows, {len(columns)} columns")
                    
            # Save schema info
            with open(self.backup_dir / "source_schema.json", "w") as f:
                json.dump(schema_info, f, indent=2, default=str)
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Schema analysis failed: {e}")
            return None
    
    def create_target_schema(self):
        """Create schema in target database using SQLAlchemy models"""
        logger.info("Creating target database schema...")
        
        try:
            # Import the app context to create tables
            from app import app, db
            
            # Temporarily update the app to use target database
            original_url = app.config['SQLALCHEMY_DATABASE_URI']
            app.config['SQLALCHEMY_DATABASE_URI'] = self.target_url
            
            with app.app_context():
                # Create all tables
                db.create_all()
                logger.info("✓ Target database schema created")
            
            # Restore original URL
            app.config['SQLALCHEMY_DATABASE_URI'] = original_url
            
            return True
            
        except Exception as e:
            logger.error(f"Target schema creation failed: {e}")
            return False
    
    def migrate_table_data(self, table_name):
        """Migrate data for a specific table"""
        logger.info(f"Migrating table: {table_name}")
        
        try:
            source_engine = create_engine(self.source_url)
            target_engine = create_engine(self.target_url)
            
            with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
                # Get row count first
                result = source_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                total_rows = result.fetchone()[0]
                
                if total_rows == 0:
                    logger.info(f"  {table_name}: No data to migrate")
                    return True
                
                # Get all data from source
                result = source_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                rows = result.fetchall()
                column_names = result.keys()
                
                if not rows:
                    logger.info(f"  {table_name}: No data found")
                    return True
                
                # Clear target table first
                target_conn.execute(text(f'DELETE FROM "{table_name}"'))
                target_conn.commit()
                
                # Prepare insert statement
                columns_str = ', '.join([f'"{col}"' for col in column_names])
                placeholders = ', '.join(['%s'] * len(column_names))
                insert_sql = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
                
                # Insert data in batches
                batch_size = 100
                total_inserted = 0
                
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    batch_data = [tuple(row) for row in batch]
                    
                    # Use raw psycopg2 for batch insert
                    import psycopg2
                    from urllib.parse import urlparse
                    
                    parsed = urlparse(self.target_url)
                    raw_conn = psycopg2.connect(
                        host=parsed.hostname,
                        port=parsed.port,
                        user=parsed.username,
                        password=parsed.password,
                        database=parsed.path.lstrip('/')
                    )
                    
                    with raw_conn.cursor() as cur:
                        cur.executemany(insert_sql, batch_data)
                        raw_conn.commit()
                    
                    raw_conn.close()
                    total_inserted += len(batch)
                    
                    if total_inserted % 100 == 0 or total_inserted == len(rows):
                        logger.info(f"  {table_name}: {total_inserted}/{len(rows)} rows migrated")
                
                logger.info(f"✓ {table_name}: {total_inserted} rows migrated successfully")
                return True
                
        except Exception as e:
            logger.error(f"✗ Migration failed for {table_name}: {e}")
            return False
    
    def verify_migration(self):
        """Verify migration by comparing row counts"""
        logger.info("Verifying migration...")
        
        try:
            source_engine = create_engine(self.source_url)
            target_engine = create_engine(self.target_url)
            
            verification_results = {}
            
            with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
                for table in self.table_order:
                    try:
                        # Get source count
                        result = source_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        source_count = result.fetchone()[0]
                        
                        # Get target count
                        result = target_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        target_count = result.fetchone()[0]
                        
                        match = source_count == target_count
                        verification_results[table] = {
                            'source_count': source_count,
                            'target_count': target_count,
                            'match': match
                        }
                        
                        status = "✓" if match else "✗"
                        logger.info(f"{status} {table}: Source {source_count}, Target {target_count}")
                        
                    except Exception as e:
                        logger.warning(f"Verification failed for {table}: {e}")
                        verification_results[table] = {'error': str(e)}
            
            # Save verification results
            with open(self.backup_dir / "verification_results.json", "w") as f:
                json.dump(verification_results, f, indent=2)
            
            # Check overall success
            successful_tables = sum(1 for result in verification_results.values() 
                                  if isinstance(result, dict) and result.get('match', False))
            total_tables = len([r for r in verification_results.values() if 'error' not in r])
            
            if successful_tables == total_tables and total_tables > 0:
                logger.info(f"✅ Migration verification successful: {successful_tables}/{total_tables} tables match")
                return True
            else:
                logger.error(f"❌ Migration verification failed: {successful_tables}/{total_tables} tables match")
                return False
                
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    def update_configuration(self):
        """Update configuration files for AWS RDS"""
        logger.info("Updating configuration files...")
        
        # Create .env.aws
        env_content = f"""# AWS RDS Configuration
DATABASE_URL={self.target_url}
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', '')}
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'change-this-secret')}
MIN_DEPOSIT=0.1
BOT_ENVIRONMENT=aws
"""
        
        with open('.env.aws', 'w') as f:
            f.write(env_content)
        
        logger.info("✓ Created .env.aws configuration")
        
        # Create migration summary
        summary = {
            'migration_date': datetime.now().isoformat(),
            'source_database': 'Neon',
            'target_database': 'AWS RDS',
            'target_url': self.target_url,
            'status': 'completed',
            'next_steps': [
                'Stop current bot',
                'Copy .env.aws to .env',
                'Start bot with new configuration',
                'Run post-migration tests'
            ]
        }
        
        with open(self.backup_dir / "migration_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info("✓ Created migration summary")
    
    def run_migration(self):
        """Run complete migration process"""
        logger.info("=== Starting Python-based AWS RDS Migration ===")
        
        # Step 1: Test connections
        if not self.test_connections():
            logger.error("Connection test failed")
            return False
        
        # Step 2: Analyze source schema
        schema_info = self.get_source_schema()
        if not schema_info:
            logger.error("Schema analysis failed")
            return False
        
        # Step 3: Create target schema
        if not self.create_target_schema():
            logger.error("Target schema creation failed")
            return False
        
        # Step 4: Migrate data table by table
        failed_tables = []
        for table in self.table_order:
            if table in schema_info and schema_info[table]['exists']:
                if not self.migrate_table_data(table):
                    failed_tables.append(table)
            else:
                logger.info(f"Skipping {table} - not found in source")
        
        if failed_tables:
            logger.error(f"Migration failed for tables: {failed_tables}")
            return False
        
        # Step 5: Verify migration
        if not self.verify_migration():
            logger.error("Migration verification failed")
            return False
        
        # Step 6: Update configuration
        self.update_configuration()
        
        logger.info("=== Migration Completed Successfully ===")
        return True

def main():
    """Run the migration"""
    migrator = PythonMigrator()
    
    try:
        success = migrator.run_migration()
        
        if success:
            print("\n✅ Migration completed successfully!")
            print("Your data has been migrated to AWS RDS")
            print("\nNext steps:")
            print("1. Copy .env.aws to .env: cp .env.aws .env")
            print("2. Restart your bot")
            print("3. Test bot functionality")
        else:
            print("\n❌ Migration failed!")
            print("Check the logs for details")
            
    except Exception as e:
        logger.error(f"Migration crashed: {e}")
        print(f"\n💥 Migration error: {e}")

if __name__ == "__main__":
    main()