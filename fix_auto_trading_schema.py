#!/usr/bin/env python3
"""
Fix Auto Trading Schema - Add Missing Database Columns
====================================================
This script adds the missing external_signals_enabled column to the auto_trading_settings table
to fix the auto trading settings page connection issue.
"""

import logging
from app import app, db
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_auto_trading_schema():
    """Add missing column to auto_trading_settings table"""
    try:
        with app.app_context():
            # Check if the column already exists by querying the table structure
            try:
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'auto_trading_settings' 
                    AND column_name = 'external_signals_enabled'
                """))
                column_exists = result.fetchone() is not None
            except Exception as e:
                logger.info(f"Could not check column existence, proceeding with addition: {e}")
                column_exists = False
            
            if not column_exists:
                logger.info("Adding missing external_signals_enabled column to auto_trading_settings table")
                
                # Add the missing column with a default value
                db.session.execute(text("""
                    ALTER TABLE auto_trading_settings 
                    ADD COLUMN external_signals_enabled BOOLEAN DEFAULT TRUE
                """))
                db.session.commit()
                
                logger.info("✅ Successfully added external_signals_enabled column")
            else:
                logger.info("external_signals_enabled column already exists")
            
            # Verify the fix by checking if we can query the new column
            try:
                result = db.session.execute(text("SELECT external_signals_enabled FROM auto_trading_settings LIMIT 1"))
                logger.info("✅ Column verification successful - external_signals_enabled is accessible")
            except Exception as verify_error:
                logger.warning(f"Column verification failed: {verify_error}")
            
            # Test loading settings to ensure everything works
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.first()
            if user:
                settings = AutoTradingManager.get_or_create_settings(user.id)
                logger.info(f"✅ Successfully loaded auto trading settings for user {user.telegram_id}")
                logger.info(f"Settings: enabled={settings.is_enabled}, external_signals={settings.external_signals_enabled}")
                return True
            else:
                logger.info("No users found to test settings loading")
                return True
            
    except Exception as e:
        logger.error(f"Error fixing auto trading schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_auto_trading_schema()
    if success:
        print("✅ Auto trading schema fix completed successfully")
        print("🔧 Auto trading settings page should now work properly")
    else:
        print("❌ Failed to fix auto trading schema")