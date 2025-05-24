# Admin Trade System Guide

## New Trade Message Format

As an admin, you can now execute trades using a simple message format directly in the bot:

```
Buy $TOKEN PRICE TX_LINK
```

or 

```
Sell $TOKEN PRICE TX_LINK
```

## Examples

**Buy Example:**
```
Buy $ZING 0.0041 https://solscan.io/tx/abc123
```

**Sell Example:**
```
Sell $ZING 0.0065 https://solscan.io/tx/def456
```

## How It Works

1. **BUY Orders**:
   - Type a Buy message to record a trade entry position
   - The system stores the token name, entry price, and transaction link
   - The position remains open until a matching Sell is processed
   - A timestamp is automatically recorded

2. **SELL Orders**:
   - Type a Sell message when you want to exit a position
   - The system automatically matches with the oldest open Buy order for the same token
   - ROI is calculated: ((Sell Price - Buy Price) / Buy Price) × 100
   - All users' balances are updated with their proportional profit/loss
   - User transaction histories are immediately updated

3. **Trade Pairing Logic**:
   - The system always matches a Sell with the oldest unmatched Buy for the same token
   - This ensures proper FIFO (First In, First Out) order processing
   - Each Buy-Sell pair creates a complete trade record

4. **User Updates**:
   - Users receive real-time notifications with their personalized profit/loss
   - Transaction histories reflect the trades immediately
   - Balance updates happen in real-time

## Real-Time Transaction Impacts

When a trade is completed (BUY + SELL):

- User balances are updated instantly
- Transaction history is updated immediately for each user
- Trading positions are recorded with complete details
- Users receive immediate personalized notifications

## Features

- **Timestamps**: Automatically recorded for all trades
- **Transaction verification**: Links stored for verification
- **Duplicate prevention**: System detects and prevents duplicate transactions
- **Detailed trade tracking**: Entry and exit prices, ROI, timestamps
- **Real-time updates**: Transaction histories updated immediately

## Admin-Only Access

This feature is restricted to admin users only. Non-admins attempting to use this format will receive an error message.

## Troubleshooting

- If a Sell message returns "No open BUY position found", ensure you've previously recorded a Buy for that token
- If transaction links are reported as duplicates, verify you're not using the same transaction hash twice
- Check user transaction histories to confirm trades are being properly recorded