#!/usr/bin/env python
"""
Fix Trading Stats Display in Telegram Bot
This script updates the bot_v20_runner.py file to show the correct
wins and losses from the yield_data.json file instead of just today's trades.
"""
import logging
import os
import json
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_trading_stats_display():
    """
    Fix the trading stats display to show wins/losses from yield_data.json
    instead of only counting today's trades from the Transaction table.
    """
    try:
        # Path to the bot file
        bot_file = 'bot_v20_runner.py'
        
        if not os.path.exists(bot_file):
            logger.error(f"Bot file {bot_file} not found")
            return False
            
        # Read the bot file
        with open(bot_file, 'r') as f:
            content = f.read()
            
        # Find the section where trading stats are computed
        trading_stats_section = """            # Count profitable vs loss trades
            profitable_trades = 0
            loss_trades = 0
            for tx in trades_today:
                if hasattr(tx, 'profit_amount') and tx.profit_amount is not None:
                    if tx.profit_amount > 0:
                        profitable_trades += 1
                    elif tx.profit_amount < 0:
                        loss_trades += 1
            
            # Calculate win rate
            total_trades = profitable_trades + loss_trades
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0"""
        
        # Create improved stats section that uses yield_data.json
        improved_stats_section = """            # Get trading stats from yield_data.json instead of just today's trades
            profitable_trades = 0
            loss_trades = 0
            
            # Try to get stats from yield_data.json file first
            try:
                yield_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yield_data.json')
                
                if os.path.exists(yield_data_path):
                    with open(yield_data_path, 'r') as f:
                        yield_data = json.load(f)
                    
                    user_id_str = str(user.id)
                    if user_id_str in yield_data:
                        user_data = yield_data[user_id_str]
                        # Get wins and losses from yield_data
                        profitable_trades = user_data.get('wins', 0)
                        loss_trades = user_data.get('losses', 0)
                        logging.info(f"Got stats from yield_data.json: {profitable_trades} wins, {loss_trades} losses")
                        
            except Exception as e:
                logging.error(f"Error reading yield_data.json: {e}")
                
            # Fallback to calculating from today's trades if we didn't get stats from yield_data.json
            if profitable_trades == 0 and loss_trades == 0:
                for tx in trades_today:
                    if hasattr(tx, 'profit_amount') and tx.profit_amount is not None:
                        if tx.profit_amount > 0:
                            profitable_trades += 1
                        elif tx.profit_amount < 0:
                            loss_trades += 1
            
            # Calculate win rate
            total_trades = profitable_trades + loss_trades
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0"""
        
        # Replace the trading stats section
        if trading_stats_section in content:
            new_content = content.replace(trading_stats_section, improved_stats_section)
            
            # Make sure import json and os are at the top of the file if not already there
            if "import json" not in new_content:
                import_section_end = new_content.find("\n\n", new_content.find("import"))
                new_content = new_content[:import_section_end] + "\nimport json" + new_content[import_section_end:]
                
            if "import os" not in new_content:
                import_section_end = new_content.find("\n\n", new_content.find("import"))
                new_content = new_content[:import_section_end] + "\nimport os" + new_content[import_section_end:]
            
            # Write the new content back to the file
            with open(bot_file, 'w') as f:
                f.write(new_content)
                
            logger.info("Successfully updated trading stats display code")
            return True
        else:
            logger.error("Could not find the trading stats section in the bot file")
            return False
            
    except Exception as e:
        logger.error(f"Error fixing trading stats display: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Fixing trading stats display to show all trades from yield_data.json...")
    
    if fix_trading_stats_display():
        print("✅ Trading stats display code has been successfully updated!")
        print("The bot will now show your total wins and losses from all trades in yield_data.json")
        print("\nRestart the bot for the changes to take effect.")
    else:
        print("❌ Error fixing trading stats display. See logs for details.")