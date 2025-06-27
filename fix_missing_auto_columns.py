"""
Fix Missing Auto Trading Columns
===============================
This script adds the missing columns to the AutoTradingSettings table
"""
import logging
from app import app, db
from sqlalchemy import text

def add_missing_columns():
    """Add missing columns to AutoTradingSettings table"""
    try:
        with app.app_context():
            print("Adding missing columns to auto_trading_settings table...")
            
            # List of missing columns to add
            missing_columns = [
                ("position_size_auto", "BOOLEAN DEFAULT TRUE"),
                ("stop_loss_auto", "BOOLEAN DEFAULT TRUE"),
                ("take_profit_auto", "BOOLEAN DEFAULT TRUE"), 
                ("daily_trades_auto", "BOOLEAN DEFAULT TRUE"),
                ("max_positions_auto", "BOOLEAN DEFAULT TRUE")
            ]
            
            for column_name, column_definition in missing_columns:
                try:
                    # Add the column
                    sql = f"ALTER TABLE auto_trading_settings ADD COLUMN {column_name} {column_definition};"
                    print(f"Adding column: {column_name}")
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"✅ Added {column_name}")
                    
                except Exception as col_error:
                    if "already exists" in str(col_error).lower():
                        print(f"⚠️ Column {column_name} already exists")
                    else:
                        print(f"❌ Error adding {column_name}: {col_error}")
                        db.session.rollback()
            
            print("\n✅ All missing columns have been processed")
            return True
            
    except Exception as e:
        print(f"❌ Error adding missing columns: {e}")
        db.session.rollback()
        return False


def test_auto_trading_query():
    """Test querying AutoTradingSettings after adding columns"""
    try:
        with app.app_context():
            from models import User, AutoTradingSettings
            
            # Try to query the first user's settings
            user = User.query.first()
            if not user:
                print("No users found to test with")
                return True
            
            print(f"Testing query for user {user.id}...")
            
            # This should work now with all columns present
            settings = AutoTradingSettings.query.filter_by(user_id=user.id).first()
            
            if settings:
                print(f"✅ Successfully queried settings for user {user.id}")
                print(f"   - Position size auto: {settings.position_size_auto}")
                print(f"   - Max simultaneous positions: {settings.max_simultaneous_positions}")
            else:
                print(f"No settings found for user {user.id} (this is normal)")
            
            return True
            
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        return False


def main():
    """Main function to fix missing auto trading columns"""
    print("=" * 60)
    print("Auto Trading Missing Columns Fix")
    print("=" * 60)
    
    # Step 1: Add missing columns
    print("\n1. Adding missing columns...")
    add_success = add_missing_columns()
    
    if not add_success:
        print("\n❌ Failed to add missing columns")
        return False
    
    # Step 2: Test the fix
    print("\n2. Testing the fix...")
    test_success = test_auto_trading_query()
    
    if test_success:
        print("\n✅ Auto Trading columns fix completed successfully!")
        print("The Auto Trading page should now work properly.")
    else:
        print("\n❌ Column fix verification failed")
        return False
    
    return True


if __name__ == "__main__":
    main()