# Adding Trade History Button to Bot Menus

This guide explains how to add the trade history button to your bot's main menu and dashboard, making it easy for users to access the new trading simulation features.

## Option 1: Minimal Integration (Commands Only)

The simplest integration method is to just add the yield module commands to your bot without modifying any menus:

```python
from yield_module import setup_yield_module

# After creating your application
application = Application.builder().token(BOT_TOKEN).build()

# Add your existing handlers
# ...

# Initialize the yield module
setup_yield_module(application)
```

With this approach, users can access the features via commands:
- `/simulate` - Simulate a trade
- `/history` - View trade history
- `/balance` - Check simulated balance

## Option 2: Main Menu Integration

To add trade history buttons to your main menu, modify your `show_main_menu` function in `bot_v20_runner.py`:

```python
def show_main_menu(update, chat_id):
    """Show the main menu for the bot with exact button layout from the original."""
    keyboard = [
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
        # NEW ROW - trade simulation features
        [
            {"text": "🧬 Trade Simulator", "callback_data": "trading_simulator"},
            {"text": "📜 Snipe History", "callback_data": "view_snipe_history"}
        ]
    ]
    reply_markup = bot.create_inline_keyboard(keyboard)
    
    # Rest of the function remains the same
    # ...
```

Then add callback handlers for these new buttons:

```python
# Add callback handlers for trade simulator buttons
bot.add_callback_handler("trading_simulator", trading_simulator_callback)
bot.add_callback_handler("view_snipe_history", view_snipe_history_callback)

# Define callback functions
def trading_simulator_callback(update, chat_id):
    """Handle trading simulator button."""
    bot.send_message(chat_id, "Use /simulate to generate a trade")

def view_snipe_history_callback(update, chat_id):
    """Handle snipe history button."""
    bot.send_message(chat_id, "Use /history to view your trade history")
```

## Option 3: Dashboard Integration

To add trade history buttons to your dashboard, modify the keyboard in the `dashboard_command` function:

```python
# Create keyboard buttons
keyboard = bot.create_inline_keyboard([
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
    # NEW ROW - trading simulation buttons
    [
        {"text": "🧬 Simulate Trade", "callback_data": "simulate_trade"},
        {"text": "📜 Snipe History", "callback_data": "view_snipe_history"}
    ]
])
```

## Option 4: Enhanced Integration with Pop-up

For a more sophisticated integration, use the `dashboard_enhancement.py` module we provided:

```python
from dashboard_enhancement import setup_dashboard_enhancement

# After initializing your application and yield module
setup_dashboard_enhancement(application)
```

This adds a popup with simulation buttons when users access the dashboard.

## Linking to /history and /simulate Commands

For any of these integrations to work, you need to create callback handlers that link the buttons to the commands:

```python
# Define callback handlers
bot.add_callback_handler("simulate_trade", lambda update, chat_id: bot.send_message(chat_id, "Use /simulate to generate a trade"))
bot.add_callback_handler("view_snipe_history", lambda update, chat_id: bot.send_message(chat_id, "Use /history to view your trade history"))
bot.add_callback_handler("check_sim_balance", lambda update, chat_id: bot.send_message(chat_id, "Use /balance to check your simulated balance"))
```

## Complete Example

See `menu_integration_example.py` for a complete working example of how to integrate the trade history buttons into your bot's menu system.

## UI/UX Tips

1. Use consistent emojis for the simulation features (🧬 for simulation, 📜 for history)
2. Place simulation buttons in a separate row to distinguish them from core features
3. Add brief instructions when users click on the buttons
4. Consider adding a dedicated Trade Simulator menu that combines all the simulation features