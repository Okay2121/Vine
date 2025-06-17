#!/usr/bin/env python3
"""
Simple Deposit Detection Debug Script
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, SenderWallet, Transaction
from helpers import get_global_deposit_wallet
import requests
import json
from config import SOLANA_RPC_URL, MIN_DEPOSIT

def check_system():
    """Check the deposit detection system components."""
    print("=== Deposit Detection System Debug ===")
    
    with app.app_context():
        # 1. Check deposit wallet
        deposit_wallet = get_global_deposit_wallet()
        print(f"Admin wallet: {deposit_wallet}")
        
        # 2. Check sender wallets
        sender_count = SenderWallet.query.count()
        print(f"Registered sender wallets: {sender_count}")
        
        if sender_count > 0:
            print("Sample sender wallets:")
            for wallet in SenderWallet.query.limit(3).all():
                user = User.query.get(wallet.user_id)
                print(f"  {wallet.wallet_address} -> User {user.telegram_id if user else 'Unknown'}")
        else:
            print("WARNING: No sender wallets registered!")
            print("Users need to register sender wallets for deposit matching to work.")
        
        # 3. Test API connection
        print(f"\nTesting Solana RPC: {SOLANA_RPC_URL}")
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [deposit_wallet, {"limit": 5}]
            }
            
            response = requests.post(SOLANA_RPC_URL, headers=headers, data=json.dumps(payload))
            result = response.json()
            
            print(f"API Status: {response.status_code}")
            
            if 'result' in result:
                txs = result['result']
                print(f"Found {len(txs)} transactions")
                
                for i, tx in enumerate(txs):
                    sig = tx.get('signature', 'N/A')[:16]
                    print(f"  TX {i+1}: {sig}...")
                    
                    # Check if already processed
                    existing = Transaction.query.filter_by(tx_hash=tx.get('signature')).first()
                    if existing:
                        print(f"    Already processed: User {existing.user_id}")
                    else:
                        print(f"    Not processed yet")
            else:
                print(f"API Error: {result}")
                
        except Exception as e:
            print(f"API Test Failed: {e}")
        
        # 4. Check recent deposits
        recent_deposits = Transaction.query.filter_by(transaction_type='deposit').order_by(Transaction.id.desc()).limit(5).all()
        print(f"\nRecent deposits: {len(recent_deposits)}")
        for tx in recent_deposits:
            print(f"  {tx.amount} SOL -> User {tx.user_id} (TX: {tx.tx_hash[:16]}...)")

if __name__ == "__main__":
    check_system()