"""
Update Performance Stats - Ensure trade history tallies with performance page
This script updates the performance statistics to match the trades in history
"""
import sys
import os
import json
import random
from datetime import datetime, timedelta

def main():
    """Update performance statistics based on trade history"""
    print("🔄 Updating performance statistics to match trade history...")
    
    # Set up paths
    sys.path.append('.')
    
    # Import necessary modules
    from main import app
    
    with app.app_context():
        # Import models
        from models import db, User, TradingPosition, Profit
        from sqlalchemy import text
        
        # Get all users
        users = User.query.all()
        print(f"Found {len(users)} users")
        
        for user in users:
            # Get user's trades
            trades = TradingPosition.query.filter_by(
                user_id=user.id,
                status='closed'
            ).all()
            
            # Calculate performance metrics
            total_profit = 0
            total_trades = len(trades)
            winning_trades = 0
            losing_trades = 0
            
            for trade in trades:
                # Calculate profit/loss for this trade
                pl_amount = (trade.current_price - trade.entry_price) * trade.amount
                
                # Update stats
                total_profit += pl_amount
                if pl_amount > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
            
            # Calculate win rate
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            print(f"User {user.id}: {total_trades} trades, {winning_trades} wins, {losing_trades} losses ({win_rate:.1f}% win rate)")
            print(f"Total profit: {total_profit:.4f} SOL")
            
            # Update the JSON file with the correct statistics
            update_json_stats(user.id, total_trades, winning_trades, losing_trades, total_profit, win_rate)
            
        print("✅ Successfully updated performance statistics!")

