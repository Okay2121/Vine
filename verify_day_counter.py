#!/usr/bin/env python
"""
Quick Day Counter Verification
-----------------------------
Verifies the day counter logic works for both scenarios
"""

from app import app
from models import User, Transaction
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_day_counter():
    """Verify day counter logic for both scenarios"""
    
    with app.app_context():
        # Test user from logs (5488280696) who now has 1.5 SOL
        user = User.query.filter_by(telegram_id='5488280696').first()
        
        if user:
            # Apply the same logic as dashboard
            first_deposit = Transaction.query.filter_by(
                user_id=user.id, 
                transaction_type='deposit',
                status='completed'
            ).order_by(Transaction.timestamp).first()
            
            if first_deposit and user.balance > 0:
                days_active = (datetime.utcnow().date() - first_deposit.timestamp.date()).days + 1
                source = "first deposit date"
            elif user.balance > 0:
                days_active = (datetime.utcnow().date() - user.joined_at.date()).days + 1
                source = "join date (no deposit record)"
            else:
                days_active = 0
                source = "no SOL balance"
            
            logger.info(f"User {user.telegram_id}:")
            logger.info(f"  Balance: {user.balance} SOL")
            logger.info(f"  Days active: {days_active}")
            logger.info(f"  Source: {source}")
            
            # Dashboard display
            if days_active > 0:
                display = f"Day: {days_active}"
            else:
                display = "Day: Start your streak today!"
            
            logger.info(f"  Dashboard shows: '{display}'")
            
            return True
        
        return False

if __name__ == "__main__":
    verify_day_counter()