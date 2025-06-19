#!/usr/bin/env python3
"""
Clear Users Database Script
Removes all user data from the database and resets Telegram bot interactions
"""

import sys
import os
sys.path.append('.')

from app import app, db

def clear_users_database():
    """Clear all user-related data from the database"""
    
    with app.app_context():
        print("Starting database user cleanup...")
        
        # Count existing records
        try:
            from models import User, Transaction, Profit, TradingPosition, ReferralCode
            
            user_count = User.query.count()
            transaction_count = Transaction.query.count()
            profit_count = Profit.query.count()
            position_count = TradingPosition.query.count()
            
            print(f"Current records:")
            print(f"  Users: {user_count}")
            print(f"  Transactions: {transaction_count}")
            print(f"  Profits: {profit_count}")
            print(f"  Trading Positions: {position_count}")
            
            if user_count == 0:
                print("\nDatabase is already empty!")
                return
            
            # Delete all user-related data in proper order
            print("\nClearing database...")
            
            # Delete dependent records first to avoid foreign key constraints
            tables_to_clear = [
                ('TradingPosition', TradingPosition),
                ('Profit', Profit),
                ('Transaction', Transaction),
                ('ReferralCode', ReferralCode),
                ('User', User)
            ]
            
            for table_name, model_class in tables_to_clear:
                try:
                    count = model_class.query.count()
                    if count > 0:
                        db.session.query(model_class).delete()
                        print(f"  Cleared {count} records from {table_name}")
                except Exception as e:
                    print(f"  Skipping {table_name}: {e}")
            
            # Try to clear other tables that might exist
            additional_tables = ['UserMetrics', 'TradingCycle', 'BroadcastMessage', 'AdminMessage', 'SupportTicket']
            for table_name in additional_tables:
                try:
                    # Try to import and clear if the table exists
                    exec(f"from models import {table_name}")
                    model_class = eval(table_name)
                    count = model_class.query.count()
                    if count > 0:
                        db.session.query(model_class).delete()
                        print(f"  Cleared {count} records from {table_name}")
                except:
                    # Table doesn't exist or can't be imported, skip it
                    pass
            
            # Commit all deletions
            db.session.commit()
            
            print("\nSuccessfully cleared all user data from database!")
            print("\nNew record counts:")
            print(f"  Users: {User.query.count()}")
            print(f"  Transactions: {Transaction.query.count()}")
            print(f"  Profits: {Profit.query.count()}")
            print(f"  Trading Positions: {TradingPosition.query.count()}")
            
            print("\nTelegram bot interactions will now start fresh for all users")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing database: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    clear_users_database()