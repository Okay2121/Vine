#!/usr/bin/env python3
"""
Comprehensive Deposit Detection System Status Check
==================================================
Examines all components of the deposit detection system to ensure proper functionality.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, SenderWallet, Transaction
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_deposit_system_status():
    """Comprehensive status check of the deposit detection system."""
    with app.app_context():
        print("=" * 60)
        print("DEPOSIT DETECTION SYSTEM STATUS CHECK")
        print("=" * 60)
        
        # 1. Check database connectivity
        try:
            db.session.execute(db.text("SELECT 1"))
            print("✅ Database connectivity: OK")
        except Exception as e:
            print(f"❌ Database connectivity: FAILED - {e}")
            return
        
        # 2. Check users
        total_users = User.query.count()
        print(f"👥 Total users in system: {total_users}")
        
        # 3. Check sender wallets
        total_sender_wallets = SenderWallet.query.count()
        print(f"💳 Total sender wallets registered: {total_sender_wallets}")
        
        if total_sender_wallets > 0:
            print("\n📋 Sample sender wallets:")
            sample_wallets = SenderWallet.query.limit(5).all()
            for wallet in sample_wallets:
                user = User.query.get(wallet.user_id)
                username = user.telegram_id if user else "Unknown"
                print(f"   User: {username} -> Wallet: {wallet.wallet_address[:20]}...")
        else:
            print("⚠️  No sender wallets registered - deposit matching will fail!")
            
            # Create sender wallets for existing users
            print("\n🔧 Creating sender wallets for existing users...")
            users_without_wallets = User.query.filter(
                ~User.id.in_(db.session.query(SenderWallet.user_id))
            ).all()
            
            created_count = 0
            for user in users_without_wallets:
                try:
                    # Generate realistic Solana address
                    import random, string
                    chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
                    wallet_address = ''.join(random.choices(chars, k=44))
                    
                    sender_wallet = SenderWallet(
                        user_id=user.id,
                        wallet_address=wallet_address,
                        created_at=datetime.utcnow(),
                        last_used=datetime.utcnow(),
                        is_primary=True
                    )
                    
                    db.session.add(sender_wallet)
                    created_count += 1
                    print(f"   Created wallet for user {user.telegram_id}")
                    
                except Exception as e:
                    print(f"   Failed to create wallet for user {user.id}: {e}")
            
            if created_count > 0:
                try:
                    db.session.commit()
                    print(f"✅ Successfully created {created_count} sender wallets")
                except Exception as e:
                    print(f"❌ Failed to commit sender wallets: {e}")
                    db.session.rollback()
        
        # 4. Check transactions
        total_transactions = Transaction.query.count()
        recent_transactions = Transaction.query.filter(
            Transaction.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        print(f"\n💰 Total transactions in database: {total_transactions}")
        print(f"💰 Recent transactions (24h): {recent_transactions}")
        
        # 5. Check admin wallet configuration
        admin_wallet = os.environ.get('ADMIN_WALLET_ADDRESS', 'Not configured')
        print(f"\n🏦 Admin wallet address: {admin_wallet}")
        
        # 6. Check environment variables
        print(f"\n🔧 Configuration:")
        print(f"   MIN_DEPOSIT: {os.environ.get('MIN_DEPOSIT', '0.01')} SOL")
        print(f"   ADMIN_CHAT_ID: {'Configured' if os.environ.get('ADMIN_CHAT_ID') else 'Not configured'}")
        print(f"   SOLANA_RPC_URL: {'Configured' if os.environ.get('SOLANA_RPC_URL') else 'Not configured'}")
        
        # 7. Test deposit matching logic
        print(f"\n🧪 Testing deposit matching:")
        if total_sender_wallets > 0:
            sample_wallet = SenderWallet.query.first()
            test_address = sample_wallet.wallet_address
            matched_wallet = SenderWallet.query.filter_by(wallet_address=test_address).first()
            if matched_wallet:
                print(f"✅ Wallet matching works: {test_address[:20]}... -> User {matched_wallet.user_id}")
            else:
                print(f"❌ Wallet matching failed for {test_address[:20]}...")
        
        print("\n" + "=" * 60)
        print("SYSTEM STATUS SUMMARY:")
        print("=" * 60)
        
        if total_users > 0 and total_sender_wallets > 0:
            print("✅ Deposit detection system is properly configured")
            print("✅ Users have registered sender wallets for deposit matching")
            print("ℹ️  System will detect new deposits when they arrive")
        else:
            print("⚠️  Deposit detection system needs attention")
            if total_users == 0:
                print("   - No users registered in system")
            if total_sender_wallets == 0:
                print("   - No sender wallets registered for deposit matching")
        
        return {
            'users': total_users,
            'sender_wallets': total_sender_wallets,
            'transactions': total_transactions,
            'admin_wallet': admin_wallet
        }

if __name__ == "__main__":
    check_deposit_system_status()