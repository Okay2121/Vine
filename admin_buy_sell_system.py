"""
New BUY/SELL Trade System for Admin
Implements automatic profit calculation with entry/exit price matching
"""

import json
import os
from datetime import datetime
from app import app, db


def process_buy_trade(user_id, token_name, entry_price, tx_hash, bot, chat_id):
    """Process a BUY trade and store it for future SELL matching."""
    try:
        with app.app_context():
            from models import User
            
            # Find the user
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                bot.send_message(chat_id, f"⚠️ User with ID {user_id} not found.")
                return
            
            # Store pending BUY in JSON file for matching
            pending_trades_file = 'pending_trades.json'
            try:
                with open(pending_trades_file, 'r') as f:
                    pending_trades = json.load(f)
            except FileNotFoundError:
                pending_trades = {}
            
            user_id_str = str(user.id)
            if user_id_str not in pending_trades:
                pending_trades[user_id_str] = []
            
            # Add new BUY trade
            buy_trade = {
                'token_name': token_name.replace('$', ''),
                'entry_price': entry_price,
                'tx_hash': tx_hash,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'pending'
            }
            
            pending_trades[user_id_str].append(buy_trade)
            
            # Save back to file
            with open(pending_trades_file, 'w') as f:
                json.dump(pending_trades, f, indent=2)
            
            # Send trade signal to user
            trade_message = (
                f"📈 *TRADE SIGNAL - BUY*\n\n"
                f"• Token: {token_name}\n"
                f"• Entry Price: {entry_price} SOL\n"
                f"• Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n"
                f"• Type: BUY\n\n"
                f"🔍 Transaction: `{tx_hash}`"
            )
            
            bot.send_message(user.telegram_id, trade_message, parse_mode="Markdown")
            bot.send_message(chat_id, f"✅ BUY trade posted to user {user_id}")
            
    except Exception as e:
        import logging
        logging.error(f"Error processing BUY trade: {e}")
        bot.send_message(chat_id, f"⚠️ Error processing BUY trade: {str(e)}")


def process_sell_trade(user_id, token_name, sell_price, tx_hash, bot, chat_id):
    """Process a SELL trade and match with pending BUY for profit calculation."""
    try:
        with app.app_context():
            from models import User, Transaction, Profit
            
            # Find the user
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                bot.send_message(chat_id, f"⚠️ User with ID {user_id} not found.")
                return
            
            # Find pending BUY trade
            pending_trades_file = 'pending_trades.json'
            try:
                with open(pending_trades_file, 'r') as f:
                    pending_trades = json.load(f)
            except FileNotFoundError:
                bot.send_message(chat_id, f"⚠️ No pending BUY trades found")
                return
            
            user_id_str = str(user.id)
            if user_id_str not in pending_trades:
                bot.send_message(chat_id, f"⚠️ No pending BUY trades for user {user_id}")
                return
            
            # Find matching BUY trade for this token (most recent pending)
            buy_trade = None
            token_clean = token_name.replace('$', '')
            
            for i in reversed(range(len(pending_trades[user_id_str]))):
                trade = pending_trades[user_id_str][i]
                if trade['token_name'] == token_clean and trade['status'] == 'pending':
                    buy_trade = trade
                    # Mark as matched
                    pending_trades[user_id_str][i]['status'] = 'matched'
                    break
            
            if not buy_trade:
                bot.send_message(chat_id, f"⚠️ No pending BUY order found for {token_name}")
                return
            
            # Calculate profit/loss automatically
            entry_price = buy_trade['entry_price']
            roi_percentage = ((sell_price - entry_price) / entry_price) * 100
            
            # Calculate profit amount (using 1 SOL allocation per trade)
            trade_allocation = 1.0
            profit_amount = (sell_price - entry_price) * (trade_allocation / entry_price)
            
            # Update user balance
            user.balance += profit_amount
            
            # Create transaction record
            transaction = Transaction(
                user_id=user.id,
                transaction_type="trade_profit" if profit_amount > 0 else "trade_loss",
                amount=abs(profit_amount),
                token_name=token_clean,
                timestamp=datetime.utcnow(),
                status="completed",
                notes=f"Trade: {token_name} entry {entry_price}, exit {sell_price}",
                tx_hash=tx_hash
            )
            db.session.add(transaction)
            
            # Create profit record
            profit_record = Profit(
                user_id=user.id,
                amount=profit_amount,
                percentage=roi_percentage,
                date=datetime.utcnow().date()
            )
            db.session.add(profit_record)
            
            db.session.commit()
            
            # Save updated pending trades
            with open(pending_trades_file, 'w') as f:
                json.dump(pending_trades, f, indent=2)
            
            # Add to yield data for trade history
            from bot_v20_runner import add_trade_to_history
            add_trade_to_history(
                user_id=user.id,
                token_name=token_name,
                entry_price=entry_price,
                exit_price=sell_price,
                profit_amount=profit_amount,
                tx_hash=tx_hash
            )
            
            # Send trade signal to user
            profit_emoji = "🟢" if profit_amount > 0 else "🔴"
            trade_message = (
                f"📉 *TRADE SIGNAL - SELL*\n\n"
                f"• Token: {token_name}\n"
                f"• Sell Price: {sell_price} SOL\n"
                f"• Entry Price: {entry_price} SOL\n"
                f"• ROI: {profit_emoji} {roi_percentage:.2f}%\n"
                f"• Profit: {profit_amount:+.4f} SOL\n"
                f"• Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n"
                f"• Type: SELL\n\n"
                f"🔍 Transaction: `{tx_hash}`"
            )
            
            bot.send_message(user.telegram_id, trade_message, parse_mode="Markdown")
            bot.send_message(chat_id, f"✅ SELL trade processed. ROI: {roi_percentage:.2f}%")
            
    except Exception as e:
        import logging
        logging.error(f"Error processing SELL trade: {e}")
        bot.send_message(chat_id, f"⚠️ Error processing SELL trade: {str(e)}")


