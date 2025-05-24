# Trade System Documentation

## Overview

The new trade execution system implements a simplified Buy/Sell format for processing cryptocurrency trades within the Solana Memecoin Trading Bot. This system automatically matches buy and sell orders, calculates ROI, and updates user balances.

## Buy/Sell Message Format

Trades are executed using a simple message format:

```
Buy $TOKEN PRICE TX_LINK
```

or 

```
Sell $TOKEN PRICE TX_LINK
```

Where:
- **$TOKEN** is the token symbol (e.g., $SOL, $BONK)
- **PRICE** is the purchase or sell price (e.g., 0.0015)
- **TX_LINK** is the transaction link or hash from the blockchain explorer

## How It Works

1. **Buy Order**:
   - Admin sends: `Buy $TOKEN PRICE TX_LINK`
   - System creates a pending buy position in the database
   - The position records token name, entry price, and transaction hash

2. **Sell Order**:
   - Admin sends: `Sell $TOKEN PRICE TX_LINK` 
   - System finds the matching buy order for the same token
   - Calculates ROI: `((Sell Price - Buy Price) / Buy Price) * 100`
   - Updates trading position status to 'closed'
   - Creates transaction records for affected users

3. **Balance Updates**:
   - When a sell is matched with a buy, user balances are automatically updated
   - ROI is applied to user balances based on their investment amount
   - Transaction records show the trade profit or loss

## Database Updates

The system uses the following database structures:

1. **TradingPosition Table**:
   - Added `buy_tx_hash` and `sell_tx_hash` columns to track transaction hashes
   - Added `buy_timestamp` and `sell_timestamp` to record when each transaction occurred
   - Added `roi_percentage` to store the calculated return on investment
   - Added `paired_position_id` to link related buy/sell positions

2. **Transaction Table**:
   - Added `related_trade_id` to link transactions to specific trades
   - Added `processed_at` to track when transactions were processed

## Benefits

- **Simplified Admin Workflow**: Easy format for quickly entering trades
- **Automatic ROI Calculation**: No need to manually calculate profits
- **Real-time Updates**: Users see trades reflected in their balance and transaction history immediately
- **Transaction Linking**: Each transaction is properly linked to its associated trade
- **Duplicate Prevention**: Transaction hashes are checked to prevent duplicate processing

## Examples

**Buy Example**:
```
Buy $BONK 0.000012 https://solscan.io/tx/3jWVXFF8UUALA
```

**Sell Example**:
```
Sell $BONK 0.000018 https://solscan.io/tx/5kPQzXYT9oLP
```

## Troubleshooting

If you encounter issues with the trade system:

1. **Duplicate Transaction**: If you see a "Duplicate Transaction" message, the same transaction hash has already been processed.
2. **No Matching Position**: If a sell order has no matching buy order, make sure the token name matches exactly.
3. **Balance Updates**: If balances aren't updating, check the transaction table for the related_trade_id field.

## Future Enhancements

1. Multiple buy-sell pairing for complex trading strategies
2. Partial sell support for gradual position closing
3. Enhanced trade analytics with profit/loss visualization
4. Batch trade processing for high-volume periods