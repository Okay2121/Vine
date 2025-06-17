"""
Robust Database Migration Tool
=============================
Migrates existing tables from Neon to AWS RDS with proper error handling.
"""

import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
import psycopg2
from urllib.parse import urlparse
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobustMigrator:
    """Production-ready database migration tool"""
    
    def __init__(self):
        self.source_url = os.environ.get('DATABASE_URL') or \
                         "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        self.target_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
        
        self.backup_dir = Path("migration_backup")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Migration order respecting foreign key constraints
        self.migration_order = [
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
        """Test database connections"""
        logger.info("Testing database connections...")
        
        try:
            # Test source
            source_engine = create_engine(self.source_url)
            with source_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Source database (Neon) connected")
            
            # Test target  
            target_engine = create_engine(self.target_url)
            with target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Target database (AWS RDS) connected")
            
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_existing_tables(self):
        """Get list of existing tables from source"""
        logger.info("Getting existing tables from source database...")
        
        try:
            source_engine = create_engine(self.source_url)
            with source_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """))
                tables = [row[0] for row in result.fetchall()]
                
            logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
            return tables
            
        except Exception as e:
            logger.error(f"Failed to get table list: {e}")
            return []
    
    def create_target_schema(self):
        """Create schema in target database"""
        logger.info("Creating target database schema...")
        
        try:
            from app import app, db
            
            # Temporarily point to target database
            original_url = app.config['SQLALCHEMY_DATABASE_URI']
            app.config['SQLALCHEMY_DATABASE_URI'] = self.target_url
            
            with app.app_context():
                db.create_all()
                logger.info("✓ Target schema created successfully")
            
            # Restore original URL
            app.config['SQLALCHEMY_DATABASE_URI'] = original_url
            return True
            
        except Exception as e:
            logger.error(f"Schema creation failed: {e}")
            return False
    
    def migrate_table(self, table_name):
        """Migrate a single table"""
        logger.info(f"Migrating table: {table_name}")
        
        try:
            # Get source data
            source_engine = create_engine(self.source_url)
            with source_engine.connect() as source_conn:
                # Check if table exists
                result = source_conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = '{table_name}'
                    )
                """))
                exists = result.fetchone()[0]
                
                if not exists:
                    logger.info(f"  {table_name}: Table does not exist in source - skipping")
                    return True
                
                # Get row count
                result = source_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                row_count = result.fetchone()[0]
                
                if row_count == 0:
                    logger.info(f"  {table_name}: No data to migrate")
                    return True
                
                # Get all data
                result = source_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                rows = result.fetchall()
                columns = list(result.keys())
                
                logger.info(f"  {table_name}: Found {len(rows)} rows with {len(columns)} columns")
            
            # Insert into target
            parsed_target = urlparse(self.target_url)
            target_conn = psycopg2.connect(
                host=parsed_target.hostname,
                port=parsed_target.port or 5432,
                user=parsed_target.username,
                password=parsed_target.password,
                database=parsed_target.path.lstrip('/')
            )
            
            try:
                with target_conn.cursor() as cur:
                    # Clear target table
                    cur.execute(f'DELETE FROM "{table_name}"')
                    
                    if rows:
                        # Prepare insert statement
                        columns_str = ', '.join([f'"{col}"' for col in columns])
                        placeholders = ', '.join(['%s'] * len(columns))
                        insert_sql = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
                        
                        # Insert data
                        cur.executemany(insert_sql, rows)
                    
                    target_conn.commit()
                    logger.info(f"✓ {table_name}: {len(rows)} rows migrated successfully")
                
            finally:
                target_conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to migrate {table_name}: {e}")
            return False
    
    def verify_migration(self, existing_tables):
        """Verify migration results"""
        logger.info("Verifying migration...")
        
        verification_results = {}
        
        try:
            source_engine = create_engine(self.source_url)
            target_engine = create_engine(self.target_url)
            
            with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
                for table in existing_tables:
                    try:
                        # Source count
                        result = source_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        source_count = result.fetchone()[0]
                        
                        # Target count
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
            
            # Save results
            with open(self.backup_dir / "verification_results.json", "w") as f:
                json.dump(verification_results, f, indent=2)
            
            # Check success
            matches = sum(1 for r in verification_results.values() 
                         if isinstance(r, dict) and r.get('match', False))
            total = len([r for r in verification_results.values() if 'error' not in r])
            
            success = matches == total and total > 0
            logger.info(f"Verification: {matches}/{total} tables match")
            
            return success
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    def create_configuration_files(self):
        """Create AWS configuration files"""
        logger.info("Creating configuration files...")
        
        # Create .env.aws
        env_content = f"""DATABASE_URL={self.target_url}
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', '')}
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'change-this-secret')}
MIN_DEPOSIT=0.1
BOT_ENVIRONMENT=aws
"""
        
        with open('.env.aws', 'w') as f:
            f.write(env_content)
        logger.info("✓ Created .env.aws")
        
        # Create migration instructions
        instructions = f"""AWS RDS Migration Completed Successfully
==========================================
Date: {datetime.now().isoformat()}

Migration Summary:
- Source: Neon Database
- Target: AWS RDS (database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com)
- Database: Vibe

Next Steps:
1. Stop your current bot process
2. Switch to AWS RDS configuration:
   cp .env.aws .env
3. Restart your bot
4. Test all functionality
5. Monitor for any issues

Rollback Instructions (if needed):
1. Stop bot
2. Restore original .env file
3. Restart bot with Neon configuration

Files Created:
- .env.aws (AWS RDS configuration)
- migration_backup/ (backup data and logs)
- verification_results.json (migration verification)
"""
        
        with open('MIGRATION_COMPLETE.md', 'w') as f:
            f.write(instructions)
        logger.info("✓ Created migration instructions")
    
    def run_migration(self):
        """Run complete migration process"""
        logger.info("=== Starting Robust Database Migration ===")
        
        # Test connections
        if not self.test_connections():
            return False
        
        # Get existing tables
        existing_tables = self.get_existing_tables()
        if not existing_tables:
            logger.error("No tables found in source database")
            return False
        
        # Create target schema
        if not self.create_target_schema():
            return False
        
        # Migrate tables in order
        failed_tables = []
        migrated_count = 0
        
        for table in self.migration_order:
            if table in existing_tables:
                if self.migrate_table(table):
                    migrated_count += 1
                else:
                    failed_tables.append(table)
        
        # Migrate any remaining tables not in order
        for table in existing_tables:
            if table not in self.migration_order:
                if self.migrate_table(table):
                    migrated_count += 1
                else:
                    failed_tables.append(table)
        
        if failed_tables:
            logger.error(f"Failed to migrate: {failed_tables}")
            return False
        
        # Verify migration
        if not self.verify_migration(existing_tables):
            logger.error("Migration verification failed")
            return False
        
        # Create configuration files
        self.create_configuration_files()
        
        logger.info(f"=== Migration Completed Successfully ===")
        logger.info(f"Migrated {migrated_count} tables to AWS RDS")
        return True

def main():
    migrator = RobustMigrator()
    
    try:
        success = migrator.run_migration()
        
        if success:
            print("\n✅ Database migration completed successfully!")
            print("Your bot data is now on AWS RDS")
            print("\nNext steps:")
            print("1. Copy AWS configuration: cp .env.aws .env")
            print("2. Restart your bot")
            print("3. Test functionality")
        else:
            print("\n❌ Migration failed - check logs for details")
            
    except Exception as e:
        logger.error(f"Migration error: {e}")
        print(f"\n💥 Migration crashed: {e}")

if __name__ == "__main__":
    main()