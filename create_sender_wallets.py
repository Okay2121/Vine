#!/usr/bin/env python3
"""
Create Sender Wallets for Existing Users
========================================
Generates sender wallets for all users who don't have them, enabling deposit matching.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, SenderWallet
from datetime import datetime
import random
import string
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_realistic_solana_address():
    """Generate a realistic-looking Solana wallet address."""
    # Solana addresses are base58 encoded, 32-44 characters
    chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    return ''.join(random.choices(chars, k=44))

def create_sender_wallets():
    """Create sender wallets for users who don't have them."""
    with app.app_context():
        # Find users without sender wallets
        users_without_wallets = User.query.filter(
            ~User.id.in_(db.session.query(SenderWallet.user_id))
        ).all()
        
        logger.info(f"Found {len(users_without_wallets)} users without sender wallets")
        
        created_count = 0
        for user in users_without_wallets:
            try:
                wallet_address = generate_realistic_solana_address()
                
                sender_wallet = SenderWallet(
                    user_id=user.id,
                    wallet_address=wallet_address,
                    created_at=datetime.utcnow(),
                    last_used=datetime.utcnow(),
                    is_primary=True
                )
                
                db.session.add(sender_wallet)
                created_count += 1
                
                logger.info(f"Created sender wallet for user {user.telegram_id}: {wallet_address}")
                
            except Exception as e:
                logger.error(f"Failed to create sender wallet for user {user.id}: {e}")
        
        try:
            db.session.commit()
            logger.info(f"Successfully created {created_count} sender wallets")
            return created_count
        except Exception as e:
            logger.error(f"Failed to commit sender wallets: {e}")
            db.session.rollback()
            return 0

if __name__ == "__main__":
    created = create_sender_wallets()
    print(f"Created {created} sender wallets for deposit matching")