#!/usr/bin/env python
"""
Clean up test users from database
"""

from app import app, db
from models import User, Transaction, SenderWallet, TradingPosition

with app.app_context():
    # Define test user patterns
    test_patterns = ['test_', 'cumulative_test', 'deposit_test', 'quicktest', '_test_']
    test_telegram_ids = ['888888888', '999999999', '777777777', '555555555', '123456', 'test123', 'test_1750362724']
    
    print("Cleaning up test users...")
    
    # Find all test users
    test_users = []
    all_users = User.query.all()
    
    for user in all_users:
        is_test = (
            any(pattern in user.username.lower() for pattern in test_patterns) or
            user.telegram_id in test_telegram_ids or
            'test' in user.username.lower()
        )
        if is_test:
            test_users.append(user)
    
    print(f"Found {len(test_users)} test users to remove")
    
    # Clean up each test user
    for user in test_users:
        print(f"Removing {user.username}...")
        
        # Delete related records
        Transaction.query.filter_by(user_id=user.id).delete()
        SenderWallet.query.filter_by(user_id=user.id).delete()
        TradingPosition.query.filter_by(user_id=user.id).delete()
        
        # Delete the user
        db.session.delete(user)
    
    # Commit changes
    db.session.commit()
    
    print(f"Cleaned up {len(test_users)} test users")
    
    # Show remaining users
    remaining_users = User.query.all()
    print(f"\nRemaining users in database: {len(remaining_users)}")
    for user in remaining_users:
        print(f"  {user.username} (TG: {user.telegram_id})")