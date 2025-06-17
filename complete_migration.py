#!/usr/bin/env python3
"""
Complete Migration Script - Final attempt with corrected connection handling
"""
import psycopg2
import os

def complete_migration():
    print("Starting complete migration to AWS RDS...")
    
    # Source connection (Neon)
    source_conn = psycopg2.connect(
        host='ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech',
        port=5432,
        user='neondb_owner',
        password='npg_9Hdj1LfbemJW',
        database='neondb',
        sslmode='require'
    )
    
    # Target connection (AWS RDS)  
    target_conn = psycopg2.connect(
        host='database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com',
        port=5432,
        user='postgres',
        password='Checker97$',
        database='Vibe'
    )
    
    print("Connected to both databases")
    
    # Migration order to respect foreign key constraints
    migration_order = [
        'user',
        'referral_code', 
        'transaction',
        'trading_position',
        'trading_cycle',
        'support_ticket',
        'sender_wallet',
        'referral_reward',
        'milestone_tracker',
        'profit',
        'user_metrics',
        'daily_snapshot',
        'broadcast_message',
        'admin_message',
        'system_settings'
    ]
    
    try:
        # Disable foreign key checks
        with target_conn.cursor() as cur:
            cur.execute("SET session_replication_role = replica;")
            target_conn.commit()
        print("Disabled foreign key constraints")
        
        migrated_tables = []
        
        for table in migration_order:
            print(f"Migrating {table}...")
            
            try:
                # Check if table has data in source
                with source_conn.cursor() as source_cur:
                    source_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = source_cur.fetchone()[0]
                    
                    if count == 0:
                        print(f"  {table}: No data to migrate")
                        continue
                    
                    # Get all data
                    source_cur.execute(f'SELECT * FROM "{table}"')
                    rows = source_cur.fetchall()
                    columns = [desc[0] for desc in source_cur.description]
                
                # Insert into target
                with target_conn.cursor() as target_cur:
                    # Clear target table
                    target_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                    
                    if rows:
                        # Build insert statement
                        cols_str = ', '.join([f'"{col}"' for col in columns])
                        placeholders = ', '.join(['%s'] * len(columns))
                        insert_sql = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'
                        
                        # Insert all rows
                        target_cur.executemany(insert_sql, rows)
                    
                    target_conn.commit()
                    print(f"  {table}: {len(rows)} rows migrated")
                    migrated_tables.append(table)
                    
            except Exception as e:
                print(f"  {table}: Migration failed - {e}")
                target_conn.rollback()
        
        # Re-enable foreign key checks
        with target_conn.cursor() as cur:
            cur.execute("SET session_replication_role = DEFAULT;")
            target_conn.commit()
        print("Re-enabled foreign key constraints")
        
        # Final verification
        print("\nMigration verification:")
        all_verified = True
        
        for table in migrated_tables:
            try:
                with source_conn.cursor() as s_cur, target_conn.cursor() as t_cur:
                    s_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    source_count = s_cur.fetchone()[0]
                    
                    t_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    target_count = t_cur.fetchone()[0]
                    
                    if source_count == target_count:
                        print(f"✓ {table}: {target_count} rows")
                    else:
                        print(f"✗ {table}: Source {source_count}, Target {target_count}")
                        all_verified = False
            except Exception as e:
                print(f"✗ {table}: Verification failed - {e}")
                all_verified = False
        
        return all_verified, len(migrated_tables)
        
    finally:
        source_conn.close()
        target_conn.close()

def update_bot_configuration():
    """Update bot configuration to use AWS RDS"""
    print("Updating bot configuration...")
    
    # Create .env.aws file
    aws_database_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
    
    env_content = f"""DATABASE_URL={aws_database_url}
TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '')}
ADMIN_USER_ID={os.environ.get('ADMIN_USER_ID', '')}
SESSION_SECRET={os.environ.get('SESSION_SECRET', 'change-this-secret')}
MIN_DEPOSIT=0.1
BOT_ENVIRONMENT=aws
"""
    
    with open('.env.aws', 'w') as f:
        f.write(env_content)
    
    print("Created .env.aws configuration file")
    
    # Update app.py fallback database URL
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Create backup
        import datetime
        backup_name = f'app.py.backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        with open(backup_name, 'w') as f:
            f.write(content)
        
        # Replace the fallback URL in app.py
        old_neon_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        new_content = content.replace(old_neon_url, aws_database_url)
        
        with open('app.py', 'w') as f:
            f.write(new_content)
        
        print(f"Updated app.py (backup saved as {backup_name})")
        
    except Exception as e:
        print(f"Could not update app.py: {e}")

if __name__ == "__main__":
    try:
        success, table_count = complete_migration()
        
        if success:
            update_bot_configuration()
            print(f"\n✅ Migration completed successfully!")
            print(f"Migrated {table_count} tables to AWS RDS")
            print("\nNext steps:")
            print("1. Stop your current bot")
            print("2. Switch to AWS RDS: cp .env.aws .env")
            print("3. Restart your bot")
            print("4. Test all bot functionality")
        else:
            print(f"\n⚠️ Migration completed with issues")
            print(f"Migrated {table_count} tables but verification failed")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")