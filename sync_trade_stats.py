"""
Synchronize Trade Statistics with Trade History Display
This script ensures that the performance page statistics match the trade history display
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Synchronize trade statistics with trade history display"""
    print("🔄 Syncing trade statistics with trade history...")
    
    # Set up paths
    sys.path.append('.')
    
    # Import necessary modules
    from main import app
    
    with app.app_context():
        # Import models
        from models import db, User, TradingPosition, Profit
        
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
            
            for trade in trades:
                # Calculate profit/loss for this trade
                pl_amount = (trade.current_price - trade.entry_price) * trade.amount
                
                # Update stats
                total_profit += pl_amount
                if pl_amount > 0:
                    winning_trades += 1
            
            # Update user's balance if needed to reflect total profit
            if total_trades > 0:
                # Calculate win rate
                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                
                print(f"User {user.id}: {total_trades} trades, {winning_trades} winning trades ({win_rate:.1f}% win rate)")
                print(f"Total profit: {total_profit:.4f} SOL")
                
                # Update the user's profit records
                today = datetime.utcnow().date()
                
                # Check if there are profit records for today
                existing_profit = Profit.query.filter_by(
                    user_id=user.id,
                    date=today
                ).first()
                
                if not existing_profit:
                    # Create a new profit record
                    profit_percentage = (total_profit / user.balance) * 100 if user.balance > 0 else 0
                    new_profit = Profit(
                        user_id=user.id,
                        amount=total_profit,
                        percentage=profit_percentage,
                        date=today
                    )
                    db.session.add(new_profit)
                
                # Also update the yield_data.json file to ensure consistency
                sync_with_yield_data(user.id, trades)
                
        # Commit all changes
        db.session.commit()
        print("✅ Successfully synchronized trade statistics with trade history!")

def sync_with_yield_data(user_id, trades):
    """Sync the database trades with yield_data.json"""
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
            
        # Calculate total profit from trades
        total_profit = 0
        for trade in trades:
            pl_amount = (trade.current_price - trade.entry_price) * trade.amount
            total_profit += pl_amount
            
        # Update user's balance in yield_data.json
        yield_data[user_id_str]['balance'] = total_profit
        
        # Ensure all trades are in yield_data.json
        json_trades = yield_data[user_id_str]['trades']
        db_trade_ids = set()
        
        for trade in trades:
            # Generate a unique ID for this trade
            trade_id = f"{trade.token_name}_{trade.entry_price}_{trade.timestamp}"
            db_trade_ids.add(trade_id)
            
            # Check if this trade already exists in the JSON
            found = False
            for json_trade in json_trades:
                # Create a unique ID for the JSON trade to compare
                try:
                    json_timestamp = datetime.fromisoformat(json_trade['timestamp'])
                    json_id = f"{json_trade['name']}_{json_trade['entry']}_{json_timestamp}"
                    if json_id == trade_id:
                        found = True
                        break
                except:
                    # If there's a parsing error, skip this check
                    pass
            
            # If not found, add it
            if not found:
                yield_percentage = ((trade.current_price / trade.entry_price) - 1) * 100 if trade.entry_price > 0 else 0
                
                new_trade = {
                    'name': trade.token_name,
                    'symbol': trade.token_name,
                    'mint': f"tx_{int(trade.timestamp.timestamp())}",
                    'entry': trade.entry_price,
                    'exit': trade.current_price,
                    'yield': yield_percentage,
                    'timestamp': trade.timestamp.isoformat()
                }
                
                json_trades.insert(0, new_trade)
                
        # Save updated yield_data.json
        with open(data_file, 'w') as f:
            json.dump(yield_data, f, indent=2)
            
        return True
    except Exception as e:
        logger.error(f"Error syncing with yield_data.json: {str(e)}")
        return False

if __name__ == "__main__":
    main()