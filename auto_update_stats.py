#!/usr/bin/env python
"""
Auto-Update Trading Stats Hook
This script adds hooks to the yield_module that automatically update
trading stats whenever new trades are added to the history.
"""
import logging
import os
import json
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def install_auto_update_hook():
    """
    Install hooks into the code that adds trades to automatically update stats
    """
    try:
        # Look for the place where trades are added to the yield_data.json file
        bot_file = 'bot_v20_runner.py'
        
        if not os.path.exists(bot_file):
            logger.error(f"Bot file {bot_file} not found")
            return False
            
        with open(bot_file, 'r') as f:
            content = f.read()
            
        # Find the code that adds trades to yield_data.json
        add_trade_pattern = "def add_trade_to_history(user_id, token_name, entry_price, exit_price, yield_percentage=None):"
        if add_trade_pattern not in content:
            logger.error("Could not find add_trade_to_history function in the bot file")
            return False
            
        # Find the location to insert the auto-update hook
        save_json_pattern = "        # Save the updated data\n        with open(data_file, 'w') as f:"
        if save_json_pattern not in content:
            logger.error("Could not find the location to insert the auto-update hook")
            return False
            
        # Create the auto-update hook
        update_hook = """        # Auto-update trading stats
        # Calculate wins and losses
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        highest_profit_percentage = 0
        
        for trade in yield_data[user_id_str]['trades']:
            trade_yield = trade.get('yield', 0)
            
            # Determine if win or loss
            if trade_yield > 0:
                winning_trades += 1
            else:
                losing_trades += 1
                
            # Track highest profit percentage
            if trade_yield > highest_profit_percentage:
                highest_profit_percentage = trade_yield
                
            # Calculate profit amount
            entry = trade.get('entry', 0)
            exit = trade.get('exit', 0)
            profit = exit - entry
            total_profit += profit
        
        # Update user stats
        yield_data[user_id_str]['wins'] = winning_trades
        yield_data[user_id_str]['losses'] = losing_trades
        yield_data[user_id_str]['total_profit'] = total_profit
        yield_data[user_id_str]['highest_profit_percentage'] = highest_profit_percentage
        yield_data[user_id_str]['last_updated'] = datetime.now().isoformat()
        
        # Also update stats dictionary if it exists
        if 'stats' in yield_data[user_id_str]:
            yield_data[user_id_str]['stats'].update({
                'total_trades': winning_trades + losing_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / (winning_trades + losing_trades) * 100) if (winning_trades + losing_trades) > 0 else 0,
                'total_profit': total_profit
            })
        
        logging.info(f"Updated stats for user {user_id}: {winning_trades} wins, {losing_trades} losses")
        
"""
        
        # Insert the hook before saving the file
        new_content = content.replace(save_json_pattern, update_hook + save_json_pattern)
        
        # Add datetime import if needed
        if "from datetime import datetime" not in new_content:
            datetime_import = "from datetime import datetime, timedelta\n"
            import_section_end = new_content.find("\n\n", new_content.find("import"))
            new_content = new_content[:import_section_end] + datetime_import + new_content[import_section_end:]
        
        # Write the updated content back to the file
        with open(bot_file, 'w') as f:
            f.write(new_content)
            
        logger.info("Successfully installed auto-update hook in add_trade_to_history function")
        
        # Now run the update once to fix current stats
        update_all_stats()
        
        return True
        
    except Exception as e:
        logger.error(f"Error installing auto-update hook: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def update_all_stats():
    """
    Update all stats in yield_data.json immediately
    """
    try:
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
                
                # Determine if win or loss
                if trade_yield > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                    
                # Track highest profit percentage
                if trade_yield > highest_profit_percentage:
                    highest_profit_percentage = trade_yield
                
                # Calculate profit amount
                entry = trade.get('entry', 0)
                exit = trade.get('exit', 0)
                profit = exit - entry
                total_profit += profit
            
            # Update user stats
            yield_data[user_id]['wins'] = winning_trades
            yield_data[user_id]['losses'] = losing_trades
            yield_data[user_id]['total_profit'] = total_profit
            yield_data[user_id]['highest_profit_percentage'] = highest_profit_percentage
            yield_data[user_id]['last_updated'] = datetime.now().isoformat()
            
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
        logger.error(f"Error updating all stats: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Installing automatic stats update hooks...")
    
    if install_auto_update_hook():
        print("✅ Auto-update hooks installed successfully!")
        print("Stats will now update automatically whenever new trades are added")
    else:
        print("❌ Error installing auto-update hooks. Check the logs for details.")
        print("Attempting manual stats update instead...")
        
        if update_all_stats():
            print("✅ Manual stats update completed successfully!")
        else:
            print("❌ Error with manual stats update. Check the logs for details.")