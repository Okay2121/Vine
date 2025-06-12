"""
Clean Database Script - Remove all users and related data
"""
from dotenv import load_dotenv
load_dotenv()

from app import app, db
from sqlalchemy import text

def clean_database():
    """Clean all user data from database"""
    print("Database Cleanup Starting...")
    
    with app.app_context():
        try:
            # Get initial counts
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
                user_count = result.scalar()
                print(f"Found {user_count} users to delete")
                
                if user_count == 0:
                    print("Database is already clean")
                    return
            
            # Delete in correct order (child tables first)
            deletion_order = [
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
            
            total_deleted = 0
            
            for table in deletion_order:
                with db.engine.connect() as conn:
                    try:
                        # Count records
                        count_result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        count = count_result.scalar()
                        
                        if count > 0:
                            # Delete all records
                            conn.execute(text(f'DELETE FROM "{table}"'))
                            conn.commit()
                            print(f"Deleted {count} records from {table}")
                            total_deleted += count
                        else:
                            print(f"Table {table} already empty")
                            
                    except Exception as e:
                        print(f"Could not process {table}: {e}")
            
            print(f"\nCleanup complete! Deleted {total_deleted} total records")
            
            # Verify cleanup
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
                remaining = result.scalar()
                print(f"Remaining users: {remaining}")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    clean_database()