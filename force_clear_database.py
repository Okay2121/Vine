#!/usr/bin/env python3
"""
Force Clear Database - Complete User Data Removal
Handles foreign key constraints by clearing tables in correct dependency order
"""

import sys
import os
sys.path.append('.')

from app import app, db

def force_clear_database():
    """Force clear all user data by handling foreign keys properly"""
    
    with app.app_context():
        print("Force clearing all user data from database...")
        
        try:
            # Get database connection
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            # Clear tables in dependency order (children first, then parents)
            clear_queries = [
                # Clear all dependent tables first
                'DELETE FROM daily_snapshot;',
                'DELETE FROM user_metrics;',
                'DELETE FROM sender_wallet;',
                'DELETE FROM milestone_tracker;',
                'DELETE FROM trading_cycle;',
                'DELETE FROM trading_position;',
                'DELETE FROM profit;',
                'DELETE FROM transaction;',
                'DELETE FROM referral_reward;',
                'DELETE FROM referral_code;',
                'DELETE FROM support_ticket;',
                'DELETE FROM admin_message;',
                'DELETE FROM broadcast_message;',
                'DELETE FROM "user";'  # Clear users last
            ]
            
            successful_clears = 0
            for query in clear_queries:
                try:
                    cursor.execute(query)
                    table_name = query.split('FROM ')[1].strip(';').strip('"')
                    print(f"Cleared {table_name}")
                    successful_clears += 1
                except Exception as e:
                    table_name = query.split('FROM ')[1].strip(';').strip('"')
                    print(f"Skipping {table_name}: {str(e)}")
            
            # Commit all changes
            connection.commit()
            cursor.close()
            connection.close()
            
            print(f"\nCleared {successful_clears} tables successfully")
            
            # Verify with SQLAlchemy
            from models import User, Transaction, Profit, TradingPosition
            
            final_counts = {
                'Users': User.query.count(),
                'Transactions': Transaction.query.count(), 
                'Profits': Profit.query.count(),
                'Trading Positions': TradingPosition.query.count()
            }
            
            print("\nFinal verification:")
            for table, count in final_counts.items():
                print(f"  {table}: {count}")
            
            total_remaining = sum(final_counts.values())
            if total_remaining == 0:
                print("\nDatabase successfully cleared!")
                print("All user data removed - Telegram bot will start fresh")
                return True
            else:
                print(f"\n{total_remaining} records remain due to constraints")
                return False
                
        except Exception as e:
            print(f"Error during force clear: {e}")
            return False

if __name__ == "__main__":
    success = force_clear_database()
    if success:
        print("\nDatabase cleared successfully!")
    else:
        print("\nPartial clearing completed - some constraints remain")