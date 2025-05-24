# Simple Trade System Guide

## Overview

The Simple Trade System provides an intuitive way for admins to execute and record trades directly in the Telegram bot. This new format drastically simplifies the process by allowing admins to use a standardized message format that automatically:

1. Records buy/sell positions
2. Matches sell positions with existing buy positions
3. Calculates ROI automatically
4. Updates user balances based on trade performance
5. Creates transaction history records for all affected users
6. Sends personalized notifications to users

## Message Format

Admins can use the following message format to record trades:

```
Buy $TOKEN PRICE TX_LINK
```

or 

```
Sell $TOKEN PRICE TX_LINK
```

### Examples

**Buy Example:**
```
Buy $ZING 0.0041 https://solscan.io/tx/abc123
```

**Sell Example:**
```
Sell $ZING 0.0065 https://solscan.io/tx/def456
```

## How It Works

### Buy Process

1. Admin sends a Buy message in the proper format
2. System validates the format and checks for duplicate transactions
3. A new open trading position is recorded with:
   - Token name
   - Entry price
   - Transaction hash
   - Buy timestamp
   - Admin ID
   - Open status (waiting for matching sell)
4. Admin receives confirmation with position details

### Sell Process

1. Admin sends a Sell message in the proper format
2. System validates the format and checks for duplicate transactions
3. System searches for the oldest open Buy position for the same token
4. When a match is found, the system:
   - Updates the Buy position with sell details
   - Calculates ROI: ((Sell Price - Buy Price) / Buy Price) × 100
   - Changes position status to "closed"
   - Updates all user balances proportionally to the ROI
   - Creates transaction records for all users
   - Sends notifications to users
5. Admin receives confirmation with trade details including ROI

## Features

### Automatic ROI Calculation

The system automatically calculates the Return on Investment (ROI) when a sell is matched with a buy:

```
ROI = ((Sell Price - Buy Price) / Buy Price) × 100
```

For example, if a token was bought at $0.0041 and sold at $0.0065:
```
ROI = ((0.0065 - 0.0041) / 0.0041) × 100 = 58.54%
```

### Transaction Recording

Every Buy and Sell creates detailed records:

1. **Buy Transaction:**
   - Token name
   - Entry price
   - Buy transaction hash
   - Buy timestamp
   - Open status

2. **Sell Transaction:**
   - Token name
   - Exit price
   - Sell transaction hash
   - Sell timestamp
   - ROI percentage
   - Closed status

### User Balance Updates

When a trade is completed (matched Buy + Sell):

1. All users with positive balances receive their proportion of profits/losses
2. Each user's transaction history is updated immediately
3. Users receive real-time notifications with their personalized profit/loss

### Duplicate Prevention

The system automatically prevents:
- Recording the same buy transaction twice
- Recording the same sell transaction twice
- Selling tokens that haven't been bought

## Best Practices

1. **Consistent Token Names:** Use the same token name format (e.g., $ZING) for both Buy and Sell
2. **Verify Transaction Links:** Ensure transaction links are valid and accessible
3. **Complete the Cycle:** Always ensure each Buy has a matching Sell to properly close positions
4. **Order Matters:** The system matches Sells with the oldest open Buy for the same token (FIFO)

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| "Invalid trade format" | Incorrect message format | Follow the exact format: Buy/Sell $TOKEN PRICE TX_LINK |
| "Transaction already recorded" | Duplicate transaction | Use a different transaction hash |
| "No open BUY position found" | Attempting to sell a token that hasn't been bought | Create a Buy position first |
| "Error processing trade" | Database or system error | Check the logs and try again |

## FAQ

**Q: Can I record multiple buys for the same token?**  
A: Yes, you can create multiple Buy positions for the same token. Sells will match with the oldest Buy first.

**Q: What happens if I make a mistake in a trade record?**  
A: Contact the system administrator to make manual corrections to trade records.

**Q: Can I use this format for any token?**  
A: Yes, the system supports any token name, but be consistent with your naming.

**Q: Do users get notified of all trades?**  
A: Users only receive notifications for completed trades (Buy + Sell) that affect their balance.