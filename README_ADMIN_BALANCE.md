# Admin Balance Management System

This tool allows admins to silently adjust user balances without affecting the auto deposit detection system or sending notifications to users.

## Features

- **Add or deduct** balance from any user
- **Silent operation** - no notifications sent to users
- **Case-insensitive username search**
- **Comprehensive validation** - prevents balance from going negative
- **Proper transaction records** - creates admin_credit or admin_debit records
- **Auto-trading trigger** - automatically triggers trading simulation on balance additions
- **Command-line interface** - easy to use from scripts or terminal

## Usage

### From Command Line

```bash
python admin_balance_manager.py <username> <amount> [reason]
```

Examples:
```bash
# Add 5 SOL to @username with reason
python admin_balance_manager.py @username 5.0 "Welcome bonus"

# Deduct 2.5 SOL from @username 
python admin_balance_manager.py @username -2.5 "Penalty adjustment"
```

### From Python Code

```python
from admin_balance_manager import adjust_balance

# Add 10 SOL to a user
success, message = adjust_balance("@username", 10.0, "Deposit bonus")
if success:
    print("Balance added successfully")
else:
    print(f"Error: {message}")

# Deduct 3 SOL from a user
success, message = adjust_balance("@username", -3.0, "Manual withdrawal")
if success:
    print("Balance deducted successfully")
else:
    print(f"Error: {message}")
```

## Finding Users

The system supports multiple ways to identify users:

- **Username with @** - e.g., `@username`
- **Username without @** - e.g., `username`
- **Case-insensitive** - e.g., `Username` will match `username`
- **Telegram ID** - e.g., `123456789`

## Safety Features

- Prevents balance from going negative
- Creates proper transaction records
- Validates input amounts
- Provides detailed error messages
- Logs all adjustments for admin review

## Usage in Bot Admin Panel

The admin balance adjustment feature can be integrated into the Telegram bot's admin panel, allowing admins to adjust balances directly from the bot interface.

## Examples

```
✅ Balance adjusted successfully!
ADMIN BALANCE ADJUSTMENT
User: username (ID: 1, Telegram ID: 123456789)
5.0000 SOL added to balance
Previous balance: 10.0000 SOL
New balance: 15.0000 SOL
Reason: Welcome bonus
Transaction ID: 123

✅ Balance adjusted successfully!
ADMIN BALANCE ADJUSTMENT
User: username (ID: 1, Telegram ID: 123456789)
2.5000 SOL deducted from balance
Previous balance: 15.0000 SOL
New balance: 12.5000 SOL
Reason: Manual withdrawal
Transaction ID: 124
```