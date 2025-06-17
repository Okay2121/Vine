"""
Simple AWS RDS Migration Tool
============================
Straightforward migration from Neon to AWS RDS with built-in safety checks.
"""

import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMigrator:
    """Simple, reliable database migration tool"""
    
    def __init__(self):
        # Current Neon DB
        self.neon_host = "ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech"
        self.neon_user = "neondb_owner"
        self.neon_password = "npg_9Hdj1LfbemJW"
        self.neon_db = "neondb"
        
        # AWS RDS target
        self.aws_host = "database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com"
        self.aws_user = "postgres"
        self.aws_password = "Checker97$"
        self.aws_db = "Vibe"
        
        # Backup directory
        self.backup_dir = Path("migration_backup")
        self.backup_dir.mkdir(exist_ok=True)
        
    def test_neon_connection(self):
        """Test connection to Neon database"""
        logger.info("Testing Neon database connection...")
        
        test_cmd = [
            'psql',
            f'postgresql://{self.neon_user}:{self.neon_password}@{self.neon_host}/{self.neon_db}?sslmode=require',
            '-c', 'SELECT version();'
        ]
        
        try:
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("✓ Neon database connection successful")
                return True
            else:
                logger.error(f"✗ Neon connection failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"✗ Neon connection test failed: {e}")
            return False
    
    def test_aws_connection(self):
        """Test connection to AWS RDS"""
        logger.info("Testing AWS RDS connection...")
        
        test_cmd = [
            'psql',
            f'postgresql://{self.aws_user}:{self.aws_password}@{self.aws_host}:5432/{self.aws_db}',
            '-c', 'SELECT version();'
        ]
        
        try:
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("✓ AWS RDS connection successful")
                return True
            else:
                logger.error(f"✗ AWS RDS connection failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"✗ AWS RDS connection test failed: {e}")
            return False
    
    def create_backup(self):
        """Create backup of Neon database"""
        logger.info("Creating database backup...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.sql"
        
        dump_cmd = [
            'pg_dump',
            f'postgresql://{self.neon_user}:{self.neon_password}@{self.neon_host}/{self.neon_db}?sslmode=require',
            '--verbose',
            '--clean',
            '--if-exists',
            '--create',
            '-f', str(backup_file)
        ]
        
        try:
            logger.info(f"Creating backup: {backup_file}")
            result = subprocess.run(dump_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                size_kb = backup_file.stat().st_size / 1024
                logger.info(f"✓ Backup created: {backup_file} ({size_kb:.1f} KB)")
                return str(backup_file)
            else:
                logger.error(f"✗ Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"✗ Backup creation failed: {e}")
            return None
    
    def restore_to_aws(self, backup_file):
        """Restore backup to AWS RDS"""
        logger.info(f"Restoring to AWS RDS: {backup_file}")
        
        restore_cmd = [
            'psql',
            f'postgresql://{self.aws_user}:{self.aws_password}@{self.aws_host}:5432/{self.aws_db}',
            '-f', backup_file,
            '--verbose'
        ]
        
        try:
            result = subprocess.run(restore_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                logger.info("✓ Restore to AWS RDS completed")
                return True
            else:
                logger.error(f"✗ Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Restore failed: {e}")
            return False
    
    def update_environment_config(self):
        """Update configuration files for AWS RDS"""
        logger.info("Updating configuration files...")
        
        aws_database_url = f"postgresql://{self.aws_user}:{self.aws_password}@{self.aws_host}:5432/{self.aws_db}"
        
        # Create .env.aws file
        env_content = f"""# AWS RDS Configuration
DATABASE_URL={aws_database_url}
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', '')}
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'change-this-secret')}
MIN_DEPOSIT=0.1
BOT_ENVIRONMENT=aws
"""
        
        with open('.env.aws', 'w') as f:
            f.write(env_content)
        
        logger.info("✓ Created .env.aws configuration")
        
        # Update app.py fallback URL
        try:
            with open('app.py', 'r') as f:
                content = f.read()
            
            # Backup original
            with open(f'app.py.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}', 'w') as f:
                f.write(content)
            
            # Update fallback URL
            old_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
            new_content = content.replace(old_url, aws_database_url)
            
            with open('app.py', 'w') as f:
                f.write(new_content)
            
            logger.info("✓ Updated app.py with AWS RDS URL")
            
        except Exception as e:
            logger.warning(f"Could not update app.py automatically: {e}")
    
    def run_migration(self):
        """Run complete migration process"""
        logger.info("=== Starting AWS RDS Migration ===")
        
        # Step 1: Test connections
        if not self.test_neon_connection():
            logger.error("Cannot connect to Neon database - aborting")
            return False
        
        if not self.test_aws_connection():
            logger.error("Cannot connect to AWS RDS - aborting") 
            return False
        
        # Step 2: Create backup
        backup_file = self.create_backup()
        if not backup_file:
            logger.error("Backup creation failed - aborting")
            return False
        
        # Step 3: Restore to AWS
        if not self.restore_to_aws(backup_file):
            logger.error("Restore to AWS failed - aborting")
            return False
        
        # Step 4: Update configuration
        self.update_environment_config()
        
        logger.info("=== Migration Completed Successfully ===")
        logger.info("Next steps:")
        logger.info("1. Stop your current bot")
        logger.info("2. Copy .env.aws to .env: cp .env.aws .env")
        logger.info("3. Start bot with new configuration")
        logger.info("4. Test bot functionality")
        
        return True

def main():
    """Run migration"""
    migrator = SimpleMigrator()
    
    print("AWS RDS Migration Tool")
    print("=====================")
    print(f"Source: Neon Database")
    print(f"Target: AWS RDS (database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com)")
    print()
    
    try:
        success = migrator.run_migration()
        if success:
            print("\n✅ Migration completed successfully!")
        else:
            print("\n❌ Migration failed!")
            
    except KeyboardInterrupt:
        print("\nMigration cancelled by user")
    except Exception as e:
        print(f"\nMigration error: {e}")

if __name__ == "__main__":
    main()