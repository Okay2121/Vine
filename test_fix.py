#!/usr/bin/env python
"""Test script for verifying balance adjustments and broadcast trades"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Set up app context
from app import app, db
with app.app_context():
    from models import User, Transaction
    
    # Test 1: Balance adjustment
    print("===== Testing Balance Adjustment =====")
    
    # Use our fixed balance manager
    try:
        import fixed_balance_manager
        
        # Find a user to test with
        test_user = User.query.first()
        if test_user:
            print(f"Found test user: {test_user.username} (ID: {test_user.id})")
            print(f"Current balance: {test_user.balance}")
            
            # Try to adjust balance
            success, message = fixed_balance_manager.adjust_balance(
                test_user.telegram_id, 
                1.0, 
                "Testing fixed balance manager"
            )
            
            print(f"Balance adjustment result: {success}")
            print(message)
            
            # Verify the balance was updated
            db.session.expire_all()
            fresh_user = User.query.get(test_user.id)
            print(f"Updated balance: {fresh_user.balance}")
        else:
            print("No users found for testing")
    
    except Exception as e:
        print(f"Error testing balance adjustment: {e}")
        import traceback
        print(traceback.format_exc())
    
    # Test 2: Add trade to history
    print("\n===== Testing Trade History =====")
    try:
        from bot_v20_runner import add_trade_to_history
        
        # Find a user to test with
        test_user = User.query.first()
        if test_user:
            print(f"Adding trade for user: {test_user.username} (ID: {test_user.id})")
            
            # Try to add a trade
            result = add_trade_to_history(
                user_id=test_user.id,
                token_name="$TEST",
                entry_price=0.005,
                exit_price=0.007,
                profit_amount=0.5,
                tx_hash="https://solscan.io/tx/test123"
            )
            
            print(f"Add trade result: {result}")
            
            # Check the trade history
            import json
            try:
                with open('yield_data.json', 'r') as f:
                    yield_data = json.load(f)
                    user_trades = yield_data.get(str(test_user.id), {}).get('trades', [])
                    print(f"User has {len(user_trades)} trades in history")
                    if user_trades:
                        print(f"Most recent trade: {user_trades[0]}")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error reading yield_data.json: {e}")
            
            # Check database for trading position
            from models import TradingPosition
            positions = TradingPosition.query.filter_by(user_id=test_user.id).all()
            print(f"User has {len(positions)} trading positions in database")
            for pos in positions:
                print(f"Position: {pos.token_name}, Status: {pos.status}")
        else:
            print("No users found for testing")
            
    except Exception as e:
        print(f"Error testing trade history: {e}")
        import traceback
        print(traceback.format_exc())

print("Tests completed!")