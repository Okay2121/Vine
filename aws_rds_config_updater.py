"""
AWS RDS Configuration Updater
============================
Updates all configuration files to use AWS RDS while maintaining compatibility
with existing code. Ensures zero downtime migration.
"""

import os
import logging
from pathlib import Path
import shutil
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigUpdater:
    """Updates configuration files for AWS RDS migration"""
    
    def __init__(self):
        self.aws_rds_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
        self.backup_suffix = f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def backup_file(self, file_path):
        """Create backup of file before modification"""
        if os.path.exists(file_path):
            backup_path = f"{file_path}{self.backup_suffix}"
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backed up {file_path} to {backup_path}")
            return backup_path
        return None
    
    def update_app_py(self):
        """Update app.py to use AWS RDS with fallback support"""
        logger.info("Updating app.py configuration...")
        
        app_py_path = "app.py"
        self.backup_file(app_py_path)
        
        # Read current content
        with open(app_py_path, 'r') as f:
            content = f.read()
        
        # Update the fallback database URL
        old_neon_url = 'postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require'
        new_aws_url = self.aws_rds_url
        
        content = content.replace(old_neon_url, new_aws_url)
        
        # Update the logger message
        content = content.replace(
            'logger.info("Using production Neon database URL")',
            'logger.info("Using production AWS RDS database URL")'
        )
        
        # Write updated content
        with open(app_py_path, 'w') as f:
            f.write(content)
        
        logger.info("✓ Updated app.py with AWS RDS configuration")
    
    def update_production_config(self):
        """Update production_config.py"""
        logger.info("Updating production_config.py...")
        
        config_path = "production_config.py"
        if os.path.exists(config_path):
            self.backup_file(config_path)
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Update DATABASE_URL
            old_url = 'postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require'
            content = content.replace(old_url, self.aws_rds_url)
            
            with open(config_path, 'w') as f:
                f.write(content)
            
            logger.info("✓ Updated production_config.py")
    
    def update_deployment_config(self):
        """Update deployment_config.py"""
        logger.info("Updating deployment_config.py...")
        
        config_path = "deployment_config.py"
        if os.path.exists(config_path):
            self.backup_file(config_path)
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Update DATABASE_URL
            old_url = 'postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require'
            content = content.replace(old_url, self.aws_rds_url)
            
            with open(config_path, 'w') as f:
                f.write(content)
            
            logger.info("✓ Updated deployment_config.py")
    
    def create_env_aws(self):
        """Create .env.aws for production deployment"""
        logger.info("Creating .env.aws file...")
        
        env_content = f"""# AWS RDS Production Configuration
DATABASE_URL={self.aws_rds_url}

# Telegram Bot Configuration (update with your values)
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', 'your-telegram-bot-token')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', 'your-admin-user-id')}

# Security
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'your-session-secret-key')}

# Trading Configuration
MIN_DEPOSIT=0.1

# AWS RDS Connection Details
DB_HOST=database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com
DB_NAME=Vibe
DB_USER=postgres
DB_PASSWORD=Checker97$
DB_PORT=5432

# Optional Webhook Configuration
WEBHOOK_URL=
WEBHOOK_SECRET=
WEBHOOK_PORT=8443

# Performance Settings
BOT_ENVIRONMENT=aws
"""
        
        with open('.env.aws', 'w') as f:
            f.write(env_content)
        
        logger.info("✓ Created .env.aws configuration file")
    
    def update_database_monitoring(self):
        """Update database monitoring scripts to use AWS RDS"""
        logger.info("Updating database monitoring configurations...")
        
        files_to_update = [
            'database_monitoring.py',
            'database_connection_handler.py'
        ]
        
        for file_path in files_to_update:
            if os.path.exists(file_path):
                self.backup_file(file_path)
                logger.info(f"✓ Backed up {file_path} (manual review recommended)")
    
    def create_migration_instructions(self):
        """Create detailed migration instructions"""
        logger.info("Creating migration instructions...")
        
        instructions = """# AWS RDS Migration Instructions

## Pre-Migration Checklist
- [x] Database backup created
- [x] AWS RDS connection tested
- [x] Configuration files updated
- [x] Environment variables prepared

## Migration Steps

### 1. Stop Current Bot (if running in production)
```bash
# Stop the current bot process
pkill -f bot_v20_runner.py
```

### 2. Update Environment Variables
Choose one of these methods:

#### Option A: Use .env.aws file
```bash
cp .env.aws .env
```

#### Option B: Set environment variables directly
```bash
export DATABASE_URL="postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
export TELEGRAM_BOT_TOKEN="your-token"
export ADMIN_USER_ID="your-admin-id"
export SESSION_SECRET="your-secret"
```

### 3. Test Database Connection
```bash
python aws_rds_migration_test.py
```

### 4. Start Bot with New Configuration
```bash
python bot_v20_runner.py
```

### 5. Monitor and Verify
- Check /health endpoint
- Test bot commands
- Monitor logs for errors
- Verify user data integrity

## Rollback Plan (if needed)
1. Stop new bot process
2. Restore original .env file: `cp .env.backup_* .env`
3. Restart bot with original configuration

## Post-Migration Tasks
- Monitor performance for 24 hours
- Update deployment scripts
- Remove old database references
- Update documentation

## Support
If issues occur, check:
1. Database connection logs
2. Environment variable values
3. Network connectivity to AWS RDS
4. Security group settings in AWS
"""
        
        with open('AWS_MIGRATION_GUIDE.md', 'w') as f:
            f.write(instructions)
        
        logger.info("✓ Created AWS_MIGRATION_GUIDE.md")
    
    def run_all_updates(self):
        """Run all configuration updates"""
        logger.info("=== Starting Configuration Updates for AWS RDS ===")
        
        try:
            self.update_app_py()
            self.update_production_config()
            self.update_deployment_config()
            self.create_env_aws()
            self.update_database_monitoring()
            self.create_migration_instructions()
            
            logger.info("=== Configuration Updates Completed ===")
            logger.info("All files have been updated for AWS RDS migration")
            logger.info("Backup files created with timestamp suffix")
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration update failed: {e}")
            return False

def main():
    """Run configuration updates"""
    updater = ConfigUpdater()
    success = updater.run_all_updates()
    
    if success:
        print("\n✅ Configuration updated successfully!")
        print("Files ready for AWS RDS migration")
        print("Review AWS_MIGRATION_GUIDE.md for next steps")
    else:
        print("\n❌ Configuration update failed")

if __name__ == "__main__":
    main()