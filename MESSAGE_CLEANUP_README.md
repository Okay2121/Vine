# Progressive Message Cleanup System

This module provides a comprehensive solution for maintaining a clean, user-friendly chat experience in the Telegram bot by automatically removing old or outdated messages as users progress through different interactions.

## Key Features

1. **Automatic Message Tracking**: The system automatically tracks messages by type and user, making it easy to clean up specific message categories.

2. **Progressive Flow States**: Messages are deleted as users transition between different states (welcome → start → dashboard → deposit, etc.) to keep the chat clean.

3. **Selective Persistence**: Important messages like receipts, transaction history, and trade reports are preserved, while temporary messages are removed.

4. **Smart Error Handling**: The system gracefully handles cases where messages can't be deleted (too old, already deleted, etc.) without disrupting the user experience.

## Integration Points

The message cleanup system is integrated at these key points:

1. **Command Handlers**: When users issue commands like `/start`, `/deposit`, `/dashboard`, etc.

2. **Callback Handlers**: When users interact with buttons in messages.

3. **Auto Trading Notifications**: Trading updates replace old updates to avoid chat clutter.

4. **Flow Transitions**: Messages are cleaned up when users move between different screens or states.

## Message Types and Persistence

### Tracked Message Types (Auto-Cleaned)

- `welcome_message`: Initial greeting before /start
- `start_message`: Response to /start command
- `dashboard`: Dashboard displays
- `deposit_instruction`: Instructions for deposits
- `deposit_pending`: Pending deposit confirmation
- `deposit_confirmation`: User confirmed deposit was made
- `wallet_request`: Requesting wallet address
- `withdraw_instruction`: Withdrawal instructions
- `withdraw_pending`: Pending withdrawal confirmation
- `settings_menu`: Settings menus
- `referral_menu`: Referral program menus
- `referral_stats`: Referral statistics
- `help_menu`: Help/FAQ displays
- `trading_update`: Auto-trading updates
- `balance_update`: Balance notifications
- `roi_streak`: ROI streak updates
- `inactivity_nudge`: Reminders to deposit/interact

### Persistent Message Types (Never Deleted)

- `deposit_receipt`: Deposit confirmations after processing
- `withdrawal_receipt`: Withdrawal confirmations after processing
- `trade_history`: Trade history records
- `transaction_history`: Transaction records
- `important_notice`: Critical system notifications
- `support_ticket`: Support ticket submissions
- `admin_message`: Messages from administrators

## Flow Transitions

The system defines these transitions that trigger cleanup:

- `welcome_to_start`: Clean up welcome messages when user starts
- `start_to_dashboard`: Clean up start messages when showing dashboard
- `dashboard_to_deposit`: Clean up dashboard when showing deposit
- `deposit_to_confirmation`: Clean up deposit instructions when confirming
- `confirmation_to_dashboard`: Clean up confirmation when returning to dashboard
- `dashboard_to_withdraw`: Clean up dashboard when showing withdrawal
- `withdraw_to_confirmation`: Clean up withdrawal instructions when confirming
- `any_to_referral`: Clean up various screens when showing referral program
- `any_to_settings`: Clean up various screens when showing settings
- `any_to_dashboard`: Clean up various screens when returning to dashboard

## Usage

To use the message cleanup system in handlers:

```python
# Import the helpers
from utils.message_handlers import (
    send_welcome_message,
    send_start_message,
    send_dashboard_message,
    send_deposit_instructions,
    # etc.
)

# Then in your handler functions:
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command with automatic cleanup."""
    # This will clean up welcome messages and transition to start state
    await send_start_message(
        update, 
        context,
        "Welcome to the bot! Here are your options...",
        reply_markup=your_keyboard_markup
    )
```

For more complex cases, you can use the lower-level functions:

```python
from utils.message_handlers import send_or_edit_message, cleanup_previous_messages

# Clean up specific message types
await cleanup_previous_messages(update, context, ['dashboard', 'deposit_instruction'])

# Send message with custom flow transition
await send_or_edit_message(
    update, 
    context, 
    "Your message here", 
    message_type='custom_type',
    flow_state='custom_state',
    reply_markup=your_keyboard_markup
)
```

## Implementation Details

The system is implemented in two modules:

1. `utils/message_cleanup.py`: Core functionality for tracking, deleting, and transitioning between message states.

2. `utils/message_handlers.py`: Helper functions for integrating the cleanup system with handlers.

These modules work with both direct Telegram Bot API calls and the python-telegram-bot library, providing maximum flexibility and reliability.

## Testing

The system has been tested with the following user paths:

- Welcome → Start → Dashboard → Deposit → Confirmation → Dashboard
- Start → Dashboard → Withdraw → Confirmation → Dashboard
- Dashboard → Referral → Dashboard
- Dashboard → Settings → Dashboard

All paths maintain a clean chat interface without disturbing important messages or functionality.