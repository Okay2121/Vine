"""
Update Transaction Table Schema
This script adds the related_trade_id column to the Transaction table
"""
import logging
import sys
from app import app, db
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def update_transaction_table():
    """Add related_trade_id column to the Transaction table"""
    try:
        with app.app_context():
            # Check if column exists first
            query = text('PRAGMA table_info("transaction")')
            result = db.session.execute(query).fetchall()
            
            # Convert result to column names
            columns = [row[1] for row in result]
            logger.info(f"Current columns in transaction table: {columns}")
            
            # Check if related_trade_id already exists
            if 'related_trade_id' in columns:
                logger.info("related_trade_id column already exists")
                return True
                
            # Add the column
            alter_query = text('ALTER TABLE "transaction" ADD COLUMN related_trade_id INTEGER')
            db.session.execute(alter_query)
            db.session.commit()
            
            # Verify the column was added
            query = text('PRAGMA table_info("transaction")')
            result = db.session.execute(query).fetchall()
            columns = [row[1] for row in result]
            
            if 'related_trade_id' in columns:
                logger.info("related_trade_id column added successfully")
                return True
            else:
                logger.error("related_trade_id column was not added")
                return False
                
    except Exception as e:
        logger.error(f"Error updating transaction table: {e}")
        return False

if __name__ == "__main__":
    print("Updating Transaction table schema...")
    
    if update_transaction_table():
        print("✅ Transaction table updated successfully")
    else:
        print("❌ Failed to update Transaction table")