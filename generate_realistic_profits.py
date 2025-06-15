#!/usr/bin/env python
"""
Generate Realistic Profit Data for Dashboard Testing
===================================================
This script creates realistic profit entries for users with balances
to ensure the autopilot dashboard displays properly.
"""

import random
from datetime import datetime, timedelta
from app import app, db
from models import User, Profit, Transaction

def generate_user_profits(user_id, days_back=7):
    """Generate realistic profit data for a user over the past days"""
    user = User.query.get(user_id)
    if not user or user.balance <= 0:
        return 0
    
    profits_created = 0
    current_date = datetime.utcnow().date()
    
    # Generate profits for the past few days
    for i in range(days_back):
        profit_date = current_date - timedelta(days=i)
        
        # Check if profit already exists for this date
        existing_profit = Profit.query.filter_by(user_id=user_id, date=profit_date).first()
        if existing_profit:
            continue
        
        # 70% chance of profit on any given day
        if random.random() < 0.7:
            # Generate realistic profit amount (0.5% to 5% of balance)
            profit_percentage = random.uniform(0.5, 5.0)
            profit_amount = (user.balance * profit_percentage) / 100
            
            # Create profit record
            profit = Profit(
                user_id=user_id,
                amount=profit_amount,
                percentage=profit_percentage,
                date=profit_date
            )
            
            db.session.add(profit)
            profits_created += 1
            
            # Also create a trade_profit transaction for consistency
            transaction = Transaction(
                user_id=user_id,
                amount=profit_amount,
                transaction_type='trade_profit',
                status='completed',
                timestamp=datetime.combine(profit_date, datetime.min.time()) + timedelta(hours=random.randint(8, 18))
            )
            
            db.session.add(transaction)
    
    try:
        db.session.commit()
        print(f"Created {profits_created} profit entries for user {user_id}")
        return profits_created
    except Exception as e:
        db.session.rollback()
        print(f"Error creating profits for user {user_id}: {e}")
        return 0

def generate_profits_for_all_users():
    """Generate profit data for all users with balances"""
    with app.app_context():
        # Get all users with positive balances
        users_with_balance = User.query.filter(User.balance > 0).all()
        total_profits = 0
        
        print(f"Generating profit data for {len(users_with_balance)} users...")
        
        for user in users_with_balance:
            profits = generate_user_profits(user.id, days_back=7)
            total_profits += profits
        
        print(f"Total profit entries created: {total_profits}")
        return total_profits

if __name__ == "__main__":
    generate_profits_for_all_users()