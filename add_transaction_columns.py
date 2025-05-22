"""
Script to add new columns to Transaction table and create indexes
This enhances the deposit monitoring system to prevent duplicate transactions
"""
from app import app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_transaction_columns():
    """
    Add new columns to the Transaction table:
    - processed_at - when the transaction was actually processed
    - Make tx_hash unique and indexed to prevent duplicate processing
    - Create indexes for common query patterns
    """
    try:
        logger.info("Starting migration: Adding columns and indexes to Transaction table...")
        with app.app_context():
            # Use raw SQL to check if the columns exist and add them if they don't
            with db.engine.connect() as conn:
                # Check if processed_at column exists
                result = conn.execute(text(
                    """
                    SELECT name FROM pragma_table_info('transaction') 
                    WHERE name='processed_at'
                    """
                ))
                
                if not result.fetchone():
                    # Add the processed_at column
                    logger.info("Adding processed_at column to Transaction table...")
                    conn.execute(text(
                        """
                        ALTER TABLE "transaction" 
                        ADD COLUMN processed_at TIMESTAMP
                        """
                    ))
                    conn.commit()
                    logger.info("Added processed_at column to Transaction table.")
                else:
                    logger.info("Column 'processed_at' already exists in the Transaction table.")
                
                # Create index on tx_hash if it doesn't exist
                result = conn.execute(text(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='ix_transaction_tx_hash'
                    """
                ))
                
                if not result.fetchone():
                    logger.info("Creating index on tx_hash column...")
                    conn.execute(text(
                        """
                        CREATE INDEX ix_transaction_tx_hash ON "transaction" (tx_hash)
                        """
                    ))
                    conn.commit()
                    logger.info("Created index on tx_hash column.")
                else:
                    logger.info("Index on tx_hash already exists.")
                
                # Create index on user_id and transaction_type if it doesn't exist
                result = conn.execute(text(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='idx_transaction_user_type'
                    """
                ))
                
                if not result.fetchone():
                    logger.info("Creating index on user_id and transaction_type columns...")
                    conn.execute(text(
                        """
                        CREATE INDEX idx_transaction_user_type ON "transaction" (user_id, transaction_type)
                        """
                    ))
                    conn.commit()
                    logger.info("Created index on user_id and transaction_type columns.")
                else:
                    logger.info("Index on user_id and transaction_type already exists.")
                
                # Create index on status if it doesn't exist
                result = conn.execute(text(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='idx_transaction_status'
                    """
                ))
                
                if not result.fetchone():
                    logger.info("Creating index on status column...")
                    conn.execute(text(
                        """
                        CREATE INDEX idx_transaction_status ON "transaction" (status)
                        """
                    ))
                    conn.commit()
                    logger.info("Created index on status column.")
                else:
                    logger.info("Index on status already exists.")
                
                # Create index on timestamp if it doesn't exist
                result = conn.execute(text(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='ix_transaction_timestamp'
                    """
                ))
                
                if not result.fetchone():
                    logger.info("Creating index on timestamp column...")
                    conn.execute(text(
                        """
                        CREATE INDEX ix_transaction_timestamp ON "transaction" (timestamp)
                        """
                    ))
                    conn.commit()
                    logger.info("Created index on timestamp column.")
                else:
                    logger.info("Index on timestamp already exists.")
            
        logger.info("Transaction table migration complete.")
        return True
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    add_transaction_columns()