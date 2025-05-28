"""
Quick Fix for Realistic Trade Broadcast Amounts
===============================================
This directly patches the bot's trade broadcast to show realistic spending amounts
"""

def apply_realistic_fix():
    """Apply the realistic spending fix to bot_v20_runner.py"""
    
    # Read the current bot file
    with open('bot_v20_runner.py', 'r') as f:
        content = f.read()
    
    # The problematic code that creates unrealistic amounts
    old_code = '''                        # Create trading position that shows immediately in Position feed
                        position = TradingPosition(
                            user_id=user.id,
                            token_name=token_name,
                            amount=realistic_amount,  # Use realistic amount based on user's balance
                            entry_price=entry_price,
                            current_price=entry_price,
                            timestamp=datetime.utcnow(),
                            status='open',
                            trade_type='buy'
                        )'''
    
    # Better realistic code
    new_code = '''                        # Deduct the realistic amount from user's balance
                        user.balance -= spent_sol
                        
                        # Create trading position that shows realistic amounts in Position feed
                        position = TradingPosition(
                            user_id=user.id,
                            token_name=token_name,
                            amount=realistic_amount,  # Use realistic amount based on user's balance
                            entry_price=entry_price,
                            current_price=entry_price,
                            timestamp=datetime.utcnow(),
                            status='open',
                            trade_type='buy'
                        )
                        
                        # Create transaction record showing realistic spending
                        transaction = Transaction(
                            user_id=user.id,
                            transaction_type='buy',
                            amount=-spent_sol,  # Negative because it's spent
                            token_name=token_name,
                            timestamp=datetime.utcnow(),
                            status='completed',
                            notes=f'Buy {realistic_amount:,} {token_name} @ {entry_price:.8f} ({risk_percent:.1f}% risk)',
                            tx_hash=f"{tx_link}_user_{user.id}"
                        )
                        db.session.add(transaction)'''
    
    # Replace the code
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Write back to file
        with open('bot_v20_runner.py', 'w') as f:
            f.write(content)
        
        print("✅ Applied realistic spending fix to bot_v20_runner.py")
        return True
    else:
        print("❌ Could not find the exact code to replace")
        return False

def restart_bot():
    """Restart the bot to apply changes"""
    import os
    print("🔄 Restarting bot to apply realistic spending fix...")
    # The workflow will automatically restart the bot

if __name__ == "__main__":
    print("🚀 Applying Quick Fix for Realistic Trade Amounts")
    print("=" * 50)
    
    if apply_realistic_fix():
        print("✅ Fix applied successfully!")
        print("The trade broadcasts will now show realistic spending amounts.")
        restart_bot()
    else:
        print("❌ Fix could not be applied automatically.")
        print("Manual intervention may be required.")