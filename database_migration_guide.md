# Database Migration Guide - Step by Step

Your Neon database is hitting quota limits. Here are the exact steps to migrate to a reliable production database.

## Option 1: Railway PostgreSQL (Recommended for Quick Fix)
**Cost: $5/month | Setup Time: 5 minutes**

### Steps:
1. Go to https://railway.app
2. Sign up/login with GitHub
3. Click "New Project" → "Provision PostgreSQL"
4. Once created, click on the PostgreSQL service
5. Go to "Connect" tab
6. Copy the "Postgres Connection URL"

### Example connection string:
```
postgresql://postgres:password@monorail.proxy.rlwy.net:12345/railway
```

## Option 2: Digital Ocean Managed Database
**Cost: $15/month | High Reliability**

### Steps:
1. Go to https://cloud.digitalocean.com
2. Create account and verify
3. Click "Create" → "Databases"
4. Choose PostgreSQL
5. Select $15/month plan (1GB RAM)
6. Choose datacenter closest to your users
7. Database name: `solana-trading-bot`
8. Wait 2-3 minutes for creation
9. Copy connection details from dashboard

## Option 3: AWS RDS PostgreSQL (Best for Production)
**Cost: $20-50/month | Enterprise Grade**

### Steps:
1. Go to AWS RDS Console
2. Click "Create database"
3. Choose "PostgreSQL"
4. Template: "Production" or "Dev/Test"
5. Settings:
   - DB instance identifier: `solana-trading-bot`
   - Master username: `postgres`
   - Master password: [create strong password]
   - DB name: `solana_trading`
6. Instance configuration: `db.t3.micro` (free tier) or `db.t3.small`
7. Storage: 20 GB (can auto-scale)
8. VPC security group: Create new, allow port 5432
9. Create database (takes 5-10 minutes)
10. Get endpoint from RDS dashboard

### Connection string format:
```
postgresql://postgres:password@database-endpoint.region.rds.amazonaws.com:5432/solana_trading
```

## Option 4: Supabase (Free Tier Available)
**Cost: Free tier, then $25/month**

### Steps:
1. Go to https://supabase.com
2. Sign up with GitHub
3. Click "New project"
4. Choose organization
5. Project name: `solana-trading-bot`
6. Database password: [create strong password]
7. Region: Choose closest to your users
8. Wait for setup (2-3 minutes)
9. Go to Settings → Database
10. Copy "Connection string" under "Connection parameters"

## After Getting Your New Database URL

### Step 1: Test Connection
```bash
# Replace YOUR_NEW_DATABASE_URL with your actual URL
python -c "
import psycopg2
try:
    conn = psycopg2.connect('YOUR_NEW_DATABASE_URL')
    print('✓ Connection successful!')
    conn.close()
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

### Step 2: Update Your Environment
Create or update your `.env` file:
```
DATABASE_URL=YOUR_NEW_DATABASE_URL
SESSION_SECRET=your-secure-random-string
```

### Step 3: Update Production Environment
For AWS deployment:
```bash
# Set as environment variable
export DATABASE_URL="YOUR_NEW_DATABASE_URL"

# Or use AWS Systems Manager
aws ssm put-parameter \
  --name "/solana-bot/database-url" \
  --value "YOUR_NEW_DATABASE_URL" \
  --type "SecureString"
```

For Railway deployment:
```bash
railway variables:set DATABASE_URL="YOUR_NEW_DATABASE_URL"
```

### Step 4: Test Your Application
1. Restart your application
2. Check health endpoint: `curl your-app-url/health`
3. Verify deposit monitoring is working in logs

## Migration Script (Optional)

If you want to migrate existing data from your current Neon database, run this script after setting up the new database:

```python
import os
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your current Neon database (source)
source_url = "postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"

# Your new database (target)
target_url = "YOUR_NEW_DATABASE_URL"  # Replace with your new database URL

def migrate_data():
    try:
        source_engine = create_engine(source_url)
        target_engine = create_engine(target_url)
        
        # Get table names
        with source_engine.connect() as source_conn:
            tables_result = source_conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """))
            tables = [row[0] for row in tables_result]
            
            logger.info(f"Found tables to migrate: {tables}")
            
            for table in tables:
                try:
                    # Get data from source
                    result = source_conn.execute(text(f"SELECT * FROM {table}"))
                    rows = result.fetchall()
                    columns = result.keys()
                    
                    if rows:
                        # Insert into target
                        with target_engine.connect() as target_conn:
                            for row in rows:
                                placeholders = ', '.join([f":{col}" for col in columns])
                                query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                                row_dict = dict(zip(columns, row))
                                target_conn.execute(text(query), row_dict)
                            target_conn.commit()
                        
                        logger.info(f"✓ Migrated {len(rows)} rows from {table}")
                    else:
                        logger.info(f"✓ Table {table} is empty")
                        
                except Exception as e:
                    logger.error(f"✗ Failed to migrate {table}: {e}")
        
        logger.info("✓ Migration completed!")
        
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")

if __name__ == "__main__":
    migrate_data()
```

## Recommended Choice

For immediate relief: **Railway** ($5/month, 5-minute setup)
For production: **AWS RDS** ($20+/month, enterprise reliability)

Your deposit detection system and bot will work normally once the database connectivity is restored.