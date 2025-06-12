"""
Auto Database User Cleanup Script
Automatically removes all users and related data from the database
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the app and database
from app import app, db
from sqlalchemy import text

def delete_all_users():
    """Delete all users and related data automatically"""
    print("Database User Cleanup Tool")
    print("=" * 40)
    
    with app.app_context():
        try:
            # Scan database structure
            with db.engine.connect() as conn:
                # Get all table names
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """))
                tables = [row[0] for row in result.fetchall()]
                
                print(f"Found {len(tables)} tables:")
                for table in tables:
                    print(f"  - {table}")
                
                # Count current users
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
                    user_count = result.scalar()
                    print(f"Current user count: {user_count}")
                except Exception as e:
                    print(f"Note: Could not count users: {e}")
                    user_count = 0
                
                if user_count == 0:
                    print("No users found to delete.")
                    return True
                
                print(f"\nStarting automatic deletion of all {user_count} users and related data...")
                
                # Delete from related tables first (to avoid foreign key constraints)
                tables_to_clean = [
                    'trading_position',
                    'transaction', 
                    'support_ticket',
                    'referral_reward',
                    'referral_code',
                    'profit',
                    'broadcast_message',
                    'admin_message',
                    'user'
                ]
                
                deleted_counts = {}
                
                # Start transaction
                trans = conn.begin()
                
                try:
                    for table in tables_to_clean:
                        try:
                            # Check if table exists and count records
                            count_result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                            count = count_result.scalar()
                            
                            if count > 0:
                                # Delete all records from table
                                conn.execute(text(f'DELETE FROM "{table}"'))
                                deleted_counts[table] = count
                                print(f"✓ Deleted {count} records from {table}")
                            else:
                                print(f"✓ Table {table} is already empty")
                                
                        except Exception as e:
                            print(f"Note: Could not process table '{table}': {e}")
                    
                    # Commit all deletions
                    trans.commit()
                    
                    print(f"\n✅ Successfully deleted all user data:")
                    total_deleted = 0
                    for table, count in deleted_counts.items():
                        print(f"  - {table}: {count} records")
                        total_deleted += count
                    
                    print(f"\nTotal records deleted: {total_deleted}")
                    print("Database has been cleaned successfully!")
                    
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    raise e
            
        except Exception as e:
            print(f"ERROR: Failed to delete users: {e}")
            return False

if __name__ == "__main__":
    success = delete_all_users()
    if success:
        print("\n🎉 All users have been successfully removed from the database.")
    else:
        print("\n❌ Failed to delete all users. Check the errors above.")