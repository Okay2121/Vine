# Real-Time Snipe History + Yield Tracker Module

This module adds realistic trade simulations, yield tracking, and trade history to your Telegram bot, enhancing the user experience without interfering with existing functionality.

## Features

- **Realistic Trade Simulation**: Simulates token snipes with data from Pump.fun with entry caps between $2M-$4M
- **7-Day 2x ROI Yield Tracking**: Calculates yield based on a 7-day doubling curve (~10.4% daily)
- **Automatic Balance Updates**: Updates virtual SOL balance immediately after each trade
- **Trade History with Pagination**: Shows trade history with Next/Prev navigation (3 per page)
- **Clickable Token Links**: Each trade includes links to pump.fun and Birdeye.so

## Commands

This module adds three new commands to your Telegram bot:

- `/simulate` - Simulates a random trade and updates yield + balance
- `/history` - Shows paginated snipe history
- `/balance` - Displays current SOL balance

## Integration

### Simple Integration

1. Copy the `yield_module.py` file to your project directory.

2. In your main bot file, import and initialize the module:

```python
from yield_module import setup_yield_module

# After creating your application but before starting it
application = Application.builder().token(BOT_TOKEN).build()

# Add your existing handlers
# ...

# Initialize the yield module
setup_yield_module(application)

# Start your application
application.run_polling()  # or application.run_webhook()
```

### Complete Integration Example

We've provided a complete integration example in `bot_webhook_handler_with_yield.py` that shows how to integrate the module with the existing bot.

## Data Storage

The module uses its own isolated storage mechanism in `yield_data.json`, which maintains:

- A simulated SOL balance (starting at 1.0 SOL)
- A chronological list of trade history for each user
- Pagination state for the trade history view

The module does not interact with the existing database or user balance system, ensuring zero interference with other bot functionality.

## API Connections

The module connects to:

- https://client-api.pump.fun/tokens/recent - To fetch recent tokens for simulation
- (Fallback to randomized data if API is unavailable)

## Technical Details

- **Framework Compatibility**: Works with python-telegram-bot v20+
- **Pagination Mechanism**: Uses callback_data with page tracking for navigation
- **Yield Calculation**: Implements compound interest to simulate 2x ROI in 7 days
- **Link Format**: Uses HTML parsing with anchor tags for clickable links

## Testing

A test script is included that demonstrates how the module works without needing a full Telegram bot integration:

```
python test_yield_module.py
```

This will:
- Test fetching tokens from the API
- Generate sample trades
- Show trade history with pagination
- Display balance information

## Troubleshooting

- **API Connection Issues**: If the connection to Pump.fun fails, the module will fall back to generating random token data.
- **Command Conflicts**: The module only adds new commands that don't conflict with existing commands.
- **Missing Imports**: Make sure python-telegram-bot v20+ is installed.

## Future Enhancements

Possible future enhancements for this module include:

- Daily scheduled simulated trades
- Token category filtering
- Performance metrics and charts
- Real-time price tracking via Birdeye API
- Customizable ROI strategies