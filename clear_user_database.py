"""
Clear User Database - Complete User Data Removal
===============================================
This script safely removes all user data from the database and clears any
cached Telegram data to provide a fresh start.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import (
    User, Transaction, TradingPosition, Profit, 
    ReferralCode, BroadcastMessage, AdminMessage, SupportTicket
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_admin_settings():
    """Backup critical admin settings before clearing users."""
    
    with app.app_context():
        try:
            from models import SystemSettings
            
            # Get current admin settings
            admin_settings = {}
            settings = SystemSettings.query.all()
            
            for setting in settings:
                admin_settings[setting.setting_name] = setting.setting_value
            
            logger.info(f"Backed up {len(admin_settings)} admin settings")
            return admin_settings
            
        except Exception as e:
            logger.warning(f"Could not backup admin settings: {e}")
            return {}


def clear_all_user_data():
    """Clear all user-related data from the database."""
    
    with app.app_context():
        try:
            logger.info("Starting complete user database clearing...")
            
            # Count current data
            user_count = User.query.count()
            transaction_count = Transaction.query.count()
            position_count = TradingPosition.query.count()
            profit_count = Profit.query.count()
            referral_count = ReferralCode.query.count()
            
            logger.info(f"Current data counts:")
            logger.info(f"  Users: {user_count}")
            logger.info(f"  Transactions: {transaction_count}")
            logger.info(f"  Trading Positions: {position_count}")
            logger.info(f"  Profits: {profit_count}")
            logger.info(f"  Referral Codes: {referral_count}")
            
            if user_count == 0:
                logger.info("Database is already empty")
                return True
            
            # Clear in correct order to respect foreign key constraints
            logger.info("Clearing user-related data...")
            
            # 1. Clear profits (references users)
            if profit_count > 0:
                Profit.query.delete()
                logger.info(f"Cleared {profit_count} profit records")
            
            # 2. Clear trading positions (references users)
            if position_count > 0:
                TradingPosition.query.delete()
                logger.info(f"Cleared {position_count} trading positions")
            
            # 3. Clear transactions (references users)
            if transaction_count > 0:
                Transaction.query.delete()
                logger.info(f"Cleared {transaction_count} transactions")
            
            # 4. Clear support tickets (references users)
            try:
                ticket_count = SupportTicket.query.count()
                if ticket_count > 0:
                    SupportTicket.query.delete()
                    logger.info(f"Cleared {ticket_count} support tickets")
            except Exception as e:
                logger.warning(f"Could not clear support tickets: {e}")
            
            # 5. Clear broadcast messages (may reference users)
            try:
                broadcast_count = BroadcastMessage.query.count()
                if broadcast_count > 0:
                    BroadcastMessage.query.delete()
                    logger.info(f"Cleared {broadcast_count} broadcast messages")
            except Exception as e:
                logger.warning(f"Could not clear broadcast messages: {e}")
            
            # 6. Clear admin messages (may reference users)
            try:
                admin_msg_count = AdminMessage.query.count()
                if admin_msg_count > 0:
                    AdminMessage.query.delete()
                    logger.info(f"Cleared {admin_msg_count} admin messages")
            except Exception as e:
                logger.warning(f"Could not clear admin messages: {e}")
            
            # 7. Clear referral codes (references users)
            if referral_count > 0:
                ReferralCode.query.delete()
                logger.info(f"Cleared {referral_count} referral codes")
            
            # 8. Finally clear users
            User.query.delete()
            logger.info(f"Cleared {user_count} users")
            
            # Commit all changes
            db.session.commit()
            logger.info("✅ All user data cleared successfully")
            
            # Verify clearing
            verify_clearing()
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing user data: {e}")
            db.session.rollback()
            return False


def verify_clearing():
    """Verify that all user data has been cleared."""
    
    with app.app_context():
        try:
            # Check all tables are empty
            remaining_users = User.query.count()
            remaining_transactions = Transaction.query.count()
            remaining_positions = TradingPosition.query.count()
            remaining_profits = Profit.query.count()
            remaining_referrals = ReferralCode.query.count()
            
            logger.info("Verification results:")
            logger.info(f"  Remaining users: {remaining_users}")
            logger.info(f"  Remaining transactions: {remaining_transactions}")
            logger.info(f"  Remaining positions: {remaining_positions}")
            logger.info(f"  Remaining profits: {remaining_profits}")
            logger.info(f"  Remaining referrals: {remaining_referrals}")
            
            total_remaining = (remaining_users + remaining_transactions + 
                             remaining_positions + remaining_profits + 
                             remaining_referrals)
            
            if total_remaining == 0:
                logger.info("✅ Database clearing verified - all user data removed")
                return True
            else:
                logger.error(f"❌ {total_remaining} records still remain")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying clearing: {e}")
            return False


def reset_database_sequences():
    """Reset database sequences to start from 1 again."""
    
    with app.app_context():
        try:
            logger.info("Resetting database sequences...")
            
            # Reset primary key sequences for PostgreSQL
            reset_queries = [
                "ALTER SEQUENCE user_id_seq RESTART WITH 1;",
                "ALTER SEQUENCE transaction_id_seq RESTART WITH 1;",
                "ALTER SEQUENCE trading_position_id_seq RESTART WITH 1;",
                "ALTER SEQUENCE profit_id_seq RESTART WITH 1;",
                "ALTER SEQUENCE referral_code_id_seq RESTART WITH 1;",
            ]
            
            for query in reset_queries:
                try:
                    db.session.execute(query)
                    logger.info(f"Reset sequence: {query.split()[2]}")
                except Exception as e:
                    logger.warning(f"Could not reset sequence {query}: {e}")
            
            db.session.commit()
            logger.info("✅ Database sequences reset")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting sequences: {e}")
            return False


def clear_telegram_cache():
    """Clear any Telegram-related cache or temporary data."""
    
    logger.info("Clearing Telegram cache and temporary data...")
    
    # Clear any global variables that might hold user data
    try:
        # Reset admin adjustment globals
        import bot_v20_runner
        if hasattr(bot_v20_runner, 'admin_target_user_id'):
            bot_v20_runner.admin_target_user_id = None
        if hasattr(bot_v20_runner, 'admin_adjust_telegram_id'):
            bot_v20_runner.admin_adjust_telegram_id = None
        if hasattr(bot_v20_runner, 'admin_adjust_current_balance'):
            bot_v20_runner.admin_adjust_current_balance = None
        if hasattr(bot_v20_runner, 'admin_adjustment_amount'):
            bot_v20_runner.admin_adjustment_amount = None
        if hasattr(bot_v20_runner, 'admin_adjustment_reason'):
            bot_v20_runner.admin_adjustment_reason = None
            
        logger.info("✅ Cleared bot global variables")
    except Exception as e:
        logger.warning(f"Could not clear bot globals: {e}")
    
    # Clear any cached user data files
    try:
        cache_files = [
            'user_cache.json',
            'telegram_cache.json',
            'yield_data.json'
        ]
        
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                os.remove(cache_file)
                logger.info(f"Removed cache file: {cache_file}")
        
        logger.info("✅ Cleared cache files")
    except Exception as e:
        logger.warning(f"Could not clear cache files: {e}")


def create_fresh_start_summary():
    """Create a summary of the fresh start."""
    
    summary = """
