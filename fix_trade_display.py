"""
Fix Trade Display - Enhanced visual display for trade history
This script fixes the admin broadcast trade functionality and enhances the trade history display
"""
import sys
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Fix the trade history display and broadcast functionality"""
    try:
        # Set up paths
        sys.path.append('.')
        
        # Import necessary modules
        from main import app
        
        with app.app_context():
            # Import models
            from models import db, TradingPosition, User
            
            # Check if trade_type column exists in TradingPosition table
            try:
                # Try to add the column using raw SQL through db.session
                logger.info("Adding trade_type column to TradingPosition")
                db.session.execute('ALTER TABLE trading_position ADD COLUMN trade_type VARCHAR(50)')
                db.session.commit()
                logger.info("Added trade_type column successfully")
            except Exception as e:
                # Column probably already exists
                logger.info(f"Note: {str(e)}")
                logger.info("Continuing with update...")
        
        # Fix the trade_history_display_handler in bot_v20_runner.py
        bot_file_path = 'bot_v20_runner.py'
        
        with open(bot_file_path, 'r') as f:
            content = f.read()
        
        # Find the trade history display section and replace it
        old_display_code = """                            # Calculate profit/loss
                            pl_amount = (position.current_price - position.entry_price) * position.amount
                            pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                            
                            # Determine emoji based on profit/loss
                            pl_emoji = "📈" if pl_percentage > 0 else "📉"
                            date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                            
                            # Add trade details
                            history_message += f"<b>{position.token_name}</b> {pl_emoji} {pl_percentage:.1f}%\\n"
                            history_message += f"Amount: {position.amount:.6f} SOL\\n"
                            history_message += f"Entry: ${position.entry_price:.6f}\\n"
                            history_message += f"Exit: ${position.current_price:.6f}\\n"
                            history_message += f"P/L: {pl_amount:.6f} SOL\\n"
                            history_message += f"Date: {date_str}\\n\\n"""
        
        new_display_code = """                            # Calculate profit/loss
                            pl_amount = (position.current_price - position.entry_price) * position.amount
                            pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                            
                            # Determine emoji based on profit/loss
                            pl_emoji = "📈" if pl_percentage > 0 else "📉"
                            date_str = position.timestamp.strftime("%b %d, %Y at %H:%M")
                            
                            # Get trade type if it exists, or assign a random one
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
            
        # Replace all occurrences of the old display code
        updated_content = content.replace(old_display_code, new_display_code)
        
        # Also fix the admin broadcast trade functionality
        old_broadcast_code = """                    # Create TradingPosition record to display in trade history
                    from models import TradingPosition
                    
                    # Calculate the token amount - using a safe calculation to avoid division by zero
                    token_amount = 0.0
                    if exit_price != entry_price:
                        token_amount = abs(profit_amount / (exit_price - entry_price))
                    else:
                        # Fallback to a reasonable calculation if prices are the same
                        token_amount = abs(profit_amount / entry_price) if entry_price > 0 else 1.0
                    
                    # Create a completed trading position for the trade
                    trading_position = TradingPosition(
                        user_id=user.id,
                        token_name=token,
                        amount=token_amount,
                        entry_price=entry,
                        current_price=exit_price,
                        timestamp=datetime.utcnow(),
                        status="closed"  # Mark as closed since it's a completed trade
                    )"""
        
        new_broadcast_code = """                    # Create TradingPosition record to display in trade history
                    from models import TradingPosition
                    
                    # Store the entry price in a properly named variable to avoid "name 'entry_price' is not defined" error
                    entry_price = entry
                    
                    # Calculate the token amount - using a safe calculation to avoid division by zero
                    token_amount = 0.0
                    if exit_price != entry_price:
                        token_amount = abs(profit_amount / (exit_price - entry_price))
                    else:
                        # Fallback to a reasonable calculation if prices are the same
                        token_amount = abs(profit_amount / entry_price) if entry_price > 0 else 1.0
                    
                    # Assign trade type if provided, otherwise use a default
                    trade_type_value = trade_type.capitalize() if trade_type else "Scalp"
                    
                    # Create a completed trading position for the trade with trade type
                    position = TradingPosition(
                        user_id=user.id,
                        token_name=token,
                        amount=token_amount,
                        entry_price=entry_price,
                        current_price=exit_price,
                        timestamp=datetime.utcnow(),
                        status="closed"  # Mark as closed since it's a completed trade
                    )
                    db.session.add(position)
                    db.session.flush()  # Get the ID
                    
                    # Update trade_type using raw SQL since the column might be new
                    db.session.execute(f"UPDATE trading_position SET trade_type = '{trade_type_value}' WHERE id = {position.id}")"""
        
        # Replace the broadcast code
        updated_content = updated_content.replace(old_broadcast_code, new_broadcast_code)
        
        # Write the updated file
        with open(bot_file_path, 'w') as f:
            f.write(updated_content)
        
        logger.info("Successfully updated trade display and broadcast functionality")
        return True
    
    except Exception as e:
        logger.error(f"Error fixing trade display: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    main()