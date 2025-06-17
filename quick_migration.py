#!/usr/bin/env python3
"""
Quick Migration Script - Neon to AWS RDS
"""
import os
import psycopg2
from urllib.parse import urlparse

def migrate_data():
    # Connection strings
    source_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    target_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
    
    # Parse URLs
    source_parsed = urlparse(source_url)
    target_parsed = urlparse(target_url)
    
    print("Connecting to databases...")
    
    # Connect to source
    source_conn = psycopg2.connect(
        host=source_parsed.hostname,
        port=source_parsed.port or 5432,
        user=source_parsed.username,
        password=source_parsed.password,
        database=source_parsed.path.lstrip('/'),
        sslmode='require'
    )
    
    # Connect to target
    target_conn = psycopg2.connect(
        host=target_parsed.hostname,
        port=target_parsed.port or 5432,
        user=target_parsed.username,
        password=target_parsed.password,
        database=target_parsed.path.lstrip('/')
    )
    
    print("✓ Connected to both databases")
    
    # Get table list
    with source_conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cur.fetchall()]
    
    print(f"Found {len(tables)} tables to migrate")
    
    # Migration order
    ordered_tables = ['referral_code', 'user', 'transaction', 'trading_position', 'system_settings']
    remaining_tables = [t for t in tables if t not in ordered_tables]
    migration_tables = ordered_tables + remaining_tables
    
    migrated_count = 0
    
    for table in migration_tables:
        if table not in tables:
            continue
            
        print(f"Migrating {table}...")
        
        try:
            # Get source data
            with source_conn.cursor() as source_cur:
                source_cur.execute(f'SELECT * FROM "{table}"')
                rows = source_cur.fetchall()
                columns = [desc[0] for desc in source_cur.description]
            
            if not rows:
                print(f"  {table}: No data")
                continue
            
            # Clear target and insert
            with target_conn.cursor() as target_cur:
                target_cur.execute(f'DELETE FROM "{table}"')
                
                if rows:
                    cols_str = ', '.join([f'"{col}"' for col in columns])
                    placeholders = ', '.join(['%s'] * len(columns))
                    insert_sql = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'
                    target_cur.executemany(insert_sql, rows)
                
                target_conn.commit()
                print(f"  {table}: {len(rows)} rows migrated")
                migrated_count += 1
                
        except Exception as e:
            print(f"  {table}: Error - {e}")
    
    # Verify
    print("\nVerification:")
    for table in migration_tables[:5]:  # Check first 5 tables
        if table not in tables:
            continue
            
        try:
            with source_conn.cursor() as s_cur, target_conn.cursor() as t_cur:
                s_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                source_count = s_cur.fetchone()[0]
                
                t_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                target_count = t_cur.fetchone()[0]
                
                status = "✓" if source_count == target_count else "✗"
                print(f"{status} {table}: {source_count} -> {target_count}")
        except:
            pass
    
    source_conn.close()
    target_conn.close()
    
    print(f"\n✅ Migration completed: {migrated_count} tables")
    return True

if __name__ == "__main__":
    migrate_data()