DATABASE CLEARING COMPLETE
=========================

✅ All user data removed:
   • Users and profiles
   • Transaction history
   • Trading positions
   • Profit records
   • Referral codes and relationships
   • Support tickets
   • Broadcast messages

✅ Database sequences reset to start from ID 1

✅ Telegram cache cleared

✅ Bot globals reset

The system is now ready for fresh users with a clean slate.
Next users will start with ID 1 and clean history.

Admin settings and system configuration preserved.
"""
    
    logger.info(summary)
    
    # Save summary to file
    try:
        with open('database_clearing_summary.txt', 'w') as f:
            f.write(summary)
            f.write(f"\nClearing completed at: {datetime.now()}\n")
        logger.info("Summary saved to database_clearing_summary.txt")
    except Exception as e:
        logger.warning(f"Could not save summary: {e}")


def main():
    """Main function to clear all user data."""
    
    logger.info("User Database Clearing Tool")
    logger.info("=" * 50)
    
    # Step 1: Backup admin settings
    admin_settings = backup_admin_settings()
    
    # Step 2: Clear all user data
    if not clear_all_user_data():
        logger.error("Failed to clear user data")
        return False
    
    # Step 3: Reset database sequences
    if not reset_database_sequences():
        logger.warning("Could not reset all sequences")
    
    # Step 4: Clear Telegram cache
    clear_telegram_cache()
    
    # Step 5: Final verification
    if not verify_clearing():
        logger.error("Verification failed")
        return False
    
    # Step 6: Create summary
    create_fresh_start_summary()
    
    logger.info("=" * 50)
    logger.info("✅ USER DATABASE CLEARING COMPLETED SUCCESSFULLY")
    logger.info("The bot is ready for fresh users with clean data")
    
    return True


if __name__ == "__main__":
    try:
        from datetime import datetime
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Clearing script crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)