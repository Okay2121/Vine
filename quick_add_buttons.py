#!/usr/bin/env python
"""
Quick Add Buttons
This script directly adds the trade history and simulation buttons to your bot.
No READMEs, no popups, just adds the buttons to the menus.
"""

import os

def add_buttons_to_bot_v20_runner():
    """Add buttons directly to bot_v20_runner.py"""
    try:
        # Check if the file exists
        if not os.path.exists('bot_v20_runner.py'):
            print("❌ bot_v20_runner.py not found")
            return False
        
        # Read the file
        with open('bot_v20_runner.py', 'r') as file:
            lines = file.readlines()
        
        # Find the main menu keyboard
        main_menu_start = -1
        main_menu_end = -1
        for i, line in enumerate(lines):
            if 'keyboard = [' in line and 'First row - primary actions' in lines[i+1]:
                main_menu_start = i
            if main_menu_start != -1 and ']' in line and main_menu_end == -1:
                main_menu_end = i
        
        if main_menu_start == -1 or main_menu_end == -1:
            print("❌ Couldn't find main menu keyboard in bot_v20_runner.py")
        else:
            # Add new buttons row before the closing bracket
            new_row = '        # Trade simulation buttons\n        [\n            {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},\n            {"text": "📜 Trade History", "callback_data": "view_trade_history"}\n        ],\n'
            lines[main_menu_end:main_menu_end] = [new_row]
            print("✅ Added buttons to main menu")
        
        # Find the dashboard keyboard
        dashboard_start = -1
        dashboard_end = -1
        for i, line in enumerate(lines):
            if 'keyboard = bot.create_inline_keyboard([' in line:
                dashboard_start = i
            if dashboard_start != -1 and '])' in line and dashboard_end == -1:
                dashboard_end = i
        
        if dashboard_start == -1 or dashboard_end == -1:
            print("❌ Couldn't find dashboard keyboard")
        else:
            # Add new buttons row before the closing bracket
            new_row = '                [\n                    {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},\n                    {"text": "📜 Trade History", "callback_data": "view_trade_history"}\n                ],\n'
            lines[dashboard_end:dashboard_end] = [new_row]
            print("✅ Added buttons to dashboard")
        
        # Find where callback handlers are defined
        callback_handlers_position = -1
        for i, line in enumerate(lines):
            if 'bot.add_callback_handler(' in line and 'referral_earnings' in line:
                callback_handlers_position = i + 1
                break
        
        if callback_handlers_position == -1:
            print("❌ Couldn't find where to add callback handlers")
        else:
            # Add callback handlers
            handlers = '\n    # Trade simulation handlers\n    bot.add_callback_handler("simulate_trade", lambda update, chat_id: bot.send_message(chat_id, "Use /simulate to generate a new trade"))\n    bot.add_callback_handler("view_trade_history", lambda update, chat_id: bot.send_message(chat_id, "Use /history to view your trade history"))\n'
            lines[callback_handlers_position:callback_handlers_position] = [handlers]
            print("✅ Added callback handlers")
        
        # Write the modified content back to file
        with open('bot_v20_runner.py', 'w') as file:
            file.writelines(lines)
        
        # Write integration instructions to a separate file
        with open('integration_instructions.txt', 'w') as file:
            file.write("How to finish integrating the yield module:\n\n")
            file.write("1. Add these lines to your main bot file:\n\n")
            file.write("   from yield_module import setup_yield_module\n")
            file.write("   # After creating your application\n")
            file.write("   setup_yield_module(application)\n\n")
            file.write("2. Restart your bot\n\n")
            file.write("3. Users can now access:\n")
            file.write("   /simulate - Generate a simulated trade\n")
            file.write("   /history - View trade history\n")
            file.write("   /balance - Check simulated balance\n")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Adding trade history and simulation buttons to your bot...")
    success = add_buttons_to_bot_v20_runner()
    
    if success:
        print("\n✅ Buttons added successfully!")
        print("\nTo complete the integration:")
        print("1. Add the yield module to your main bot file:")
        print("   from yield_module import setup_yield_module")
        print("   setup_yield_module(application)")
        print("\n2. Restart your bot")
    else:
        print("\n❌ Failed to add buttons. Manual integration required.")
        print("1. Add buttons to your main menu and dashboard")
        print("2. Add callback handlers for 'simulate_trade' and 'view_trade_history'")
        print("3. Add the yield module to your main bot file")