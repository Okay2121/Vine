#!/usr/bin/env python
"""
Add Trade History Button
This script adds the trade history button to your bot's main menu and dashboard.
"""
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def add_trade_history_button_to_bot_v20_runner():
    """
    Add the trade history button to bot_v20_runner.py
    """
    try:
        # Read the current content of the file
        with open('bot_v20_runner.py', 'r') as file:
            content = file.read()
        
        # 1. Add button to main menu
        main_menu_keyboard_pattern = """    keyboard = [
        # First row - primary actions
        [
            {"text": "💰 Deposit SOL", "callback_data": "deposit"},
            {"text": "📊 Dashboard", "callback_data": "view_dashboard"}
        ],
        # Second row - information and features
        [
            {"text": "ℹ️ How It Works", "callback_data": "how_it_works"},
            {"text": "🔗 Referral Program", "callback_data": "referral"}
        ],
        # Third row - settings and help
        [
            {"text": "⚙️ Settings", "callback_data": "settings"},
            {"text": "❓ Help", "callback_data": "help"}
        ]"""
        
        main_menu_keyboard_replacement = """    keyboard = [
        # First row - primary actions
        [
            {"text": "💰 Deposit SOL", "callback_data": "deposit"},
            {"text": "📊 Dashboard", "callback_data": "view_dashboard"}
        ],
        # Second row - information and features
        [
            {"text": "ℹ️ How It Works", "callback_data": "how_it_works"},
            {"text": "🔗 Referral Program", "callback_data": "referral"}
        ],
        # Third row - settings and help
        [
            {"text": "⚙️ Settings", "callback_data": "settings"},
            {"text": "❓ Help", "callback_data": "help"}
        ],
        # Trade simulation features
        [
            {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},
            {"text": "📜 Trade History", "callback_data": "view_trade_history"}
        ]"""
        
        content = content.replace(main_menu_keyboard_pattern, main_menu_keyboard_replacement)
        
        # 2. Add button to dashboard
        dashboard_keyboard_pattern = """            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💰 Deposit", "callback_data": "deposit"},
                    {"text": "💸 Withdrawal", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "📊 Performance", "callback_data": "trading_history"},
                    {"text": "👥 Referral", "callback_data": "referral"}
                ],
                [
                    {"text": "🛟 Customer Support", "callback_data": "support"},
                    {"text": "❓ FAQ", "callback_data": "faqs"}
                ]"""
                
        dashboard_keyboard_replacement = """            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💰 Deposit", "callback_data": "deposit"},
                    {"text": "💸 Withdrawal", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "📊 Performance", "callback_data": "trading_history"},
                    {"text": "👥 Referral", "callback_data": "referral"}
                ],
                [
                    {"text": "🛟 Customer Support", "callback_data": "support"},
                    {"text": "❓ FAQ", "callback_data": "faqs"}
                ],
                [
                    {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},
                    {"text": "📜 Trade History", "callback_data": "view_trade_history"}
                ]"""
        
        content = content.replace(dashboard_keyboard_pattern, dashboard_keyboard_replacement)
        
        # 3. Add callback handlers for the buttons
        handlers_pattern = """    # Referral-specific buttons
    bot.add_callback_handler("copy_referral", lambda update, chat_id: bot.send_message(chat_id, "Referral link copied to clipboard! Share with friends to earn 5% of their profits."))
    bot.add_callback_handler("referral_earnings", lambda update, chat_id: bot.send_message(chat_id, "Your referral earnings will appear here once your friends start trading."))
    
    # Admin panel handlers"""
        
        handlers_replacement = """    # Referral-specific buttons
    bot.add_callback_handler("copy_referral", lambda update, chat_id: bot.send_message(chat_id, "Referral link copied to clipboard! Share with friends to earn 5% of their profits."))
    bot.add_callback_handler("referral_earnings", lambda update, chat_id: bot.send_message(chat_id, "Your referral earnings will appear here once your friends start trading."))
    
    # Trade simulation buttons
    bot.add_callback_handler("simulate_trade", lambda update, chat_id: bot.send_message(chat_id, "Use /simulate to generate a new trade"))
    bot.add_callback_handler("view_trade_history", lambda update, chat_id: bot.send_message(chat_id, "Use /history to view your simulated trade history"))
    
    # Admin panel handlers"""
        
        content = content.replace(handlers_pattern, handlers_replacement)
        
        # Write the modified content back to the file
        with open('bot_v20_runner.py', 'w') as file:
            file.write(content)
        
        logger.info("Successfully added trade history buttons to bot_v20_runner.py")
        return True
    except Exception as e:
        logger.error(f"Failed to add trade history buttons: {e}")
        return False

if __name__ == "__main__":
    print("Adding trade history buttons to your bot...")
    success = add_trade_history_button_to_bot_v20_runner()
    if success:
        print("✅ Trade history buttons added successfully!")
        print("\nTo complete the integration:")
        print("1. Add the yield module to your bot.py or main bot file:")
        print("   from yield_module import setup_yield_module")
        print("   setup_yield_module(application)")
        print("\n2. Restart your bot")
    else:
        print("❌ Failed to add trade history buttons. Check the logs for details.")