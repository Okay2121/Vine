#!/usr/bin/env python3
"""
Final Migration Script - Disables FK constraints during migration
"""
import psycopg2
from urllib.parse import urlparse

def run_final_migration():
    source_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    target_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
    
    source_parsed = urlparse(source_url)
    target_parsed = urlparse(target_url)
    
    print("Starting final migration...")
    
    # Connect to databases
    source_conn = psycopg2.connect(
        host=source_parsed.hostname,
        port=source_parsed.port or 5432,
        user=source_parsed.username,
        password=source_parsed.password,
        database=source_parsed.path.lstrip('/'),
        sslmode='require'
    )
    
    target_conn = psycopg2.connect(
        host=target_parsed.hostname,
        port=target_parsed.port or 5432,
        user=target_parsed.username,
        password=target_parsed.password,
        database=target_parsed.path.lstrip('/')
    )
    
    print("Connected to both databases")
    
    try:
        # Get all tables with data
        with source_conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            all_tables = [row[0] for row in cur.fetchall()]
        
        # Check which tables have data
        tables_with_data = []
        for table in all_tables:
            with source_conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cur.fetchone()[0]
                if count > 0:
                    tables_with_data.append((table, count))
        
        print(f"Found {len(tables_with_data)} tables with data:")
        for table, count in tables_with_data:
            print(f"  {table}: {count} rows")
        
        # Disable foreign key checks on target
        with target_conn.cursor() as cur:
            cur.execute("SET session_replication_role = replica;")
            target_conn.commit()
            print("Disabled foreign key constraints")
        
        # Migrate data
        migrated = 0
        for table, expected_count in tables_with_data:
            print(f"Migrating {table}...")
            
            try:
                # Get source data
                with source_conn.cursor() as source_cur:
                    source_cur.execute(f'SELECT * FROM "{table}"')
                    rows = source_cur.fetchall()
                    columns = [desc[0] for desc in source_cur.description]
                
                # Clear and insert into target
                with target_conn.cursor() as target_cur:
                    target_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                    
                    if rows:
                        cols_str = ', '.join([f'"{col}"' for col in columns])
                        placeholders = ', '.join(['%s'] * len(columns))
                        insert_sql = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'
                        target_cur.executemany(insert_sql, rows)
                    
                    target_conn.commit()
                    print(f"  {table}: {len(rows)} rows migrated")
                    migrated += 1
                    
            except Exception as e:
                print(f"  {table}: Failed - {e}")
                target_conn.rollback()
        
        # Re-enable foreign key checks
        with target_conn.cursor() as cur:
            cur.execute("SET session_replication_role = DEFAULT;")
            target_conn.commit()
            print("Re-enabled foreign key constraints")
        
        # Verify migration
        print("\nVerification:")
        all_good = True
        for table, expected_count in tables_with_data:
            try:
                with target_conn.cursor() as cur:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    actual_count = cur.fetchone()[0]
                    
                    if actual_count == expected_count:
                        print(f"✓ {table}: {actual_count} rows")
                    else:
                        print(f"✗ {table}: Expected {expected_count}, got {actual_count}")
                        all_good = False
            except Exception as e:
                print(f"✗ {table}: Verification failed - {e}")
                all_good = False
        
        if all_good:
            print(f"\n✅ Migration successful! {migrated} tables migrated")
            return True
        else:
            print(f"\n⚠️ Migration completed with issues")
            return False
            
    finally:
        source_conn.close()
        target_conn.close()

def update_configuration():
    """Update app configuration for AWS RDS"""
    import os
    from datetime import datetime
    
    aws_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
    
    # Create .env.aws
    env_content = f"""DATABASE_URL={aws_url}
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', '')}
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'change-this-secret')}
MIN_DEPOSIT=0.1
BOT_ENVIRONMENT=aws
"""
    
    with open('.env.aws', 'w') as f:
        f.write(env_content)
    
    print("Created .env.aws configuration")
    
    # Update app.py fallback URL
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Backup original
        backup_name = f'app.py.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        with open(backup_name, 'w') as f:
            f.write(content)
        
        # Replace the fallback URL
        old_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        new_content = content.replace(old_url, aws_url)
        
        with open('app.py', 'w') as f:
            f.write(new_content)
        
        print(f"Updated app.py (backup: {backup_name})")
        
    except Exception as e:
        print(f"Could not update app.py: {e}")

if __name__ == "__main__":
    success = run_final_migration()
    
    if success:
        update_configuration()
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Stop your current bot")
        print("2. Switch to AWS RDS: cp .env.aws .env")
        print("3. Restart your bot")
        print("4. Test all functionality")
    else:
        print("\n❌ Migration had issues - check output above")