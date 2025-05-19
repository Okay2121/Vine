#!/usr/bin/env python
"""
Add Only Trade History Button
This script removes previously added buttons and adds only a trade history button
to the performance page of the Telegram bot.
"""
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_and_add_trade_history_button():
    """
    Remove all previously added buttons and add a trade history button only to the performance page.
    """
    try:
        # Read the bot_v20_runner.py file
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # Remove buttons from main menu if they exist
        main_menu_pattern = """        # Trade simulation buttons
        [
            {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},
            {"text": "📜 Trade History", "callback_data": "view_trade_history"}
        ],"""
        if main_menu_pattern in content:
            content = content.replace(main_menu_pattern, "")
            logger.info("Removed extra buttons from main menu")
        
        # Remove buttons from dashboard if they exist
        dashboard_pattern = """                [
                    {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},
                    {"text": "📜 Trade History", "callback_data": "view_trade_history"}
                ],"""
        if dashboard_pattern in content:
            content = content.replace(dashboard_pattern, "")
            logger.info("Removed extra buttons from dashboard")
        
        # Remove extra handlers if they exist
        handlers_pattern = """    # Trade simulation handlers
    bot.add_callback_handler("simulate_trade", lambda update, chat_id: bot.send_message(chat_id, "Use /simulate to generate a new trade"))
    bot.add_callback_handler("view_trade_history", lambda update, chat_id: bot.send_message(chat_id, "Use /history to view your trade history"))
"""
        if handlers_pattern in content:
            content = content.replace(handlers_pattern, "")
            logger.info("Removed extra handlers")
        
        # Add trade history button to performance page
        performance_keyboard_pattern = """            # Create proper keyboard with transaction history button
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💲 Deposit More", "callback_data": "deposit"},
                    {"text": "💰 Withdraw", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "📜 Transaction History", "callback_data": "transaction_history"},
                    {"text": "🔙 Back to Dashboard", "callback_data": "dashboard"}
                ]"""
        
        performance_keyboard_replacement = """            # Create proper keyboard with transaction history button
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💲 Deposit More", "callback_data": "deposit"},
                    {"text": "💰 Withdraw", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "📜 Transaction History", "callback_data": "transaction_history"},
                    {"text": "📊 Trade History", "callback_data": "view_trade_history"}
                ],
                [
                    {"text": "🔙 Back to Dashboard", "callback_data": "dashboard"}
                ]"""
        
        if performance_keyboard_pattern in content:
            content = content.replace(performance_keyboard_pattern, performance_keyboard_replacement)
            logger.info("Added trade history button to performance page")
        
        # Add a single handler for the trade history button
        handlers_pattern_to_add = """
    # Trade history button handler
    bot.add_callback_handler("view_trade_history", lambda update, chat_id: bot.send_message(chat_id, "Use /history to view your simulated trade history"))
"""
        
        add_handler_position = content.find("# Admin panel handlers")
        if add_handler_position > 0:
            content = content[:add_handler_position] + handlers_pattern_to_add + content[add_handler_position:]
            logger.info("Added trade history button handler")
        
        # Write the modified content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(content)
        
        logger.info("Successfully updated bot_v20_runner.py")
        return True
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Cleaning up and adding only the trade history button to the performance page...")
    success = clean_and_add_trade_history_button()
    
    if success:
        print("\n✅ Success! Trade history button added to performance page")
        print("\nTo complete the integration:")
        print("1. Add the yield module to your main bot file:")
        print("   from yield_module import setup_yield_module")
        print("   setup_yield_module(application)")
        print("\n2. Restart your bot")
    else:
        print("\n❌ Failed to update the bot file. Please check the logs.")