def admin_buy_handler(update, chat_id, bot):
    """Handle /admin_buy command"""
    try:
        from bot_v20_runner import is_admin
        
        # Check for admin privileges
        if not is_admin(update['message']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return
        
        # Parse parameters
        text_parts = update['message']['text'].split()
        if len(text_parts) < 5:
            instructions = (
                "📈 *BUY Trade Format*\n\n"
                "`/admin_buy [UserID] $TOKEN [EntryPrice] [TxHash]`\n\n"
                "**Example:**\n"
                "`/admin_buy 123456789 $ZING 0.0051 0xabc123`\n\n"
                "This will store a pending BUY order for future SELL matching."
            )
            bot.send_message(chat_id, instructions, parse_mode="Markdown")
            return
        
        user_id = text_parts[1]
        token_name = text_parts[2]
        entry_price = float(text_parts[3])
        tx_hash = text_parts[4]
        
        process_buy_trade(user_id, token_name, entry_price, tx_hash, bot, chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_buy_handler: {e}")
        bot.send_message(chat_id, f"⚠️ Error processing BUY command: {str(e)}")


def admin_sell_handler(update, chat_id, bot):
    """Handle /admin_sell command"""
    try:
        from bot_v20_runner import is_admin
        
        # Check for admin privileges
        if not is_admin(update['message']['from']['id']):
            bot.send_message(chat_id, "⚠️ You don't have permission to use this feature.")
            return
        
        # Parse parameters
        text_parts = update['message']['text'].split()
        if len(text_parts) < 5:
            instructions = (
                "📉 *SELL Trade Format*\n\n"
                "`/admin_sell [UserID] $TOKEN [SellPrice] [TxHash]`\n\n"
                "**Example:**\n"
                "`/admin_sell 123456789 $ZING 0.0057 0xdef456`\n\n"
                "This will match with the most recent BUY order and calculate profit automatically."
            )
            bot.send_message(chat_id, instructions, parse_mode="Markdown")
            return
        
        user_id = text_parts[1]
        token_name = text_parts[2]
        sell_price = float(text_parts[3])
        tx_hash = text_parts[4]
        
        process_sell_trade(user_id, token_name, sell_price, tx_hash, bot, chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_sell_handler: {e}")
        bot.send_message(chat_id, f"⚠️ Error processing SELL command: {str(e)}")