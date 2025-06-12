"""
Database User Cleanup Script
Removes all users and related data from the database
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the app and database
from app import app, db
from sqlalchemy import text

def scan_database_tables():
    """Scan and display all tables in the database"""
    print("Scanning database structure...")
    try:
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
            
            return tables
    except Exception as e:
        print(f"ERROR: Failed to scan database: {e}")
        return []

def count_users():
    """Count users in the database"""
    try:
        with db.engine.connect() as conn:
            # Try to count users from the User table
            result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
            count = result.scalar()
            print(f"Current user count: {count}")
            return count
    except Exception as e:
        print(f"Note: Could not count users - table might not exist or be named differently: {e}")
        return 0

def delete_all_users():
    """Delete all users and related data"""
    print("\nStarting user deletion process...")
    
    try:
        with db.engine.connect() as conn:
            # Get user count before deletion
            user_count = count_users()
            
            if user_count == 0:
                print("No users found to delete.")
                return True
            
            # Delete from related tables first (to avoid foreign key constraints)
            tables_to_clean = [
                'trading_position',
                'transaction', 
                'withdrawal_request',
                'support_ticket',
                'user_referral',
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
                            print(f"Deleted {count} records from {table}")
                        else:
                            print(f"Table {table} is already empty")
                            
                    except Exception as e:
                        print(f"Note: Could not process table '{table}': {e}")
                
                # Commit all deletions
                trans.commit()
                
                print(f"\n✅ Successfully deleted all user data:")
                for table, count in deleted_counts.items():
                    print(f"  - {table}: {count} records")
                
                return True
                
            except Exception as e:
                trans.rollback()
                raise e
        
    except Exception as e:
        print(f"ERROR: Failed to delete users: {e}")
        return False

def main():
    """Main function to scan and delete users"""
    print("Database User Cleanup Tool")
    print("=" * 40)
    
    with app.app_context():
        try:
            # Scan database structure
            tables = scan_database_tables()
            
            # Count current users
            count_users()
            
            # Confirm deletion
            print(f"\n⚠️  WARNING: This will delete ALL users and related data!")
            confirm = input("Type 'DELETE ALL USERS' to confirm: ")
            
            if confirm == "DELETE ALL USERS":
                success = delete_all_users()
                if success:
                    print(f"\n✅ All users have been successfully removed from the database.")
                else:
                    print(f"\n❌ Failed to delete all users. Check the errors above.")
            else:
                print("Operation cancelled.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()