"""
Bot Smart Trade Integration - Replaces Simple Trade Broadcasting
================================================================
This integrates the smart balance allocation directly into your bot_v20_runner.py
to make admin trade commands trigger personalized, balance-based allocations.

When you send: "Buy $ZING 0.004107 812345 https://solscan.io/tx/abc123"
Each user gets a unique trade amount based on their balance!
"""

import re
import logging
from smart_balance_allocator import process_smart_buy_broadcast, process_smart_sell_broadcast

def integrate_smart_trades_into_bot():
    """
    Add smart trade handling to the bot's message processing
    """
    
    # This code should be added to your bot_v20_runner.py file
    integration_code = '''
# Add this import at the top of bot_v20_runner.py
from smart_balance_allocator import process_smart_buy_broadcast, process_smart_sell_broadcast
import re

def handle_admin_smart_trade_message(message_text, chat_id):
    """
    Handle admin trade messages with smart balance allocation
    Format: Buy $TOKEN PRICE AMOUNT TX_LINK or Sell $TOKEN PRICE AMOUNT TX_LINK
    """
    try:
        # Check if this looks like a trade command
        if not any(word in message_text.lower() for word in ['buy', 'sell']):
            return False
            
        if not '$' in message_text:
            return False
        
        # Parse the trade command
        pattern = r'(Buy|Sell)\s+\$(\w+)\s+([\d.]+)\s+([\d.]+)\s+(https?://[^\s]+|[\w]+)'
        match = re.match(pattern, message_text.strip(), re.IGNORECASE)
        
        if not match:
            # Send format help if parsing failed
            help_message = (
                "❌ Invalid trade format!\n\n"
                "Use: `Buy $TOKEN PRICE AMOUNT TX_LINK`\n"
                "Example: `Buy $ZING 0.004107 812345 https://solscan.io/tx/abc123`"
            )
            bot.send_message(chat_id, help_message, parse_mode="Markdown")
            return True
        
        trade_type = match.group(1).lower()
        token_symbol = match.group(2).upper()
        price = float(match.group(3))
        amount = float(match.group(4))
        tx_link = match.group(5)
        
        # Create solscan link if just hash provided
        if not tx_link.startswith('http'):
            tx_link = f"https://solscan.io/tx/{tx_link}"
        
        # Send processing message
        processing_msg = bot.send_message(
            chat_id, 
            f"🔄 Processing {trade_type.upper()} with Smart Allocation for ${token_symbol}..."
        )
        
        # Process the trade with smart allocation
        if trade_type == 'buy':
            success, message, affected_count, summary = process_smart_buy_broadcast(
                token_symbol=token_symbol,
                entry_price=price,
                admin_amount=amount,
                tx_link=tx_link,
                target_users="active"
            )
        else:  # sell
            success, message, affected_count, summary = process_smart_sell_broadcast(
                token_symbol=token_symbol,
                exit_price=price,
                admin_amount=amount,
                tx_link=tx_link,
                target_users="active"
            )
        
        # Delete processing message
        try:
            bot.delete_message(chat_id, processing_msg['message_id'])
        except:
            pass
        
        # Send result
        if success:
            result_message = (
                f"✅ **Smart Trade Broadcast Complete**\n\n"
                f"**{trade_type.title()} ${token_symbol}** at {price:.8f}\n"
                f"**Users Affected:** {affected_count}\n\n"
                f"🎯 **Each user got personalized amounts:**\n"
                f"{message}\n\n"
                f"💡 **No two users got identical trades!**"
            )
        else:
            result_message = f"❌ Failed to process trade: {message}"
        
        bot.send_message(chat_id, result_message, parse_mode="Markdown")
        return True
        
    except Exception as e:
        logger.error(f"Error in smart trade handler: {e}")
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
        return True

# Add this to your existing message handler function in bot_v20_runner.py
# (Find the function that processes incoming messages and add this check)

def enhanced_handle_message(update):
    """Enhanced message handler with smart trade support"""
    try:
        message = update.get('message', {})
        chat_id = str(message.get('chat', {}).get('id', ''))
        text = message.get('text', '')
        
        # Check if this is a smart trade command first
        if handle_admin_smart_trade_message(text, chat_id):
            return  # Message was handled
            
        # Continue with your existing message handling...
        # (Rest of your current message handling code)
        
    except Exception as e:
        logger.error(f"Error in enhanced message handler: {e}")
'''
    
    return integration_code

def show_smart_trade_examples():
    """Show examples of how the smart trade system works"""
    examples = [
        {
            "command": "Buy $ZING 0.004107 812345 https://solscan.io/tx/abc123",
            "description": "When you send this admin command, here's what happens:",
            "results": [
                "User A (0.5 SOL balance) → Spends 0.35 SOL, gets 85,000 ZING",
                "User B (2.0 SOL balance) → Spends 1.10 SOL, gets 268,000 ZING", 
                "User C (10 SOL balance) → Spends 2.50 SOL, gets 608,000 ZING",
                "User D (25 SOL balance) → Spends 7.20 SOL, gets 1,750,000 ZING"
            ]
        },
        {
            "command": "Sell $ZING 0.006834 812345 https://solscan.io/tx/def456",
            "description": "When you send this sell command:",
            "results": [
                "User A → Sells 85,000 ZING for 0.58 SOL (+65% profit)",
                "User B → Sells 268,000 ZING for 1.83 SOL (+66% profit)",
                "User C → Sells 608,000 ZING for 4.16 SOL (+66% profit)", 
                "User D → Sells 1,750,000 ZING for 11.96 SOL (+66% profit)"
            ]
        }
    ]
    
    print("🎯 Smart Balance Allocation Examples")
    print("=" * 50)
    
    for example in examples:
        print(f"\n📝 Admin Command:")
        print(f"   {example['command']}")
        print(f"\n{example['description']}")
        for result in example['results']:
            print(f"   • {result}")
        print()

if __name__ == "__main__":
    print("Smart Trade Integration for bot_v20_runner.py")
    print("=" * 50)
    
    integration_code = integrate_smart_trades_into_bot()
    print(integration_code)
    
    print("\n" + "=" * 50)
    show_smart_trade_examples()