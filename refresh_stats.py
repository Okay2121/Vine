#!/usr/bin/env python
"""
Quick Stats Refresh Tool
Run this script anytime the trading stats display doesn't match the actual trade history
"""
import json
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def refresh_trading_stats():
    """
    Update trading stats for all users based on their actual trade history
    """
    try:
        # Path to yield data file
        data_file = 'yield_data.json'
        
        # Load the data
        with open(data_file, 'r') as f:
            yield_data = json.load(f)
        
        print(f"Found {len(yield_data)} users in database")
        
        # Process each user
        for user_id, data in yield_data.items():
            trades = data.get('trades', [])
            
            if not trades:
                print(f"User {user_id} has no trades, skipping")
                continue
            
            # Calculate stats
            winning_trades = sum(1 for trade in trades if trade.get('yield', 0) > 0)
            losing_trades = sum(1 for trade in trades if trade.get('yield', 0) <= 0)
            
            # Update stats
            yield_data[user_id]['wins'] = winning_trades
            yield_data[user_id]['losses'] = losing_trades
            yield_data[user_id]['last_updated'] = datetime.now().isoformat()
            
            # Update stats dictionary if it exists
            if 'stats' in yield_data[user_id]:
                total_trades = winning_trades + losing_trades
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                yield_data[user_id]['stats'].update({
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate
                })
            
            print(f"User {user_id}: {winning_trades} wins, {losing_trades} losses from {len(trades)} trades")
        
        # Save updated data
        with open(data_file, 'w') as f:
            json.dump(yield_data, f, indent=2)
            
        print("✅ Stats refresh complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error refreshing stats: {str(e)}")
        return False

if __name__ == "__main__":
    print("Refreshing trading stats...")
    refresh_trading_stats()