def update_json_stats(user_id, total_trades, winning_trades, losing_trades, total_profit, win_rate):
    """Update the yield_data.json file with correct statistics"""
    try:
        data_file = 'yield_data.json'
        
        # Load existing data
        try:
            with open(data_file, 'r') as f:
                yield_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            yield_data = {}
        
        # Create user entry if needed
        user_id_str = str(user_id)
        if user_id_str not in yield_data:
            yield_data[user_id_str] = {
                'balance': 0.0,
                'trades': [],
                'page': 0
            }
        
        # Add statistics if not already present
        if 'stats' not in yield_data[user_id_str]:
            yield_data[user_id_str]['stats'] = {}
        
        # Update statistics
        yield_data[user_id_str]['stats'] = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit
        }
        
        # Update balance to match the statistics
        yield_data[user_id_str]['balance'] = total_profit
        
        # Save updated yield_data.json
        with open(data_file, 'w') as f:
            json.dump(yield_data, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Error updating JSON stats: {str(e)}")
        return False

def enhance_dashboard_function():
    """Update the dashboard function to display wins and losses properly"""
    try:
        # Path to the bot file
        bot_file = 'bot_v20_runner.py'
        
        # Read the file
        with open(bot_file, 'r') as f:
            content = f.read()
        
        # Find the dashboard command function
        dashboard_start = content.find("def dashboard_command(update, chat_id):")
        if dashboard_start == -1:
            print("Could not find dashboard_command function")
            return False
        
        # Look for the ROI metrics function
        metrics_start = content.find("def get_user_roi_metrics(user_id):", dashboard_start)
        if metrics_start == -1:
            print("Could not find get_user_roi_metrics function")
            return False
        
        # Update the ROI metrics function to include wins and losses
        old_metrics_code = """def get_user_roi_metrics(user_id):
                \"\"\"Get ROI metrics for a user - simplified implementation\"\"\"
                import json
                import os
                
                # Load yield data from JSON file
                data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yield_data.json')
                try:
                    with open(data_path, 'r') as f:
                        yield_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    yield_data = {}
                
                user_id_str = str(user_id)
                if user_id_str not in yield_data:
                    return {
                        'roi_percentage': 0,
                        'trades_count': 0,
                        'profit_amount': 0
                    }
                
                user_data = yield_data[user_id_str]
                trades = user_data.get('trades', [])
                
                # Calculate ROI metrics
                profit_amount = user_data.get('balance', 0)
                trades_count = len(trades)
                
                # Some default values for new users
                roi_percentage = 0
                if trades_count > 0:
                    # Calculate average ROI percentage across all trades
                    total_roi = sum(trade.get('yield', 0) for trade in trades)
                    roi_percentage = total_roi / trades_count if trades_count > 0 else 0
                
                return {
                    'roi_percentage': roi_percentage,
                    'trades_count': trades_count,
                    'profit_amount': profit_amount
                }"""
        
        new_metrics_code = """def get_user_roi_metrics(user_id):
                \"\"\"Get ROI metrics for a user - enhanced implementation with wins/losses\"\"\"
                import json
                import os
                
                # Load yield data from JSON file
                data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yield_data.json')
                try:
                    with open(data_path, 'r') as f:
                        yield_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    yield_data = {}
                
                user_id_str = str(user_id)
                if user_id_str not in yield_data:
                    return {
                        'roi_percentage': 0,
                        'trades_count': 0,
                        'profit_amount': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'win_rate': 0
                    }
                
                user_data = yield_data[user_id_str]
                trades = user_data.get('trades', [])
                
                # Get statistics from JSON if available
                stats = user_data.get('stats', {})
                if stats:
                    return {
                        'roi_percentage': stats.get('win_rate', 0),
                        'trades_count': stats.get('total_trades', len(trades)),
                        'profit_amount': stats.get('total_profit', user_data.get('balance', 0)),
                        'winning_trades': stats.get('winning_trades', 0),
                        'losing_trades': stats.get('losing_trades', 0),
                        'win_rate': stats.get('win_rate', 0)
                    }
                
                # Calculate ROI metrics if stats not available
                profit_amount = user_data.get('balance', 0)
                trades_count = len(trades)
                
                # Count winning and losing trades
                winning_trades = 0
                losing_trades = 0
                for trade in trades:
                    if trade.get('yield', 0) > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
                        
                # Calculate win rate
                win_rate = (winning_trades / trades_count) * 100 if trades_count > 0 else 0
                
                # Some default values for new users
                roi_percentage = 0
                if trades_count > 0:
                    # Calculate average ROI percentage across all trades
                    total_roi = sum(trade.get('yield', 0) for trade in trades)
                    roi_percentage = total_roi / trades_count if trades_count > 0 else 0
                
                return {
                    'roi_percentage': roi_percentage,
                    'trades_count': trades_count,
                    'profit_amount': profit_amount,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate
                }"""
        
        # Replace the ROI metrics function
        if old_metrics_code in content:
            updated_content = content.replace(old_metrics_code, new_metrics_code)
            
            # Now update the dashboard display to show wins and losses
            dashboard_code = """            # Create dashboard message
            metrics = get_user_roi_metrics(user.id)
            
            dashboard_message = (
                "📊 *Trading Dashboard*\n\n"
                f"• *Balance:* {user.balance:.2f} SOL\n"
                f"• *ROI:* {metrics['roi_percentage']:.2f}%\n"
                f"• *Total Profit:* {metrics['profit_amount']:.2f} SOL\n"
                f"• *Trades:* {metrics['trades_count']}\n\n"
            )"""
            
            enhanced_dashboard = """            # Create dashboard message
            metrics = get_user_roi_metrics(user.id)
            
            dashboard_message = (
                "📊 *Trading Dashboard*\n\n"
                f"• *Balance:* {user.balance:.2f} SOL\n"
                f"• *Win Rate:* {metrics['win_rate']:.1f}%\n"
                f"• *Trades:* {metrics['trades_count']} (✅{metrics['winning_trades']} | ❌{metrics['losing_trades']})\n"
                f"• *Total Profit:* {metrics['profit_amount']:.2f} SOL\n\n"
            )"""
            
            # Replace the dashboard code
            if dashboard_code in updated_content:
                final_content = updated_content.replace(dashboard_code, enhanced_dashboard)
                
                # Write the updated file
                with open(bot_file, 'w') as f:
                    f.write(final_content)
                    
                print("✅ Successfully enhanced dashboard to display wins and losses")
                return True
            else:
                print("Could not find dashboard message code to update")
                return False
        else:
            print("Could not find ROI metrics function to update")
            return False
            
    except Exception as e:
        print(f"Error enhancing dashboard function: {str(e)}")
        return False

if __name__ == "__main__":
    main()
    enhance_dashboard_function()