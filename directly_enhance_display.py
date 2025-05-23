"""
Direct Enhancement Script - Update trade history display and performance page
This script directly modifies the bot file to apply our enhancements
"""
import os
import sys
import json

def main():
    """
    Directly enhance the trade history display and performance page
    """
    print("🔄 Directly enhancing trade history display and performance page...")
    
    # Path to the bot file
    bot_file = 'bot_v20_runner.py'
    
    # Read the file
    with open(bot_file, 'r') as f:
        content = f.read()
    
    # 1. Replace the trade display code in trade_history_display_handler
    old_trade_display = """                            # Add trade details
                            history_message += f"<b>{position.token_name}</b> {pl_emoji} {pl_percentage:.1f}%\\n"
                            history_message += f"Amount: {position.amount:.6f} SOL\\n"
                            history_message += f"Entry: ${position.entry_price:.6f}\\n"
                            history_message += f"Exit: ${position.current_price:.6f}\\n"
                            history_message += f"P/L: {pl_amount:.6f} SOL\\n"
                            history_message += f"Date: {date_str}\\n\\n"""
    
    new_trade_display = """                            # Get trade type if it exists
                            trade_type = "Scalp"
                            if hasattr(position, 'trade_type') and position.trade_type:
                                trade_type = position.trade_type
                            
                            # Add trade details with enhanced formatting
                            history_message += f"🪙 <b>{position.token_name}</b> {pl_emoji} <b>{pl_percentage:.1f}%</b>\\n"
                            history_message += f"<i>Strategy: {trade_type} Trade</i>\\n"
                            history_message += f"💰 Amount: {position.amount:.4f} SOL\\n"
                            history_message += f"📥 Entry: <b>${position.entry_price:.6f}</b>\\n"
                            history_message += f"📤 Exit: <b>${position.current_price:.6f}</b>\\n"
                            
                            # Format profit/loss with color indicators
                            if pl_amount > 0:
                                history_message += f"✅ Profit: +{pl_amount:.4f} SOL\\n"
                            else:
                                history_message += f"❌ Loss: {pl_amount:.4f} SOL\\n"
                                
                            history_message += f"🕒 Executed: {date_str}\\n"
                            history_message += f"───────────────────\\n\\n"""
    
    # Replace the trade display
    updated_content = content.replace(old_trade_display, new_trade_display)
    
    # 2. Update the dashboard_command function to show wins/losses
    dashboard_start = updated_content.find("def dashboard_command(update, chat_id):")
    if dashboard_start == -1:
        print("Could not find dashboard_command function")
        return False
    
    # Locate the dashboard message construction
    dashboard_message_start = updated_content.find("dashboard_message = (", dashboard_start)
    if dashboard_message_start == -1:
        print("Could not find dashboard message construction")
        return False
    
    dashboard_message_end = updated_content.find(")", dashboard_message_start)
    if dashboard_message_end == -1:
        print("Could not find end of dashboard message")
        return False
    
    # Extract the current dashboard message
    old_dashboard_message = updated_content[dashboard_message_start:dashboard_message_end+1]
    
    # Create a new dashboard message with wins/losses
    new_dashboard_message = """dashboard_message = (
                "📊 *Trading Dashboard*\\n\\n"
                f"• *Balance:* {user.balance:.2f} SOL\\n"
                f"• *Trades:* {metrics['trades_count']}\\n"
                f"• *Win Rate:* {winning_rate:.1f}% (✅ {winning_trades} | ❌ {losing_trades})\\n"
                f"• *Total Profit:* {metrics['profit_amount']:.2f} SOL\\n\\n"
            )"""
    
    # Replace the dashboard message
    if old_dashboard_message in updated_content:
        updated_content = updated_content.replace(old_dashboard_message, new_dashboard_message)
    
    # 3. Insert code to calculate wins/losses before the dashboard message
    win_loss_code = """            # Calculate wins and losses
            winning_trades = 0
            losing_trades = 0
            
            # Get trade statistics from database
            with app.app_context():
                from models import TradingPosition
                
                # Get closed trades for this user
                trades = TradingPosition.query.filter_by(
                    user_id=user.id,
                    status='closed'
                ).all()
                
                # Count wins and losses
                for trade in trades:
                    pl_amount = (trade.current_price - trade.entry_price) * trade.amount
                    if pl_amount > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
            
            # Calculate win rate
            winning_rate = (winning_trades / metrics['trades_count']) * 100 if metrics['trades_count'] > 0 else 0
            
"""
    
    # Find the right location to insert the win/loss calculation code
    insert_location = updated_content.find("            # Create dashboard message", dashboard_start)
    if insert_location == -1:
        print("Could not find location to insert win/loss calculation code")
        return False
    
    # Insert the win/loss calculation code
    final_content = updated_content[:insert_location] + win_loss_code + updated_content[insert_location:]
    
    # Write the updated file
    with open(bot_file, 'w') as f:
        f.write(final_content)
    
    print("✅ Successfully enhanced trade history display and performance page!")
    
    # Create sample trades for testing
    create_sample_trade()
    
    return True

