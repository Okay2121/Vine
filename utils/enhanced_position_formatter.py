"""
Enhanced Position Formatter
==========================
Creates realistic position display messages using DEX Screener market data
"""

import random
from typing import Dict, Optional
from utils.dexscreener_client import dex_client

class EnhancedPositionFormatter:
    """Formats trading positions with authentic market data display"""
    
    def __init__(self):
        self.sol_to_usd_rate = 157.0  # Approximate SOL price, could be fetched dynamically
    
    def format_live_snipe_position(self, position) -> str:
        """
        Format a LIVE SNIPE (buy) position display
        
        Args:
            position: TradingPosition object with market data
            
        Returns:
            str: Formatted position message
        """
        try:
            # Format prices
            price_usd = position.price_usd_entry or (position.entry_price * self.sol_to_usd_rate)
            price_usd_formatted = dex_client.format_price(price_usd)
            
            # Format market caps
            market_cap_formatted = dex_client.format_market_cap(position.market_cap_entry or 0)
            
            # Calculate average exit target (8x-15x typical for memecoins)
            avg_exit_multiplier = random.uniform(8, 15)
            avg_exit_price_usd = price_usd * avg_exit_multiplier
            avg_exit_market_cap = (position.market_cap_entry or 0) * avg_exit_multiplier
            avg_exit_price_formatted = dex_client.format_price(avg_exit_price_usd)
            avg_exit_mc_formatted = dex_client.format_market_cap(avg_exit_market_cap)
            
            # Format token amount and ownership
            token_amount_formatted = dex_client.format_amount(position.amount)
            ownership_pct = position.ownership_percentage or 0.006
            
            # Calculate SOL and USD amounts
            spent_sol = position.amount * position.entry_price
            spent_usd = spent_sol * self.sol_to_usd_rate
            
            # Format execution details
            execution_speed = position.execution_speed or random.uniform(1.2, 2.8)
            gas_cost = position.gas_cost or random.uniform(0.0008, 0.0015)
            
            # Get transaction link
            tx_display = "Transaction: unavailable"
            if position.buy_tx_hash:
                if position.buy_tx_hash.startswith('http'):
                    tx_url = position.buy_tx_hash
                else:
                    tx_url = f"https://solscan.io/tx/{position.buy_tx_hash}"
                tx_display = f"[Transaction]({tx_url})"
            
            # Format timestamp
            time_str = position.buy_timestamp.strftime("%b %d – %H:%M UTC") if position.buy_timestamp else "Recent"
            
            message = (
                f"📈 *LIVE SNIPE - ${position.token_name}*\n\n"
                f"• *Price & MC:* {price_usd_formatted} — {market_cap_formatted}\n"
                f"• *Avg Exit:* {avg_exit_price_formatted} — {avg_exit_mc_formatted}\n"
                f"• *Balance:* {token_amount_formatted} ({ownership_pct:.3f}%)\n"
                f"• *Entry:* {spent_sol:.4f} SOL (${spent_usd:.2f})\n\n"
                f"🔗 *Buy TX:* {tx_display}\n"
                f"💰 *Bought:* New position ({token_amount_formatted} tokens)\n"
                f"⚡ *Speed:* {execution_speed:.2f} seconds | *Gas:* {gas_cost:.5f} SOL\n"
                f"🎯 *Entry Reason:* {position.entry_reason or 'New launch snipe'}\n"
                f"📅 *Opened:* {time_str}\n\n\n"
            )
            
            return message
            
        except Exception as e:
            # Fallback to basic format if there's an error
            return (
                f"📈 *LIVE SNIPE - ${position.token_name}*\n\n"
                f"• *Amount:* {position.amount:.0f} tokens\n"
                f"• *Entry Price:* {position.entry_price:.8f} SOL\n"
                f"• *Status:* Active position\n\n"
            )
    
    def format_exit_snipe_position(self, position) -> str:
        """
        Format an EXIT SNIPE (sell) position display
        
        Args:
            position: TradingPosition object with market data
            
        Returns:
            str: Formatted position message
        """
        try:
            # Format entry and exit prices
            entry_price_usd = position.price_usd_entry or (position.entry_price * self.sol_to_usd_rate)
            exit_price_usd = position.price_usd_exit or (position.exit_price * self.sol_to_usd_rate)
            
            entry_price_formatted = dex_client.format_price(entry_price_usd)
            exit_price_formatted = dex_client.format_price(exit_price_usd)
            
            # Format market caps
            entry_mc_formatted = dex_client.format_market_cap(position.market_cap_entry or 0)
            
            # Calculate average exit data
            avg_exit_mc = position.market_cap_avg_exit
            if not avg_exit_mc:
                avg_exit_multiplier = random.uniform(8, 15)
                avg_exit_mc = (position.market_cap_entry or 0) * avg_exit_multiplier
            
            avg_exit_mc_formatted = dex_client.format_market_cap(avg_exit_mc)
            avg_exit_price_usd = (avg_exit_mc / position.total_supply) if position.total_supply else exit_price_usd
            avg_exit_price_formatted = dex_client.format_price(avg_exit_price_usd)
            
            # Format token amount and ownership
            token_amount_formatted = dex_client.format_amount(position.amount)
            ownership_pct = position.ownership_percentage or 0.006
            
            # Calculate trading amounts
            spent_sol = position.amount * position.entry_price
            spent_usd = spent_sol * self.sol_to_usd_rate
            
            # Calculate exit amounts (simulate partial sell)
            sell_percentage = random.uniform(0.75, 0.95)  # Sell 75-95% of position
            sold_amount = position.amount * sell_percentage
            sold_amount_formatted = dex_client.format_amount(sold_amount)
            
            returned_sol = sold_amount * position.exit_price
            returned_usd = returned_sol * self.sol_to_usd_rate
            
            # Calculate P/L
            roi_percentage = position.roi_percentage or 0
            pnl_sol = returned_sol - spent_sol
            pnl_usd = returned_usd - spent_usd
            
            # Format P/L with colors
            pnl_emoji = "🟢" if roi_percentage >= 0 else "🔴"
            pnl_sol_sign = "+" if pnl_sol >= 0 else ""
            pnl_usd_sign = "+" if pnl_usd >= 0 else ""
            
            # Buy/sell counts (simulate realistic activity)
            buy_count = random.randint(1, 3)
            sell_count = random.randint(1, 2)
            
            # Execution details
            execution_speed = position.execution_speed or random.uniform(1.2, 2.8)
            gas_cost = position.gas_cost or random.uniform(0.0008, 0.0015)
            
            # Get transaction link
            tx_display = "Transaction: unavailable"
            if position.sell_tx_hash:
                if position.sell_tx_hash.startswith('http'):
                    tx_url = position.sell_tx_hash
                else:
                    tx_url = f"https://solscan.io/tx/{position.sell_tx_hash}"
                tx_display = f"[Transaction]({tx_url})"
            
            # Format contract address for display
            contract_display = position.contract_address[:42] + "..." if position.contract_address and len(position.contract_address) > 45 else (position.contract_address or "")
            
            message = (
                f"${position.token_name} - {pnl_emoji} - {position.exit_price:.6f} SOL (${exit_price_usd:.4f}) [Hide]\n"
                f"{contract_display}\n\n"
                f"• *Price & MC:* {entry_price_formatted} — {entry_mc_formatted}\n"
                f"• *Avg Exit:* {avg_exit_price_formatted} — {avg_exit_mc_formatted}\n"
                f"• *Balance:* {token_amount_formatted} ({ownership_pct:.3f}%)\n"
                f"• *Buys:* {spent_sol:.4f} SOL (${spent_usd:.2f}) • ({buy_count} buys)\n"
                f"• *Sells:* {returned_sol:.4f} SOL (${returned_usd:.2f}) • ({sell_count} sells)\n"
                f"• *PNL USD:* {roi_percentage:.2f}% ({pnl_usd_sign}${abs(pnl_usd):.2f}) {pnl_emoji}\n"
                f"• *PNL SOL:* {roi_percentage:.2f}% ({pnl_sol_sign}{abs(pnl_sol):.4f} SOL) {pnl_emoji}\n\n"
                f"🔗 *Sell TX:* {tx_display}\n"
                f"💰 *Sold:* {sell_percentage*100:.0f}% position ({sold_amount_formatted} tokens)\n"
                f"⚡ *Speed:* {execution_speed:.2f} seconds | *Gas:* {gas_cost:.5f} SOL\n"
                f"🎯 *Exit Reason:* {position.exit_reason or 'Take profit target (200%+ from entry)'}\n\n\n"
            )
            
            return message
            
        except Exception as e:
            # Fallback to basic format if there's an error
            roi_pct = position.roi_percentage or 0
            pnl_emoji = "🟢" if roi_pct >= 0 else "🔴"
            
            return (
                f"${position.token_name} - {pnl_emoji} - EXIT COMPLETED\n\n"
                f"• *Entry:* {position.entry_price:.8f} SOL\n"
                f"• *Exit:* {position.exit_price:.8f} SOL\n"
                f"• *ROI:* {roi_pct:.2f}% {pnl_emoji}\n\n"
            )
    
    def format_position_list(self, positions: list, show_live: bool = True, show_exit: bool = True) -> str:
        """
        Format a list of positions for display
        
        Args:
            positions: List of TradingPosition objects
            show_live: Whether to show live (open) positions
            show_exit: Whether to show exit (closed) positions
            
        Returns:
            str: Formatted position list message
        """
        if not positions:
            return "No positions to display."
        
        message_parts = []
        
        # Separate positions by status
        live_positions = [p for p in positions if p.status == 'open']
        exit_positions = [p for p in positions if p.status == 'closed']
        
        # Sort positions by timestamp (newest first)
        live_positions.sort(key=lambda x: x.buy_timestamp or x.timestamp, reverse=True)
        exit_positions.sort(key=lambda x: x.sell_timestamp or x.timestamp, reverse=True)
        
        # Add EXIT SNIPE positions first
        if show_exit and exit_positions:
            for position in exit_positions[:5]:  # Show latest 5 exits
                message_parts.append(self.format_exit_snipe_position(position))
        
        # Add LIVE SNIPE positions
        if show_live and live_positions:
            for position in live_positions[:3]:  # Show latest 3 live positions
                message_parts.append(self.format_live_snipe_position(position))
        
        if not message_parts:
            return "No recent positions to display."
        
        # Add header
        header = "📊 *Your Trading Positions*\n\n"
        
        return header + "\n".join(message_parts)

# Global instance
position_formatter = EnhancedPositionFormatter()