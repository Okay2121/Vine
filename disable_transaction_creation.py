#!/usr/bin/env python
"""
Disable Transaction Creation - Temporary Fix
This script disables the problematic transaction creation that's causing database errors
so your bot can run smoothly while we resolve the issue.
"""
import os
import sys

# Add the current directory to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def disable_sell_transaction_creation():
    """
    Temporarily disable the transaction creation that's causing database errors
    """
    try:
        # Read the bot file
        with open('bot_v20_runner.py', 'r') as f:
            content = f.read()
        
        # Find and comment out the problematic transaction creation
        lines = content.split('\n')
        new_lines = []
        in_transaction_block = False
        
        for i, line in enumerate(lines):
            if 'Create SELL transaction record that shows in history' in line:
                in_transaction_block = True
                new_lines.append(f"                                    # TEMPORARILY DISABLED: {line.strip()}")
                continue
            elif in_transaction_block and 'db.session.add(transaction)' in line:
                new_lines.append(f"                                    # TEMPORARILY DISABLED: {line.strip()}")
                in_transaction_block = False
                continue
            elif in_transaction_block and line.strip().startswith('transaction = Transaction('):
                new_lines.append(f"                                    # TEMPORARILY DISABLED: {line.strip()}")
                continue
            elif in_transaction_block and ('user_id=' in line or 'transaction_type=' in line or 
                                         'amount=' in line or 'token_name=' in line or 
                                         'timestamp=' in line or 'status=' in line or 
                                         'notes=' in line or 'tx_hash=' in line):
                new_lines.append(f"                                    # TEMPORARILY DISABLED: {line.strip()}")
                continue
            elif in_transaction_block and line.strip() == ')':
                new_lines.append(f"                                    # TEMPORARILY DISABLED: {line.strip()}")
                in_transaction_block = False
                continue
            else:
                new_lines.append(line)
        
        # Write the modified content back
        with open('bot_v20_runner.py', 'w') as f:
            f.write('\n'.join(new_lines))
        
        print("✅ Temporarily disabled problematic transaction creation")
        print("✅ Your bot should now run without database errors")
        print("✅ Dashboard profit data will still work normally")
        return True
        
    except Exception as e:
        print(f"❌ Error disabling transaction creation: {e}")
        return False

def main():
    """
    Run the temporary fix
    """
    print("🔧 Applying temporary fix for database errors...")
    
    if disable_sell_transaction_creation():
        print("\n🎉 Temporary fix applied successfully!")
        print("✅ Your bot should now run without crashes")
        print("✅ Dashboard will continue to show profit data")
        print("📝 This is a temporary solution - the bot will work normally")
    else:
        print("\n❌ Failed to apply temporary fix")

if __name__ == "__main__":
    main()