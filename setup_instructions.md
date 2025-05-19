# Balance Adjustment System Setup

## Overview
This guide explains how to use the improved balance adjustment system for the Solana trading bot. The system allows admins to add or deduct funds from user accounts silently without sending notifications to users.

## Components
1. **admin_balance_manager.py** - Main balance adjustment system
2. **admin_balance_report.py** - Tool for generating balance adjustment reports
3. **simple_balance_adjuster.py** - Direct command-line tool for quick adjustments

## Features
- Case-insensitive username search
- Support for adding or deducting balance
- Proper transaction records
- Silent operation (no user notifications)
- Auto-trading simulation for added funds
- Comprehensive reporting

## Using the Balance Manager

### From Command Line
```bash
# Add 5 SOL to a user
python admin_balance_manager.py @username 5.0 "Reason for adjustment"

# Deduct 2.5 SOL from a user
python admin_balance_manager.py @username -2.5 "Reason for deduction"
```

### From Python Code
```python
from admin_balance_manager import adjust_balance

# Add funds
success, message = adjust_balance("@username", 10.0, "Welcome bonus")

# Deduct funds
success, message = adjust_balance("@username", -3.0, "Manual withdrawal")
```

## Generating Reports

### Basic Report (Last 7 Days)
```bash
python admin_balance_report.py
```

### Filtered Report
```bash
# Last 30 days
python admin_balance_report.py --days 30

# For specific user
python admin_balance_report.py --username @username

# Export to CSV
python admin_balance_report.py --csv
```

## Simulating Trades

After adjusting a user's balance, you may want to simulate some trading activity:

```bash
# Generate 3 trades for a specific user
python live_memecoin_simulation.py
```

This will:
1. Create realistic buy/sell transactions with real token names
2. Generate appropriate profit/loss records
3. Use real-world token data when available

## Integration with Telegram Bot
The admin panel in the Telegram bot automatically uses this system for balance adjustments.

## Troubleshooting
If you encounter any issues with the balance adjustment system:

1. Check that the user exists with the correct username
2. Verify that the database is accessible
3. Check the logs for error messages
4. Ensure the amount format is correct (e.g., 5.0, -2.5)