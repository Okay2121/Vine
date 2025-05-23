"""
Script to add new columns to TradingPosition table
This enhances the trading system to support the Buy/Sell transaction format
"""

from app import app, db
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_trading_columns():
    """
    Add new columns to the TradingPosition table:
    - buy_tx_hash - transaction hash for the buy transaction
    - sell_tx_hash - transaction hash for the sell transaction
    - buy_timestamp - when the buy was executed
    - sell_timestamp - when the sell was executed
    - roi_percentage - calculated ROI percentage
    - paired_position_id - for linking related buy/sell positions
    """
    logger.info("Starting to add columns to TradingPosition table")
    
    with app.app_context():
        # Check if the database engine is SQLite
        is_sqlite = 'sqlite' in db.engine.url.drivername
        
        # Create a connection
        connection = db.engine.connect()
        transaction = connection.begin()
        
        try:
            # Check which columns already exist
            if is_sqlite:
                result = connection.execute("PRAGMA table_info(trading_position)")
                existing_columns = [row[1] for row in result]
            else:
                # PostgreSQL version - adjust as needed
                result = connection.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'trading_position'
                """)
                existing_columns = [row[0] for row in result]
            
            # Add each column if it doesn't exist
            columns_to_add = {
                "buy_tx_hash": "VARCHAR(128)",
                "sell_tx_hash": "VARCHAR(128)",
                "buy_timestamp": "DATETIME",
                "sell_timestamp": "DATETIME",
                "roi_percentage": "FLOAT",
                "paired_position_id": "INTEGER"
            }
            
            for column_name, column_type in columns_to_add.items():
                if column_name.lower() not in [col.lower() for col in existing_columns]:
                    if is_sqlite:
                        connection.execute(f"ALTER TABLE trading_position ADD COLUMN {column_name} {column_type}")
                    else:
                        connection.execute(f"ALTER TABLE trading_position ADD COLUMN {column_name} {column_type}")
                    logger.info(f"Added column {column_name} to TradingPosition table")
                else:
                    logger.info(f"Column {column_name} already exists in TradingPosition table")
            
            # Check if Transaction table has price column
            if is_sqlite:
                result = connection.execute("PRAGMA table_info(transaction)")
                existing_columns = [row[1] for row in result]
            else:
                result = connection.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'transaction'
                """)
                existing_columns = [row[0] for row in result]
                
            # Add price column to Transaction if needed
            if "price" not in [col.lower() for col in existing_columns]:
                if is_sqlite:
                    connection.execute("ALTER TABLE transaction ADD COLUMN price FLOAT")
                else:
                    connection.execute("ALTER TABLE transaction ADD COLUMN price FLOAT")
                logger.info("Added column price to Transaction table")
            else:
                logger.info("Column price already exists in Transaction table")
            
            # Commit the transaction
            transaction.commit()
            logger.info("Successfully added all necessary columns to the database")
            
            return True, "Successfully added columns"
            
        except Exception as e:
            # Rollback in case of error
            transaction.rollback()
            logger.error(f"Error adding columns: {str(e)}")
            return False, f"Error: {str(e)}"
        
        finally:
            # Close the connection
            connection.close()

if __name__ == "__main__":
    success, message = add_trading_columns()
    print(message)