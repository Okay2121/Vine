"""
Update database tables for the Buy/Sell trading system
"""
from app import app, db
from models import TradingPosition, Transaction, Profit
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_tables():
    """
    Update database tables to support the Buy/Sell trading format
    Creates/updates tables based on SQLAlchemy models
    """
    with app.app_context():
        logger.info("Starting database schema update")
        try:
            # Create/update tables based on SQLAlchemy models
            db.create_all()
            logger.info("Database schema updated successfully")
            return True, "Database updated successfully"
        except Exception as e:
            logger.error(f"Error updating database schema: {str(e)}")
            return False, f"Error: {str(e)}"

if __name__ == "__main__":
    success, message = update_database_tables()
    print(message)