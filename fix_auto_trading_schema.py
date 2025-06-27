"""
Fix Auto Trading Settings Database Schema
========================================
This script checks and fixes column name mismatches in the AutoTradingSettings table
"""
import logging
from app import app, db
from models import AutoTradingSettings
from sqlalchemy import text, inspect

def check_auto_trading_schema():
    """Check the current schema of AutoTradingSettings table"""
    try:
        with app.app_context():
            # Get the table inspector
            inspector = inspect(db.engine)
            
            # Get column information for auto_trading_settings table
            columns = inspector.get_columns('auto_trading_settings')
            
            print("Current AutoTradingSettings table columns:")
            for column in columns:
                print(f"- {column['name']}: {column['type']}")
            
            # Check for problematic columns
            column_names = [col['name'] for col in columns]
            
            # Check for the specific column causing issues
            if 'simultaneous_positions' in column_names and 'max_simultaneous_positions' not in column_names:
                print("\n❌ Found issue: Column 'simultaneous_positions' should be 'max_simultaneous_positions'")
                return False
            elif 'max_simultaneous_positions' in column_names:
                print("\n✅ Column naming is correct")
                return True
            else:
                print("\n⚠️ Neither column found - table may need creation")
                return False
                
    except Exception as e:
        print(f"Error checking schema: {e}")
        return False


def fix_column_naming():
    """Fix column naming issues in AutoTradingSettings table"""
    try:
        with app.app_context():
            # Check if we need to rename the column
            inspector = inspect(db.engine)
            columns = inspector.get_columns('auto_trading_settings')
            column_names = [col['name'] for col in columns]
            
            if 'simultaneous_positions' in column_names and 'max_simultaneous_positions' not in column_names:
                print("Renaming 'simultaneous_positions' to 'max_simultaneous_positions'...")
                
                # Rename the column
                db.session.execute(text("""
                    ALTER TABLE auto_trading_settings 
                    RENAME COLUMN simultaneous_positions TO max_simultaneous_positions;
                """))
                
                db.session.commit()
                print("✅ Column renamed successfully")
                return True
            else:
                print("No column renaming needed")
                return True
                
    except Exception as e:
        print(f"Error fixing column naming: {e}")
        db.session.rollback()
        return False


def recreate_auto_trading_table():
    """Recreate the AutoTradingSettings table with correct schema"""
    try:
        with app.app_context():
            print("Recreating AutoTradingSettings table...")
            
            # Drop and recreate the table
            db.session.execute(text("DROP TABLE IF EXISTS auto_trading_settings CASCADE;"))
            db.session.commit()
            
            # Create the table with correct schema
            db.create_all()
            db.session.commit()
            
            print("✅ AutoTradingSettings table recreated successfully")
            return True
            
    except Exception as e:
        print(f"Error recreating table: {e}")
        db.session.rollback()
        return False


def test_auto_trading_query():
    """Test querying AutoTradingSettings to verify the fix"""
    try:
        with app.app_context():
            from models import User
            
            # Try to query the first user's settings
            user = User.query.first()
            if not user:
                print("No users found to test with")
                return True
            
            print(f"Testing query for user {user.id}...")
            
            # This should work without the column error
            settings = AutoTradingSettings.query.filter_by(user_id=user.id).first()
            
            if settings:
                print(f"✅ Successfully queried settings for user {user.id}")
                print(f"   - Max simultaneous positions: {settings.max_simultaneous_positions}")
            else:
                print(f"No settings found for user {user.id} (this is normal)")
            
            return True
            
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        return False


def main():
    """Main function to fix auto trading schema issues"""
    print("=" * 60)
    print("Auto Trading Settings Schema Fix")
    print("=" * 60)
    
    # Step 1: Check current schema
    print("\n1. Checking current schema...")
    schema_ok = check_auto_trading_schema()
    
    if not schema_ok:
        # Step 2: Try to fix column naming
        print("\n2. Attempting to fix column naming...")
        fix_success = fix_column_naming()
        
        if not fix_success:
            # Step 3: Recreate table if fixing failed
            print("\n3. Recreating table with correct schema...")
            recreate_success = recreate_auto_trading_table()
            
            if not recreate_success:
                print("\n❌ Failed to fix schema issues")
                return False
    
    # Step 4: Test the fix
    print("\n4. Testing the fix...")
    test_success = test_auto_trading_query()
    
    if test_success:
        print("\n✅ Auto Trading Settings schema fix completed successfully!")
        print("The Auto Trading page should now work properly.")
    else:
        print("\n❌ Schema fix verification failed")
        return False
    
    return True


if __name__ == "__main__":
    main()