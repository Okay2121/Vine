"""
Reset database for the Buy/Sell trading system
"""
from app import app, db
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_db():
    """
    Reset the database by dropping all tables and recreating them
    """
    with app.app_context():
        logger.info("Dropping all database tables")
        try:
            # Drop all tables
            db.drop_all()
            logger.info("All tables dropped successfully")
            
            # Recreate all tables
            logger.info("Creating tables from models")
            db.create_all()
            logger.info("All tables created successfully")
            
            # Create a test admin user
            from models import User, UserStatus
            
            # Check if admin user exists
            admin = User.query.filter_by(telegram_id="admin").first()
            if not admin:
                # Create admin user
                admin = User(
                    telegram_id="admin",
                    username="admin",
                    first_name="Admin",
                    last_name="User",
                    status=UserStatus.ACTIVE,
                    wallet_address="admin_wallet",
                    balance=100.0
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Created test admin user")
            
            return True, "Database reset successfully"
            
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            return False, f"Error: {str(e)}"

if __name__ == "__main__":
    success, message = reset_db()
    print(message)