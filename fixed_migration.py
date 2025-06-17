#!/usr/bin/env python3
"""
Fixed Migration Script - Handles Foreign Key Dependencies Correctly
"""
import psycopg2
from urllib.parse import urlparse

def migrate_with_proper_order():
    source_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    target_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
    
    source_parsed = urlparse(source_url)
    target_parsed = urlparse(target_url)
    
    print("Connecting to databases...")
    
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
    
    print("✓ Connected to both databases")
    
    # Proper migration order respecting foreign key constraints
    migration_order = [
        'user',              # Base table - no dependencies
        'referral_code',     # Depends on user
        'transaction',       # Depends on user
        'trading_position',  # Depends on user
        'trading_cycle',     # Depends on user
        'support_ticket',    # Depends on user
        'sender_wallet',     # Depends on user
        'referral_reward',   # Depends on user
        'milestone_tracker', # Depends on user
        'profit',           # Depends on user
        'user_metrics',     # Depends on user
        'daily_snapshot',   # Depends on user
        'broadcast_message', # Independent
        'admin_message',    # Independent
        'system_settings'   # Independent
    ]
    
    migrated_count = 0
    
    for table in migration_order:
        print(f"Migrating {table}...")
        
        try:
            # Start fresh transaction for each table
            source_conn.rollback()
            target_conn.rollback()
            
            # Get source data
            with source_conn.cursor() as source_cur:
                source_cur.execute(f'SELECT * FROM "{table}"')
                rows = source_cur.fetchall()
                
                if not rows:
                    print(f"  {table}: No data")
                    continue
                    
                columns = [desc[0] for desc in source_cur.description]
            
            # Insert into target
            with target_conn.cursor() as target_cur:
                # Clear target table first
                target_cur.execute(f'DELETE FROM "{table}" CASCADE')
                
                # Insert data
                cols_str = ', '.join([f'"{col}"' for col in columns])
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'
                
                target_cur.executemany(insert_sql, rows)
                target_conn.commit()
                
                print(f"  {table}: {len(rows)} rows migrated")
                migrated_count += 1
                
        except Exception as e:
            print(f"  {table}: Error - {e}")
            target_conn.rollback()
            # Continue with next table
    
    # Final verification
    print("\nVerification:")
    verification_success = True
    
    for table in migration_order[:5]:  # Check key tables
        try:
            with source_conn.cursor() as s_cur, target_conn.cursor() as t_cur:
                s_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                source_count = s_cur.fetchone()[0]
                
                t_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                target_count = t_cur.fetchone()[0]
                
                if source_count == target_count:
                    print(f"✓ {table}: {source_count} rows")
                else:
                    print(f"✗ {table}: {source_count} -> {target_count}")
                    verification_success = False
        except Exception as e:
            print(f"✗ {table}: Verification failed - {e}")
            verification_success = False
    
    source_conn.close()
    target_conn.close()
    
    if verification_success:
        print(f"\n✅ Migration successful: {migrated_count} tables migrated")
        return True
    else:
        print(f"\n⚠️ Migration completed with issues: {migrated_count} tables migrated")
        return False

def create_aws_config():
    """Create AWS configuration files"""
    import os
    
    aws_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
    
    env_content = f"""DATABASE_URL={aws_url}
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', '')}
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'change-this-secret')}
MIN_DEPOSIT=0.1
BOT_ENVIRONMENT=aws
"""
    
    with open('.env.aws', 'w') as f:
        f.write(env_content)
    
    print("✓ Created .env.aws configuration file")

if __name__ == "__main__":
    success = migrate_with_proper_order()
    if success:
        create_aws_config()
        print("\nMigration complete! Next steps:")
        print("1. Copy AWS config: cp .env.aws .env")
        print("2. Restart your bot")
        print("3. Test functionality")
    else:
        print("\nMigration had issues. Check the output above.")