def create_sample_trade():
    """Create a sample trade to verify our enhancements"""
    try:
        # Set up paths
        sys.path.append('.')
        
        # Import necessary modules
        from main import app
        
        with app.app_context():
            from models import db, User, TradingPosition
            from datetime import datetime
            from sqlalchemy import text
            
            # Find the first user
            user = User.query.first()
            if not user:
                print("No users found")
                return
            
            # Create a sample trade
            new_trade = TradingPosition(
                user_id=user.id,
                token_name="WIF",
                amount=20.0,
                entry_price=0.0025,
                current_price=0.0032,
                timestamp=datetime.utcnow(),
                status="closed"
            )
            
            db.session.add(new_trade)
            db.session.flush()
            
            # Add trade type using raw SQL
            db.session.execute(text(f"UPDATE trading_position SET trade_type = 'Snipe' WHERE id = {new_trade.id}"))
            db.session.commit()
            
            print(f"✅ Created sample WIF trade for user {user.id} with Snipe trade type")
            
            # Also update yield_data.json
            update_yield_data(user.id)
            
    except Exception as e:
        print(f"Error creating sample trade: {str(e)}")

def update_yield_data(user_id):
    """Update yield_data.json with trade statistics"""
    try:
        data_file = 'yield_data.json'
        
        # Load existing data
        try:
            with open(data_file, 'r') as f:
                yield_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            yield_data = {}
        
        # Import necessary modules
        sys.path.append('.')
        from main import app
        
        with app.app_context():
            from models import TradingPosition
            
            # Get user's trades
            trades = TradingPosition.query.filter_by(
                user_id=user_id,
                status='closed'
            ).all()
            
            # Count wins and losses
            winning_trades = 0
            losing_trades = 0
            total_profit = 0
            
            for trade in trades:
                pl_amount = (trade.current_price - trade.entry_price) * trade.amount
                total_profit += pl_amount
                
                if pl_amount > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
            
            # Calculate win rate
            total_trades = len(trades)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # Update user stats in yield_data.json
            user_id_str = str(user_id)
            if user_id_str not in yield_data:
                yield_data[user_id_str] = {
                    'balance': 0.0,
                    'trades': [],
                    'page': 0
                }
            
            # Add stats field if not present
            if 'stats' not in yield_data[user_id_str]:
                yield_data[user_id_str]['stats'] = {}
            
            # Update stats
            yield_data[user_id_str]['stats'] = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_profit': total_profit
            }
            
            # Save updated file
            with open(data_file, 'w') as f:
                json.dump(yield_data, f, indent=2)
                
            print(f"✅ Updated yield_data.json with stats for user {user_id}")
            
    except Exception as e:
        print(f"Error updating yield_data.json: {str(e)}")

if __name__ == "__main__":
    main()