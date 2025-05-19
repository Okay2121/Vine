# Auto Trading History Module

This module automatically generates realistic trading history for users with newly launched Solana memecoins, triggered when users deposit funds or when an admin adjusts a user's balance.

## Overview

The auto trading history system simulates realistic trading activity without actually executing trades on the blockchain. It creates a believable trading history that looks like the bot is actively trading on behalf of the user.

## Features

- Triggers automatically when a user deposits funds or when an admin adds to a user's balance
- Creates 4-8 trades per day at random intervals (15-60 minutes between trades)
- Uses real newly launched memecoins from pump.fun or birdeye.so APIs
- Generates realistic profit/loss mix (65% profitable trades, 35% losses)
- Stops trading when daily ROI target (5%) is reached to protect profits
- Resets every 24 hours for a fresh trading cycle
- Records trades in the database with appropriate transaction and profit records
- Sends attractive trade notifications to users via Telegram
- Provides comprehensive daily summary of trading performance
- Tracks 2x weekly ROI progress with visual progress bar
- Sends motivational messages based on performance

## Integration Points

The auto trading history system has been integrated at these points:

1. **Deposit Processing**: When a user deposits funds, the auto trading system is triggered in `utils/solana.py` in the `process_auto_deposit` function.

2. **Admin Balance Adjustment**: When an admin adds funds to a user's balance, the auto trading system is triggered in both:
   - `bot_v20_runner.py` in the `admin_confirm_adjustment_handler` function
   - `handlers/admin.py` in the `admin_confirm_adjustment_callback` function

## Key Components

### Main Module

The core functionality is implemented in `utils/auto_trading_history.py`, which contains:

- Functions to fetch real memecoin data from APIs
- Trade generation with realistic parameters
- Database record creation
- Notification formatting and sending
- Daily summary generation with statistics
- ROI tracking and target management
- Thread management for timed trading

### Entry Points

- `handle_user_deposit(user_id, amount)`: Called when a user makes a deposit
- `handle_admin_balance_adjustment(user_id, amount)`: Called when an admin adjusts a user's balance

### Trade Generation

Trades are generated with these attributes:
- Token name & symbol (from newly launched memecoins)
- Entry & exit timestamps with realistic holding periods
- Profit amount and percentage (mix of gains and losses)
- Balance updates
- Links to pump.fun or birdeye.so for token verification

### Database Records

Each trade generates:
- A "buy" transaction record
- A "sell" transaction record
- A profit record

## Testing

To test the auto trading history module:

1. Make a deposit to a user account
2. Check that auto trading has started
3. Observe the trades being generated over time (15-60 minute intervals)
4. Verify that the trade notifications are sent correctly with proper formatting
5. Confirm that trading stops when daily ROI target is reached
6. Verify that the daily summary is sent at the end of the trading day
7. Check that trading resets and begins again the next day
8. Check the database for transaction and profit records

Alternatively, you can use the admin panel to adjust a user's balance and observe the same behavior.

## Configuration

Key configuration parameters are defined at the top of the `utils/auto_trading_history.py` file:

- `TRADES_PER_DAY`: Number of trades to generate per day (default 4-8)
- `MIN_TRADE_INTERVAL` and `MAX_TRADE_INTERVAL`: Time between trades in minutes (default 15-60)
- `MIN_PROFIT_PERCENT` and `MAX_PROFIT_PERCENT`: Range of profit percentages (default 2-15%)
- `LOSS_PROBABILITY`: Chance of a trade resulting in a loss (default 35%)
- `MAX_LOSS_PERCENT`: Maximum percentage loss for negative trades (default 8%)
- `DAILY_ROI_TARGET`: Daily ROI percentage to stop trading (default 5%)

## External API Integration

The module uses these APIs to fetch real memecoin data:
- Pump.fun API: `https://client-api.pump.fun/tokens/recent`
- Birdeye API: `https://public-api.birdeye.so/public/tokenlist?sort_by=v24hUSD`

If these APIs are unavailable, the system generates realistic new memecoin names with the following patterns:
- Popular themes like "Pepe", "Doge", "Floki", "Moon"
- Current trends like "AI", "GPT", etc.
- Typical memecoin naming conventions (Inu, Labs, Finance, etc.)

## Trade Messages

Trade notifications include:
- Token name and symbol with verification link
- Entry and exit times with holding duration
- Trade amount and profit/loss with percentage
- Special emojis based on performance (rocket for big gains, charts for losses)
- Motivational messages based on trade performance
- Clean timestamp formatting

## Daily Summaries

At the end of each trading day, users receive:
- Total profit amount and ROI percentage
- Current balance
- Win rate and trade statistics
- Profit streak tracking
- Weekly 2x ROI progress with visual bar
- Personalized motivational messages
- Warnings for low balances