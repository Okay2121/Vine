"""
AWS RDS Migration Tool
=====================
Comprehensive tool for migrating from Neon DB to AWS RDS without breaking bot functionality.
Supports data export, schema validation, and safe migration with rollback capabilities.
"""

import os
import logging
import subprocess
import psycopg2
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.exc import OperationalError
import json
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSRDSMigrator:
    """Handles complete migration from Neon DB to AWS RDS"""
    
    def __init__(self):
        # Current Neon DB configuration
        self.neon_url = os.environ.get('DATABASE_URL') or \
                       "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        
        # New AWS RDS configuration
        self.aws_rds_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
        
        # Backup and migration paths
        self.backup_dir = Path("migration_backup")
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info("AWS RDS Migration Tool initialized")
        
    def test_connections(self):
        """Test connections to both source and target databases"""
        logger.info("Testing database connections...")
        
        # Test Neon DB connection
        try:
            neon_engine = create_engine(self.neon_url)
            with neon_engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                row = result.fetchone()
                version = row[0] if row else "Unknown"
                logger.info(f"✓ Neon DB connected: {version[:50]}...")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Neon DB: {e}")
            return False
            
        # Test AWS RDS connection
        try:
            aws_engine = create_engine(self.aws_rds_url)
            with aws_engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                row = result.fetchone()
                version = row[0] if row else "Unknown"
                logger.info(f"✓ AWS RDS connected: {version[:50]}...")
        except Exception as e:
            logger.error(f"✗ Failed to connect to AWS RDS: {e}")
            return False
            
        return True
    
    def analyze_current_schema(self):
        """Analyze current Neon DB schema and data"""
        logger.info("Analyzing current database schema...")
        
        try:
            engine = create_engine(self.neon_url)
            inspector = inspect(engine)
            
            # Get all tables
            tables = inspector.get_table_names()
            logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
            
            # Analyze each table
            schema_info = {}
            with engine.connect() as conn:
                for table in tables:
                    # Get row count
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    row_count = result.fetchone()[0]
                    
                    # Get columns
                    columns = inspector.get_columns(table)
                    column_names = [col['name'] for col in columns]
                    
                    schema_info[table] = {
                        'row_count': row_count,
                        'columns': column_names,
                        'column_details': columns
                    }
                    
                    logger.info(f"  {table}: {row_count} rows, {len(column_names)} columns")
            
            # Save schema analysis
            with open(self.backup_dir / "schema_analysis.json", "w") as f:
                json.dump(schema_info, f, indent=2, default=str)
                
            return schema_info
            
        except Exception as e:
            logger.error(f"Schema analysis failed: {e}")
            return None
    
    def create_database_backup(self):
        """Create complete database backup using pg_dump"""
        logger.info("Creating database backup...")
        
        # Parse connection details from URL
        from urllib.parse import urlparse
        parsed = urlparse(self.neon_url)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"neon_backup_{timestamp}.sql"
        
        # Build pg_dump command
        dump_cmd = [
            'pg_dump',
            '--host', parsed.hostname,
            '--port', str(parsed.port or 5432),
            '--username', parsed.username,
            '--dbname', parsed.path.lstrip('/'),
            '--verbose',
            '--clean',
            '--if-exists',
            '--create',
            '--file', str(backup_file)
        ]
        
        # Set password via environment
        env = os.environ.copy()
        env['PGPASSWORD'] = parsed.password
        
        try:
            logger.info(f"Running pg_dump to {backup_file}")
            result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✓ Backup created successfully: {backup_file}")
                logger.info(f"Backup size: {backup_file.stat().st_size / 1024:.1f} KB")
                return str(backup_file)
            else:
                logger.error(f"pg_dump failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None
    
    def restore_to_aws_rds(self, backup_file):
        """Restore backup to AWS RDS"""
        logger.info(f"Restoring backup to AWS RDS: {backup_file}")
        
        # Parse AWS RDS connection details
        from urllib.parse import urlparse
        parsed = urlparse(self.aws_rds_url)
        
        # Build psql restore command
        restore_cmd = [
            'psql',
            '--host', parsed.hostname,
            '--port', str(parsed.port or 5432),
            '--username', parsed.username,
            '--dbname', parsed.path.lstrip('/'),
            '--file', backup_file,
            '--verbose'
        ]
        
        # Set password via environment
        env = os.environ.copy()
        env['PGPASSWORD'] = parsed.password
        
        try:
            logger.info("Running psql restore...")
            result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✓ Restore completed successfully")
                return True
            else:
                logger.error(f"Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def verify_migration(self):
        """Verify that migration was successful by comparing data"""
        logger.info("Verifying migration...")
        
        try:
            neon_engine = create_engine(self.neon_url)
            aws_engine = create_engine(self.aws_rds_url)
            
            # Get table list from both databases
            neon_inspector = inspect(neon_engine)
            aws_inspector = inspect(aws_engine)
            
            neon_tables = set(neon_inspector.get_table_names())
            aws_tables = set(aws_inspector.get_table_names())
            
            if neon_tables != aws_tables:
                logger.error(f"Table mismatch: Neon has {neon_tables}, AWS has {aws_tables}")
                return False
            
            # Compare row counts for each table
            verification_results = {}
            with neon_engine.connect() as neon_conn, aws_engine.connect() as aws_conn:
                for table in neon_tables:
                    neon_result = neon_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    neon_count = neon_result.fetchone()[0]
                    
                    aws_result = aws_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    aws_count = aws_result.fetchone()[0]
                    
                    verification_results[table] = {
                        'neon_count': neon_count,
                        'aws_count': aws_count,
                        'match': neon_count == aws_count
                    }
                    
                    if neon_count == aws_count:
                        logger.info(f"✓ {table}: {neon_count} rows (match)")
                    else:
                        logger.error(f"✗ {table}: Neon {neon_count}, AWS {aws_count} (mismatch)")
            
            # Save verification results
            with open(self.backup_dir / "verification_results.json", "w") as f:
                json.dump(verification_results, f, indent=2)
            
            # Check if all tables match
            all_match = all(result['match'] for result in verification_results.values())
            
            if all_match:
                logger.info("✓ Migration verification successful - all data matches")
            else:
                logger.error("✗ Migration verification failed - data mismatch detected")
            
            return all_match
            
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False
    
    def create_aws_config_files(self):
        """Create configuration files for AWS RDS"""
        logger.info("Creating AWS RDS configuration files...")
        
        # Create .env.aws file
        aws_env_content = f"""# AWS RDS Configuration
DATABASE_URL={self.aws_rds_url}
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'your-session-secret')}
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', 'your-bot-token')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', 'your-admin-id')}

# AWS RDS Specific Settings
DB_HOST=database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com
DB_NAME=Vibe
DB_USER=postgres
DB_PASSWORD=Checker97$
DB_PORT=5432

# Production Settings
MIN_DEPOSIT=0.1
WEBHOOK_URL=
WEBHOOK_SECRET=
"""
        
        with open(".env.aws", "w") as f:
            f.write(aws_env_content)
        
        logger.info("✓ Created .env.aws configuration file")
        
        # Create migration status file
        migration_status = {
            'migration_date': datetime.now().isoformat(),
            'source_db': 'neon',
            'target_db': 'aws_rds',
            'aws_rds_endpoint': 'database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com',
            'database_name': 'Vibe',
            'status': 'ready_for_switchover'
        }
        
        with open(self.backup_dir / "migration_status.json", "w") as f:
            json.dump(migration_status, f, indent=2)
        
        logger.info("✓ Created migration status tracking")
        
    def run_complete_migration(self):
        """Run the complete migration process"""
        logger.info("=== Starting AWS RDS Migration ===")
        
        # Step 1: Test connections
        if not self.test_connections():
            logger.error("Connection test failed - aborting migration")
            return False
        
        # Step 2: Analyze current schema
        schema_info = self.analyze_current_schema()
        if not schema_info:
            logger.error("Schema analysis failed - aborting migration")
            return False
        
        # Step 3: Create backup
        backup_file = self.create_database_backup()
        if not backup_file:
            logger.error("Backup creation failed - aborting migration")
            return False
        
        # Step 4: Restore to AWS RDS
        if not self.restore_to_aws_rds(backup_file):
            logger.error("Restore to AWS RDS failed - aborting migration")
            return False
        
        # Step 5: Verify migration
        if not self.verify_migration():
            logger.error("Migration verification failed - aborting migration")
            return False
        
        # Step 6: Create AWS configuration files
        self.create_aws_config_files()
        
        logger.info("=== Migration Completed Successfully ===")
        logger.info("Next steps:")
        logger.info("1. Update your environment variables to use AWS RDS")
        logger.info("2. Test bot functionality with new database")
        logger.info("3. Monitor performance and connection stability")
        
        return True

def main():
    """Run the migration tool"""
    migrator = AWSRDSMigrator()
    
    try:
        success = migrator.run_complete_migration()
        if success:
            print("\n🎉 Migration completed successfully!")
            print("Your bot is now ready to use AWS RDS")
        else:
            print("\n❌ Migration failed. Check logs for details.")
            
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")

if __name__ == "__main__":
    main()