"""
Position Notification System
===========================
Sends professional position updates to users after trades are processed
"""

import logging
from typing import List, Dict, Any
from app import app, db
from models import User, TradingPosition, UserStatus
from utils.simplified_trade_processor import SimplifiedTradeProcessor

logger = logging.getLogger(__name__)

class PositionNotificationSystem:
    """Sends professional position notifications to users"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.processor = SimplifiedTradeProcessor()
    
    def send_position_update(self, user_id: int, position: TradingPosition, token_data: Dict) -> bool:
        """
        Send professional position update to a specific user
        
        Args:
            user_id (int): User ID
            position (TradingPosition): Trading position
            token_data (dict): Token data from DEX Screener
            
        Returns:
            bool: Success status
        """
        try:
            # Format the professional position display
            position_display = self.processor.format_position_display(position, token_data)
            
            # Add position management buttons
            keyboard = self.bot.create_inline_keyboard([
                [
                    {"text": "📊 View Details", "callback_data": f"position_details_{position.id}"},
                    {"text": "🔄 Refresh", "callback_data": f"position_refresh_{position.id}"}
                ],
                [
                    {"text": "📈 Performance", "callback_data": "performance_dashboard"},
                    {"text": "🎯 Sniper Mode", "callback_data": "sniper_mode"}
                ]
            ])
            
            # Send the formatted position update
            self.bot.send_message(
                user_id,
                position_display,
                reply_markup=keyboard,
                parse_mode=None  # Raw text for professional display
            )
            
            logger.info(f"Sent position update for {token_data['symbol']} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending position update to user {user_id}: {str(e)}")
            return False
    
    def notify_all_users_of_trade(self, token_data: Dict, roi_percentage: float, affected_count: int) -> Dict:
        """
        Send trade notifications to all affected users
        
        Args:
            token_data (dict): Token data from DEX Screener
            roi_percentage (float): ROI percentage from the trade
            affected_count (int): Number of users affected
            
        Returns:
            dict: Notification results
        """
        try:
            with app.app_context():
                # Get all positions for this token that were just closed
                positions = TradingPosition.query.filter_by(
                    token_name=token_data['symbol'],
                    status='closed'
                ).order_by(TradingPosition.sell_timestamp.desc()).limit(affected_count).all()
                
                if not positions:
                    return {
                        'success': False,
                        'error': f"No positions found for {token_data['symbol']}"
                    }
                
                successful_notifications = 0
                failed_notifications = 0
                
                for position in positions:
                    # Get user info
                    user = User.query.get(position.user_id)
                    if not user or user.status != UserStatus.ACTIVE:
                        failed_notifications += 1
                        continue
                    
                    # Send position notification
                    if self.send_position_update(user.telegram_id, position, token_data):
                        successful_notifications += 1
                    else:
                        failed_notifications += 1
                
                return {
                    'success': True,
                    'successful_notifications': successful_notifications,
                    'failed_notifications': failed_notifications,
                    'total_positions': len(positions)
                }
                
        except Exception as e:
            logger.error(f"Error notifying users of trade: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_trade_summary_to_admin(self, chat_id: int, result: Dict) -> None:
        """
        Send detailed trade summary to admin
        
        Args:
            chat_id (int): Admin chat ID
            result (dict): Trade processing result
        """
        try:
            if not result['success']:
                self.bot.send_message(chat_id, f"❌ {result['error']}")
                return
            
            # Send detailed success message
            success_msg = (
                f"✅ *Trade Processed Successfully*\n\n"
                f"• *Token:* {result['token_data']['symbol']} ({result['token_data']['name']})\n"
                f"• *Contract:* `{result['token_data'].get('contract_address', 'N/A')}`\n"
                f"• *Users Affected:* {result['affected_count']}\n"
                f"• *ROI Applied:* {result['roi_percentage']:.2f}%\n"
                f"• *Total Profit:* {result['total_profit']:.4f} SOL\n"
                f"• *Market Cap Entry:* {self._format_market_cap(result.get('entry_market_cap', 0))}\n"
                f"• *Market Cap Exit:* {self._format_market_cap(result.get('exit_market_cap', 0))}\n\n"
                f"*Professional position displays sent to all users!*"
            )
            
            self.bot.send_message(chat_id, success_msg, parse_mode="Markdown")
            
            # Send notification results if available
            if 'notification_result' in result:
                notif_result = result['notification_result']
                if notif_result['success']:
                    notif_msg = (
                        f"📧 *Notification Results*\n\n"
                        f"• *Successful:* {notif_result['successful_notifications']}\n"
                        f"• *Failed:* {notif_result['failed_notifications']}\n"
                        f"• *Total Positions:* {notif_result['total_positions']}"
                    )
                    self.bot.send_message(chat_id, notif_msg, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error sending trade summary to admin: {str(e)}")
            self.bot.send_message(chat_id, f"❌ Error sending trade summary: {str(e)}")
    
    def _format_market_cap(self, market_cap: float) -> str:
        """Format market cap with appropriate units"""
        if market_cap >= 1_000_000:
            return f"${market_cap/1_000_000:.2f}M"
        elif market_cap >= 1_000:
            return f"${market_cap/1_000:.1f}K"
        else:
            return f"${market_cap:.2f}"