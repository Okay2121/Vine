#!/usr/bin/env python
"""
Script to fix user search in admin balance adjustment feature
and add the ability to search for users case-insensitively
"""
import logging
from app import app, db
from models import User
from sqlalchemy import func

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def search_for_user(search_term):
    """
    Search for a user by Telegram ID or username with case-insensitive matching
    """
    with app.app_context():
        user = None
        
        # First try exact telegram_id search
        try:
            user = User.query.filter_by(telegram_id=search_term).first()
        except:
            pass
        
        # If not found, try searching by username (case-insensitive)
        if not user:
            # Handle @username format
            if search_term.startswith('@'):
                username = search_term[1:]  # Remove @ prefix
            else:
                username = search_term
                
            # Use case-insensitive query
            user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        
        return user

def test_user_search():
    """Test the user search functionality with various formats"""
    test_terms = [
        "briensmart",
        "@briensmart", 
        "@BRIENSMART", 
        "BRIENSMART",
        "BrienSmart"
    ]
    
    logger.info("Testing user search with various formats")
    
    for term in test_terms:
        user = search_for_user(term)
        if user:
            logger.info(f"✅ Found user with search term '{term}': ID={user.id}, username={user.username}")
        else:
            logger.info(f"❌ User not found with search term '{term}'")
    
    # Show all users in the database for reference
    all_users = User.query.all()
    
    logger.info("")
    logger.info(f"All users in database ({len(all_users)}):")
    for user in all_users:
        logger.info(f"ID: {user.id}, Telegram ID: {user.telegram_id}, Username: {user.username}")

if __name__ == "__main__":
    # Test the user search functionality
    test_user_search()