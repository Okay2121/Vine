#!/usr/bin/env python
"""
Update Trading Stats Display Script
This script fixes the issue where trading stats (wins/losses) aren't displayed correctly
by recalculating stats from the yield_data.json file and updating the UI.
"""
import json
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def update_trading_stats():
    """
    Update the trading stats to match the actual trade history in yield_data.json
    """
    try:
        # Load yield_data.json
        data_file = 'yield_data.json'
        
        if not os.path.exists(data_file):
            logger.error(f"File {data_file} does not exist")
            return False
            
        with open(data_file, 'r') as f:
            yield_data = json.load(f)
        
        logger.info(f"Loaded yield data with {len(yield_data)} user entries")
        
        # Update stats for each user
        updated_count = 0
        
        for user_id, user_data in yield_data.items():
            trades = user_data.get('trades', [])
            
            # Skip users with no trades
            if not trades:
                continue
                
            # Recalculate wins and losses
            winning_trades = 0
            losing_trades = 0
            total_profit = 0
            highest_profit_percentage = 0
            
            for trade in trades:
                trade_yield = trade.get('yield', 0)
                
                # Calculate profit
                entry_price = trade.get('entry', 0)
                exit_price = trade.get('exit', 0)
                profit = exit_price - entry_price
                
                if profit > 0:
                    winning_trades += 1
                    total_profit += profit
                else:
                    losing_trades += 1
                    
                # Track highest profit percentage
                if trade_yield > highest_profit_percentage:
                    highest_profit_percentage = trade_yield
            
            # Update user stats
            yield_data[user_id]['wins'] = winning_trades
            yield_data[user_id]['losses'] = losing_trades
            yield_data[user_id]['total_profit'] = total_profit
            yield_data[user_id]['highest_profit_percentage'] = highest_profit_percentage
            yield_data[user_id]['last_updated'] = datetime.utcnow().isoformat()
            
            # Also update stats dictionary if it exists
            if 'stats' in yield_data[user_id]:
                yield_data[user_id]['stats'].update({
                    'total_trades': winning_trades + losing_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': (winning_trades / (winning_trades + losing_trades) * 100) if (winning_trades + losing_trades) > 0 else 0,
                    'total_profit': total_profit
                })
            
            updated_count += 1
            logger.info(f"Updated stats for user {user_id}: {winning_trades} wins, {losing_trades} losses")
        
        # Save the updated data
        with open(data_file, 'w') as f:
            json.dump(yield_data, f, indent=2)
            
        logger.info(f"Successfully updated stats for {updated_count} users")
        return True
        
    except Exception as e:
        logger.error(f"Error updating trading stats: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Updating trading stats display...")
    
    if update_trading_stats():
        print("✅ Trading stats updated successfully!")
    else:
        print("❌ Error updating trading stats. Check the logs for details.")