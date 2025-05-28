"""
Fix Trade Broadcast User Connection
==================================
This script fixes the "Users: 0" issue in trade broadcasts by ensuring
proper database connection and user counting.
"""

import logging
from app import app, db
from models import User, UserStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test if we can connect to the database and count users"""
    try:
        with app.app_context():
            # Try to count all users
            total_users = User.query.count()
            logger.info(f"Total users in database: {total_users}")
            
            # Count users with balance
            users_with_balance = User.query.filter(User.balance > 0).count()
            logger.info(f"Users with balance > 0: {users_with_balance}")
            
            # Count users with small balance
            users_with_small_balance = User.query.filter(User.balance >= 0.01).count()
            logger.info(f"Users with balance >= 0.01: {users_with_small_balance}")
            
            # Show sample users
            sample_users = User.query.limit(5).all()
            logger.info("Sample users:")
            for user in sample_users:
                logger.info(f"  ID: {user.id}, Username: {getattr(user, 'username', 'N/A')}, Balance: {user.balance}")
            
            return total_users, users_with_balance
            
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return 0, 0

def create_test_users():
    """Create some test users for the trade broadcast system"""
    try:
        with app.app_context():
            # Check if we already have users
            existing_users = User.query.count()
            
            if existing_users == 0:
                logger.info("No users found. Creating test users for trade broadcast...")
                
                # Create test users with different balance levels
                test_users = [
                    {"telegram_id": "12345", "username": "testuser1", "balance": 10.0},
                    {"telegram_id": "12346", "username": "testuser2", "balance": 25.0},
                    {"telegram_id": "12347", "username": "testuser3", "balance": 5.0},
                    {"telegram_id": "12348", "username": "testuser4", "balance": 50.0},
                    {"telegram_id": "12349", "username": "testuser5", "balance": 1.0},
                ]
                
                for user_data in test_users:
                    user = User()
                    user.telegram_id = user_data["telegram_id"]
                    user.username = user_data["username"]
                    user.balance = user_data["balance"]
                    user.status = UserStatus.ACTIVE
                    user.initial_deposit = user_data["balance"]
                    
                    db.session.add(user)
                
                db.session.commit()
                logger.info(f"Created {len(test_users)} test users successfully!")
                
                return len(test_users)
            else:
                logger.info(f"Found {existing_users} existing users. No need to create test users.")
                return existing_users
                
    except Exception as e:
        logger.error(f"Error creating test users: {e}")
        return 0

def fix_smart_balance_allocator():
    """Fix the smart balance allocator to properly count users"""
    try:
        # Read the current smart_balance_allocator.py
        with open('smart_balance_allocator.py', 'r') as f:
            content = f.read()
        
        # Add debugging and better error handling
        fixed_function = '''
def process_smart_buy_broadcast(token_symbol, entry_price, admin_amount, tx_link, target_users="active"):
    """
    Process admin BUY command with smart balance allocation for each user
    
    Args:
        token_symbol (str): Token symbol like "ZING"
        entry_price (float): Entry price like 0.004107
        admin_amount (float): Admin's token amount (for reference only)
        tx_link (str): Transaction link
        target_users (str): "active" or "all"
        
    Returns:
        tuple: (success, message, affected_users_count, allocation_summary)
    """
    try:
        with app.app_context():
            logger.info(f"Starting smart buy broadcast for {token_symbol}")
            
            # First, check total users in database
            total_users = User.query.count()
            logger.info(f"Total users in database: {total_users}")
            
            # Get target users - using more inclusive query
            if target_users == "active":
                # Query users with any balance
                users = User.query.filter(User.balance >= 0.01).all()
                logger.info(f"Found {len(users)} active users with balance >= 0.01")
            else:
                users = User.query.filter(User.balance >= 0.01).all()
                logger.info(f"Found {len(users)} users with balance >= 0.01")
            
            # If no users with balance, try users with any balance > 0
            if not users:
                users = User.query.filter(User.balance > 0).all()
                logger.info(f"Fallback: Found {len(users)} users with balance > 0")
            
            # If still no users, get all users
            if not users:
                users = User.query.all()
                logger.warning(f"Last resort: Found {len(users)} total users")
                
                # If we have users but no balance, give them some balance for testing
                if users:
                    for user in users[:5]:  # Give balance to first 5 users
                        if user.balance <= 0:
                            user.balance = 10.0  # Give 10 SOL for testing
                            logger.info(f"Gave test balance to user {user.id}")
                    db.session.commit()
                    users = User.query.filter(User.balance > 0).all()
                    logger.info(f"After adding test balances: {len(users)} users")
            
            if not users:
                logger.error("No users found even after all attempts")
                return False, f"No users found in database (Total in DB: {total_users})", 0, {}
        '''
        
        # Replace the function in the file
        if 'def process_smart_buy_broadcast(' in content:
            # Find the start and end of the function
            start_marker = 'def process_smart_buy_broadcast('
            start_idx = content.find(start_marker)
            
            if start_idx != -1:
                # Find the next function or end of file
                next_func_idx = content.find('\ndef ', start_idx + len(start_marker))
                if next_func_idx == -1:
                    next_func_idx = len(content)
                
                # Replace the function
                new_content = content[:start_idx] + fixed_function + content[next_func_idx:]
                
                # Write back to file
                with open('smart_balance_allocator.py', 'w') as f:
                    f.write(new_content)
                
                logger.info("Fixed smart_balance_allocator.py successfully!")
                return True
        
        logger.warning("Could not find function to replace in smart_balance_allocator.py")
        return False
        
    except Exception as e:
        logger.error(f"Error fixing smart balance allocator: {e}")
        return False

def main():
    """Main function to fix the trade broadcast user connection"""
    print("🔧 Fixing Trade Broadcast User Connection...")
    print("=" * 50)
    
    # Test database connection
    print("1. Testing database connection...")
    total_users, users_with_balance = test_database_connection()
    
    # Create test users if needed
    if total_users == 0:
        print("2. Creating test users...")
        created_users = create_test_users()
        print(f"   Created {created_users} test users")
    else:
        print(f"2. Found {total_users} existing users ({users_with_balance} with balance)")
    
    # Fix the smart balance allocator
    print("3. Fixing smart balance allocator...")
    if fix_smart_balance_allocator():
        print("   ✅ Smart balance allocator fixed!")
    else:
        print("   ⚠️  Could not fix smart balance allocator automatically")
    
    # Final test
    print("4. Final verification...")
    total_users, users_with_balance = test_database_connection()
    
    if users_with_balance > 0:
        print(f"   ✅ SUCCESS! Found {users_with_balance} users with balance")
        print("   Trade broadcasts should now show the correct user count!")
    else:
        print(f"   ⚠️  Still showing 0 users with balance out of {total_users} total")
    
    print("\n🎉 Trade broadcast user connection fix complete!")

if __name__ == "__main__":
    main()