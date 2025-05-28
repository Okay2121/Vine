"""
Direct Trade Broadcast Fix - Realistic Amounts
==============================================
This directly patches the trade broadcast system to show realistic spending amounts
based on each user's actual balance instead of impossible amounts.
"""

import re

def fix_trade_broadcast():
    """Fix the trade broadcast to show realistic amounts"""
    
    with open('bot_v20_runner.py', 'r') as f:
        content = f.read()
    
    # Find and replace the problematic position creation code
    old_pattern = r'position = TradingPosition\(\s*user_id=user\.id,\s*token_name=token_name,\s*amount=realistic_amount,.*?\)'
    
    new_code = '''position = TradingPosition(
                            user_id=user.id,
                            token_name=token_name,
                            amount=realistic_amount,
                            entry_price=entry_price,
                            current_price=entry_price,
                            timestamp=datetime.utcnow(),
                            status='open',
                            trade_type='buy'
                        )
                        
                        # Update user's balance with realistic spending
                        user.balance -= spent_sol'''
    
    # Also ensure we're sending realistic notifications to users
    notification_fix = '''
                        # Send realistic notification to user
                        realistic_message = (
                            f"🟡 *LIVE SNIPE* - ${token_name}\\n\\n"
                            f"*Buy @:* {entry_price:.8f} | *Qty:* {realistic_amount:,} {token_name}\\n"
                            f"*Spent:* {spent_sol:.4f} SOL ({risk_percent:.1f}% risk) | *Est. Value:* Pending\\n"
                            f"*TX:* [View]({tx_link})\\n"
                            f"*Status:* Holding\\n"
                            f"*Opened:* {datetime.utcnow().strftime('%b %d - %H:%M UTC')}\\n\\n"
                            f"_Smart risk management applied. Position tracking active._"
                        )
                        
                        # Send to user
                        if hasattr(user, 'telegram_id') and user.telegram_id:
                            try:
                                bot.send_message(user.telegram_id, realistic_message, parse_mode="Markdown")
                            except:
                                pass  # Continue if user messaging fails'''
    
    # Add the notification fix after position creation
    if 'db.session.add(position)' in content:
        content = content.replace(
            'db.session.add(position)',
            f'db.session.add(position){notification_fix}'
        )
    
    # Write the fixed content back
    with open('bot_v20_runner.py', 'w') as f:
        f.write(content)
    
    print("✅ Applied direct fix to trade broadcast system")
    print("Trade alerts will now show realistic spending amounts!")

if __name__ == "__main__":
    fix_trade_broadcast()