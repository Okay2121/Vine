# Simple Trade System Guide

## New Trade Message Format

Just type a message with the following format:

```
Buy $TOKEN PRICE TX_LINK
```

or

```
Sell $TOKEN PRICE TX_LINK
```

## Examples

```
Buy $ZING 0.0041 https://solscan.io/tx/abc123
```

```
Sell $ZING 0.0065 https://solscan.io/tx/def456
```

## How It Works

1. **BUY Orders**: Stored in the database for future matching
2. **SELL Orders**: Automatically matched with the oldest unmatched BUY for the same token
3. **ROI Calculation**: ((Sell Price - Buy Price) / Buy Price) × 100
4. **Profit Distribution**: Applied to all active users' balances proportionally
5. **Notifications**: Users receive personalized trade alerts with their specific profits

## Features

- Timestamps are recorded automatically
- Transaction links are stored for verification
- Duplicate transactions are automatically detected and prevented
- Trade pairs are properly matched for accurate ROI tracking
- All user balances are updated with appropriate profit/loss amounts

## Admin-Only Access

This feature is restricted to admin users only for security reasons.