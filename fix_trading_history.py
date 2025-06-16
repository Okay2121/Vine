#!/usr/bin/env python
"""
Fix Trading History Display
This script fixes the error with displaying trading history in the bot
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_trading_history_handler():
    """Fix the trading_history_handler in bot_v20_runner.py"""
    try:
        # Check if bot_v20_runner.py exists
        if not os.path.exists('bot_v20_runner.py'):
            logger.error("❌ bot_v20_runner.py not found")
            return False
        
        # Read the file
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # Find the trading_history_handler function
        start_idx = content.find("def trading_history_handler(update, chat_id):")
        if start_idx == -1:
            logger.error("❌ Could not find trading_history_handler function")
            return False
        
        # Find the end of the function
        next_func_idx = content.find("def ", start_idx + 10)
        if next_func_idx == -1:
            logger.error("❌ Could not find the end of trading_history_handler function")
            return False
        
        # Extract the function
        old_function = content[start_idx:next_func_idx]
        
        # Create a fixed version of the function
        fixed_function = """def trading_history_handler(update, chat_id):
    \"\"\"Handle the request to view trading history.\"\"\"
    # Import needed modules to avoid unbound errors
    import os
    import json
    import logging
    import traceback
    from datetime import datetime, timedelta
    
    try:
        user_id = update['callback_query']['from']['id']
        with app.app_context():
            # Get user from database
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                bot.send_message(chat_id, "⚠️ User not found in database.")
                return
            
            # Get today's date for filtering trades
            today_date = datetime.now().date()
            
            # Get all trades for today
            trades_today = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type.in_(['buy', 'sell']),
                Transaction.timestamp >= datetime.combine(today_date, datetime.min.time())
            ).all()
            
            # Get trading stats from yield_data.json instead of just today's trades
            profitable_trades = 0
            loss_trades = 0
            
            # Try to get stats from yield_data.json file first
            try:
                # Try multiple possible locations for yield_data.json
                possible_paths = ['yield_data.json', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yield_data.json')]
                
                yield_data_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        yield_data_path = path
                        break
                
                if yield_data_path and os.path.exists(yield_data_path):
                    with open(yield_data_path, 'r') as f:
                        yield_data = json.load(f)
                    
                    user_id_str = str(user.id)
                    if user_id_str in yield_data:
                        user_data = yield_data[user_id_str]
                        # Get wins and losses from yield_data
                        profitable_trades = user_data.get('wins', 0)
                        loss_trades = user_data.get('losses', 0)
                        logger.info(f"Got stats from yield_data.json: {profitable_trades} wins, {loss_trades} losses")
                        
            except Exception as e:
                logger.error(f"Error reading yield_data.json: {e}")
                
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
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Build a visually stunning and user-friendly performance dashboard
            performance_message = "🚀 *PERFORMANCE DASHBOARD* 🚀\\n\\n"
            
            # Balance section - highlight the important numbers
            performance_message += "💰 *BALANCE*\\n"
            performance_message += f"Initial: {user.initial_deposit:.2f} SOL\\n"
            performance_message += f"Current: {user.balance:.2f} SOL\\n"
            
            # Get total profit
            total_profit_amount = user.balance - user.initial_deposit
            total_profit_percentage = (total_profit_amount / user.initial_deposit * 100) if user.initial_deposit > 0 else 0
            
            performance_message += f"Profit: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)\\n\\n"
            
            # Get today's profit data
            today_profit = Profit.query.filter_by(user_id=user.id, date=today_date).first()
            today_profit_amount = today_profit.amount if today_profit else 0
            today_profit_percentage = today_profit.percentage if today_profit else 0
            
            # Today's profit - emphasized and eye-catching
            performance_message += "📈 *TODAY'S PERFORMANCE*\\n"
            if today_profit_amount > 0:
                performance_message += f"Profit: +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)\\n\\n"
            else:
                yesterday_balance = user.balance - today_profit_amount
                performance_message += "No profit recorded yet today\\n"
                performance_message += f"Starting: {yesterday_balance:.2f} SOL\\n\\n"
            
            # Calculate current streak
            streak = 0
            current_date = datetime.utcnow().date()
            while True:
                profit = Profit.query.filter_by(user_id=user.id, date=current_date).first()
                if profit and profit.amount > 0:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break
            
            # Profit streak - motivational and prominent
            performance_message += "🔥 *WINNING STREAK*\\n"
            if streak > 0:
                streak_emoji = "🔥" if streak >= 3 else "✨"
                performance_message += f"{streak_emoji} {streak} day{'s' if streak > 1 else ''} in a row!\\n"
                if streak >= 5:
                    performance_message += "Incredible winning streak! Keep it up! 🏆\\n\\n"
                else:
                    performance_message += "You're on fire! Keep building momentum! 💪\\n\\n"
            else:
                performance_message += "Start your streak today with your first profit!\\n\\n"
            
            # Trading stats - enhanced with more detailed information
            performance_message += "📊 *TRADING STATS*\\n"
            performance_message += f"✅ Wins: {profitable_trades}\\n"
            performance_message += f"❌ Losses: {loss_trades}\\n"
            
            if total_trades > 0:
                performance_message += f"Win rate: {win_rate:.1f}%\\n"
                performance_message += f"Total trades: {total_trades}\\n\\n"
                
                # Provide specific performance feedback based on win rate
                if win_rate >= 75:
                    performance_message += "Exceptional trading! Your strategy is outperforming the market! 🔥📈\\n"
                elif win_rate >= 50:
                    performance_message += "Your auto-trading strategy is profitable! 📈\\n"
                elif win_rate >= 30:
                    performance_message += "Market conditions are challenging, but the bot is adapting. 🔄\\n"
                else:
                    performance_message += "Volatile market. The bot is adjusting strategy to find better opportunities. 📊\\n"
            else:
                performance_message += "No trades completed yet. The bot is waiting for optimal market conditions. ⏳\\n"
            
            # Create proper keyboard with transaction history button but no trade history button
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💲 Deposit More", "callback_data": "deposit"},
                    {"text": "💰 Withdraw", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "📜 Transaction History", "callback_data": "transaction_history"}
                ],
                [
                    {"text": "🔙 Back to Dashboard", "callback_data": "dashboard"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                performance_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        logger.error(f"Error in trading_history_handler: {e}")
        logger.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying performance data: {str(e)}")

"""
        
        # Replace the old function with the fixed one
        new_content = content.replace(old_function, fixed_function)
        
        # Write the fixed content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(new_content)
        
        logger.info("✅ Successfully fixed trading_history_handler function")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing trading_history_handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Fixing trading history handler...")
    if fix_trading_history_handler():
        logger.info("✅ Trading history handler fixed successfully!")
        logger.info("Restart the bot for changes to take effect")
    else:
        logger.error("❌ Failed to fix trading history handler")