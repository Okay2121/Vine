#!/usr/bin/env python3
"""
Production Handler System for Telegram Bot
==========================================
Optimized handlers for 500+ users with minimal database usage and efficient caching.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from optimized_bot import TelegramBotOptimized

logger = logging.getLogger(__name__)

class UserService:
    """Service for user-related operations with caching"""
    
    def __init__(self, bot: TelegramBotOptimized):
        self.bot = bot
        self.db = bot.db
        self.cache = bot.cache
    
    def get_user(self, telegram_id: str) -> Optional[Dict]:
        """Get user with caching"""
        # Try cache first
        cached = self.cache.get(f"user:{telegram_id}")
        if cached:
            return cached
        
        # Fetch from database
        def fetch_user(session):
            result = session.execute(
                text("""
                    SELECT id, telegram_id, username, first_name, last_name, 
                           status, balance, initial_deposit, wallet_address,
                           joined_at, last_activity
                    FROM "user" WHERE telegram_id = :telegram_id
                """),
                {"telegram_id": telegram_id}
            )
            row = result.fetchone()
            if row:
                return {
                    'id': row[0],
                    'telegram_id': row[1],
                    'username': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'status': row[5],
                    'balance': float(row[6]) if row[6] else 0.0,
                    'initial_deposit': float(row[7]) if row[7] else 0.0,
                    'wallet_address': row[8],
                    'joined_at': row[9],
                    'last_activity': row[10]
                }
            return None
        
        try:
            user = self.db.execute_with_retry(fetch_user)
            if user:
                self.cache.set(f"user:{telegram_id}", user)
            return user
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}")
            return None
    
    def create_user(self, telegram_id: str, username: str = None, 
                   first_name: str = None, last_name: str = None) -> Optional[Dict]:
        """Create new user"""
        def create_operation(session):
            # Check if user already exists
            existing = session.execute(
                text("SELECT id FROM \"user\" WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id}
            ).fetchone()
            
            if existing:
                return None
            
            # Create new user
            result = session.execute(
                text("""
                    INSERT INTO "user" (telegram_id, username, first_name, last_name, 
                                      status, balance, initial_deposit, joined_at, last_activity)
                    VALUES (:telegram_id, :username, :first_name, :last_name, 
                           'onboarding', 0.0, 0.0, :now, :now)
                    RETURNING id
                """),
                {
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "now": datetime.utcnow()
                }
            )
            user_id = result.fetchone()[0]
            
            return {
                'id': user_id,
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'status': 'onboarding',
                'balance': 0.0,
                'initial_deposit': 0.0,
                'wallet_address': None,
                'joined_at': datetime.utcnow(),
                'last_activity': datetime.utcnow()
            }
        
        try:
            user = self.db.execute_with_retry(create_operation)
            if user:
                self.cache.set(f"user:{telegram_id}", user)
                logger.info(f"Created new user: {telegram_id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None
    
    def update_user_activity(self, telegram_id: str) -> None:
        """Update user's last activity (batched)"""
        def update_operation(session):
            session.execute(
                text("UPDATE \"user\" SET last_activity = :now WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id, "now": datetime.utcnow()}
            )
        
        # Queue for batch processing instead of immediate execution
        self.bot.queue_database_operation(update_operation)
        
        # Update cache
        cached_user = self.cache.get(f"user:{telegram_id}")
        if cached_user:
            cached_user['last_activity'] = datetime.utcnow()
            self.cache.set(f"user:{telegram_id}", cached_user)

class TradingService:
    """Service for trading-related operations"""
    
    def __init__(self, bot: TelegramBotOptimized):
        self.bot = bot
        self.db = bot.db
        self.cache = bot.cache
    
    def get_user_positions(self, user_id: int) -> List[Dict]:
        """Get user's trading positions with caching"""
        cache_key = f"positions:{user_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        def fetch_positions(session):
            result = session.execute(
                text("""
                    SELECT id, token_name, amount, entry_price, current_price, 
                           timestamp, status, trade_type, buy_tx_hash, sell_tx_hash
                    FROM trading_position 
                    WHERE user_id = :user_id AND status = 'open'
                    ORDER BY timestamp DESC
                    LIMIT 20
                """),
                {"user_id": user_id}
            )
            
            positions = []
            for row in result:
                positions.append({
                    'id': row[0],
                    'token_name': row[1],
                    'amount': float(row[2]),
                    'entry_price': float(row[3]),
                    'current_price': float(row[4]),
                    'timestamp': row[5],
                    'status': row[6],
                    'trade_type': row[7],
                    'buy_tx_hash': row[8],
                    'sell_tx_hash': row[9]
                })
            return positions
        
        try:
            positions = self.db.execute_with_retry(fetch_positions)
            self.cache.set(cache_key, positions)
            return positions
        except Exception as e:
            logger.error(f"Error fetching positions for user {user_id}: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user trading statistics with caching"""
        cache_key = f"stats:{user_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        def fetch_stats(session):
            # Get profit/loss data
            result = session.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COALESCE(SUM(CASE WHEN transaction_type = 'trade_profit' THEN amount ELSE 0 END), 0) as total_profit,
                        COALESCE(SUM(CASE WHEN transaction_type = 'trade_loss' THEN amount ELSE 0 END), 0) as total_loss,
                        COALESCE(AVG(CASE WHEN transaction_type = 'trade_profit' THEN amount ELSE NULL END), 0) as avg_profit
                    FROM transaction 
                    WHERE user_id = :user_id 
                    AND transaction_type IN ('trade_profit', 'trade_loss')
                    AND timestamp >= :week_ago
                """),
                {
                    "user_id": user_id,
                    "week_ago": datetime.utcnow() - timedelta(days=7)
                }
            )
            
            row = result.fetchone()
            if row:
                return {
                    'total_trades': row[0],
                    'total_profit': float(row[1]),
                    'total_loss': float(row[2]),
                    'avg_profit': float(row[3]),
                    'net_profit': float(row[1]) - float(row[2])
                }
            
            return {
                'total_trades': 0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'avg_profit': 0.0,
                'net_profit': 0.0
            }
        
        try:
            stats = self.db.execute_with_retry(fetch_stats)
            self.cache.set(cache_key, stats)
            return stats
        except Exception as e:
            logger.error(f"Error fetching stats for user {user_id}: {e}")
            return {'total_trades': 0, 'total_profit': 0.0, 'total_loss': 0.0, 'avg_profit': 0.0, 'net_profit': 0.0}

class ProductionHandlers:
    """Production-optimized command handlers"""
    
    def __init__(self, bot: TelegramBotOptimized):
        self.bot = bot
        self.user_service = UserService(bot)
        self.trading_service = TradingService(bot)
    
    def start_handler(self, message: Dict, bot_instance: TelegramBotOptimized):
        """Handle /start command efficiently"""
        try:
            chat_id = str(message['chat']['id'])
            telegram_id = str(message['from']['id'])
            username = message['from'].get('username')
            first_name = message['from'].get('first_name')
            last_name = message['from'].get('last_name')
            
            # Get or create user
            user = self.user_service.get_user(telegram_id)
            if not user:
                user = self.user_service.create_user(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
            
            # Update activity (batched)
            self.user_service.update_user_activity(telegram_id)
            
            # Send welcome message
            if user and user['status'] == 'onboarding':
                welcome_text = """
🚀 <b>Welcome to Solana Memecoin Trading Bot!</b>

Ready to start automated trading on Solana? Here's how it works:

1️⃣ Deposit SOL to your trading wallet
2️⃣ Our AI finds profitable memecoin opportunities
3️⃣ Automatic trading generates daily profits
4️⃣ Withdraw anytime to your personal wallet

<b>Quick Actions:</b>
💰 /deposit - Add funds to start trading
📊 /dashboard - View your portfolio
⚙️ /settings - Configure your preferences
🎯 /help - Get detailed help

Ready to make your first deposit?
"""
                
                keyboard = {
                    'inline_keyboard': [
                        [{'text': '💰 Make Deposit', 'callback_data': 'start_deposit'}],
                        [{'text': '📊 View Dashboard', 'callback_data': 'dashboard'}],
                        [{'text': '❓ How It Works', 'callback_data': 'how_it_works'}]
                    ]
                }
                
                bot_instance.send_message_safe(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=keyboard
                )
            else:
                # Returning user
                bot_instance.send_message_safe(
                    chat_id=chat_id,
                    text=f"Welcome back! Use /dashboard to view your portfolio or /help for assistance."
                )
                
        except Exception as e:
            logger.error(f"Error in start_handler: {e}")
            bot_instance.send_message_safe(
                chat_id=chat_id,
                text="⚠️ Sorry, there was an error. Please try again in a moment."
            )
    
    def dashboard_handler(self, message: Dict, bot_instance: TelegramBotOptimized):
        """Handle /dashboard command with caching"""
        try:
            chat_id = str(message['chat']['id'])
            telegram_id = str(message['from']['id'])
            
            # Get user data
            user = self.user_service.get_user(telegram_id)
            if not user:
                bot_instance.send_message_safe(
                    chat_id=chat_id,
                    text="Please use /start to initialize your account first."
                )
                return
            
            # Update activity
            self.user_service.update_user_activity(telegram_id)
            
            # Get trading stats
            stats = self.trading_service.get_user_stats(user['id'])
            positions = self.trading_service.get_user_positions(user['id'])
            
            # Calculate ROI
            roi_percentage = 0.0
            if user['initial_deposit'] > 0:
                roi_percentage = ((user['balance'] - user['initial_deposit']) / user['initial_deposit']) * 100
            
            # Format dashboard
            dashboard_text = f"""
📊 <b>Your Trading Dashboard</b>

💰 <b>Balance:</b> {user['balance']:.4f} SOL
💵 <b>Initial Deposit:</b> {user['initial_deposit']:.4f} SOL
📈 <b>ROI:</b> {roi_percentage:+.2f}%

<b>Trading Summary (7 days):</b>
🔄 Trades: {stats['total_trades']}
💚 Profit: +{stats['total_profit']:.4f} SOL
💔 Loss: -{stats['total_loss']:.4f} SOL
📊 Net: {stats['net_profit']:+.4f} SOL

<b>Active Positions:</b> {len(positions)}
"""
            
            # Add position details if any
            if positions:
                dashboard_text += "\n<b>Recent Positions:</b>\n"
                for i, pos in enumerate(positions[:3]):  # Show top 3
                    pnl = (pos['current_price'] - pos['entry_price']) * pos['amount']
                    pnl_pct = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
                    dashboard_text += f"• {pos['token_name']}: {pnl:+.4f} SOL ({pnl_pct:+.1f}%)\n"
                
                if len(positions) > 3:
                    dashboard_text += f"... and {len(positions) - 3} more\n"
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '💰 Deposit', 'callback_data': 'deposit'}, 
                     {'text': '💸 Withdraw', 'callback_data': 'withdraw'}],
                    [{'text': '📈 Positions', 'callback_data': 'live_positions'}, 
                     {'text': '📜 History', 'callback_data': 'trade_history'}],
                    [{'text': '⚙️ Settings', 'callback_data': 'settings'}, 
                     {'text': '🔄 Refresh', 'callback_data': 'dashboard'}]
                ]
            }
            
            bot_instance.send_message_safe(
                chat_id=chat_id,
                text=dashboard_text,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in dashboard_handler: {e}")
            bot_instance.send_message_safe(
                chat_id=chat_id,
                text="⚠️ Unable to load dashboard. Please try again."
            )
    
    def deposit_handler(self, message: Dict, bot_instance: TelegramBotOptimized):
        """Handle /deposit command"""
        try:
            chat_id = str(message['chat']['id'])
            telegram_id = str(message['from']['id'])
            
            user = self.user_service.get_user(telegram_id)
            if not user:
                bot_instance.send_message_safe(
                    chat_id=chat_id,
                    text="Please use /start to initialize your account first."
                )
                return
            
            # Get admin wallet from environment or config
            admin_wallet = "Soa8DkfSzZEmXLJ2AWEqm76fgrSWYxT5iPg6kDdZbKmx"  # From your logs
            
            deposit_text = f"""
💰 <b>Make a Deposit</b>

Send SOL to this wallet address:
<code>{admin_wallet}</code>

<b>Important:</b>
• Minimum deposit: 0.1 SOL
• Your deposit will be automatically detected
• Trading starts immediately after confirmation
• Keep your receipt for support

<b>Current Balance:</b> {user['balance']:.4f} SOL

After sending, your deposit will appear within 1-5 minutes.
"""
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '📋 Copy Address', 'callback_data': f'copy_address:{admin_wallet}'}],
                    [{'text': '🔍 Check Status', 'callback_data': 'check_deposit'}],
                    [{'text': '🏠 Back to Dashboard', 'callback_data': 'dashboard'}]
                ]
            }
            
            bot_instance.send_message_safe(
                chat_id=chat_id,
                text=deposit_text,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in deposit_handler: {e}")
            bot_instance.send_message_safe(
                chat_id=chat_id,
                text="⚠️ Unable to show deposit info. Please try again."
            )
    
    def help_handler(self, message: Dict, bot_instance: TelegramBotOptimized):
        """Handle /help command"""
        chat_id = str(message['chat']['id'])
        telegram_id = str(message['from']['id'])
        
        # Update activity
        self.user_service.update_user_activity(telegram_id)
        
        help_text = """
🤖 <b>Solana Memecoin Trading Bot Help</b>

<b>📋 Commands:</b>
/start - Initialize your account
/dashboard - View portfolio & stats
/deposit - Add SOL to start trading
/settings - Configure preferences
/help - Show this help

<b>🎯 How It Works:</b>
1. Deposit SOL to your trading wallet
2. Our AI monitors memecoin markets 24/7
3. Automatic trades execute on profitable opportunities
4. Daily profits compound your balance
5. Withdraw anytime to your personal wallet

<b>💡 Features:</b>
• Real-time market analysis
• Risk management & stop losses
• Portfolio diversification
• Daily profit notifications
• Transparent trade history

<b>🛟 Support:</b>
Contact @support for assistance

Ready to start? Use /deposit to fund your account!
"""
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '💰 Make Deposit', 'callback_data': 'deposit'}],
                [{'text': '📊 View Dashboard', 'callback_data': 'dashboard'}],
                [{'text': '❓ How It Works', 'callback_data': 'how_it_works'}]
            ]
        }
        
        bot_instance.send_message_safe(
            chat_id=chat_id,
            text=help_text,
            reply_markup=keyboard
        )
    
    def callback_query_handler(self, callback_query: Dict, bot_instance: TelegramBotOptimized):
        """Handle callback queries efficiently"""
        try:
            chat_id = str(callback_query['message']['chat']['id'])
            message_id = callback_query['message']['message_id']
            data = callback_query['data']
            telegram_id = str(callback_query['from']['id'])
            
            # Answer callback query to remove loading state
            requests.post(
                f"{bot_instance.api_url}/answerCallbackQuery",
                json={'callback_query_id': callback_query['id']},
                timeout=10
            )
            
            # Route to appropriate handler
            if data == 'dashboard':
                # Create fake message for dashboard handler
                fake_message = {
                    'chat': {'id': chat_id},
                    'from': {'id': telegram_id}
                }
                self.dashboard_handler(fake_message, bot_instance)
                
            elif data == 'deposit' or data == 'start_deposit':
                fake_message = {
                    'chat': {'id': chat_id},
                    'from': {'id': telegram_id}
                }
                self.deposit_handler(fake_message, bot_instance)
                
            elif data == 'how_it_works':
                self.how_it_works_callback(chat_id, bot_instance)
                
            elif data.startswith('copy_address:'):
                address = data.split(':', 1)[1]
                bot_instance.send_message_safe(
                    chat_id=chat_id,
                    text=f"📋 Wallet address copied:\n<code>{address}</code>\n\nSend SOL to this address to make a deposit."
                )
                
            else:
                bot_instance.send_message_safe(
                    chat_id=chat_id,
                    text="⚠️ Unknown action. Please try again."
                )
                
        except Exception as e:
            logger.error(f"Error in callback_query_handler: {e}")
    
    def how_it_works_callback(self, chat_id: str, bot_instance: TelegramBotOptimized):
        """Show how the bot works"""
        how_it_works_text = """
🎯 <b>How Our Trading Bot Works</b>

<b>🔍 Market Analysis:</b>
• AI monitors 1000+ Solana memecoins 24/7
• Identifies breakout patterns & volume spikes
• Analyzes social sentiment & whale movements

<b>⚡ Automated Trading:</b>
• Executes trades within milliseconds
• Built-in stop-loss & take-profit
• Portfolio diversification across multiple tokens

<b>📈 Profit Strategy:</b>
• Scalping: Quick 2-5% gains
• Snipe: Early token launches
• Dip buying: Buy low, sell high
• Reversal: Catch trend changes

<b>🛡️ Risk Management:</b>
• Never risk more than 10% per trade
• Smart position sizing
• Emergency stop-loss protection

<b>💰 Profit Distribution:</b>
• 80% goes to your balance
• 20% reinvested for compound growth

Start with just 0.1 SOL and watch your portfolio grow!
"""
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '💰 Start Trading', 'callback_data': 'deposit'}],
                [{'text': '📊 View Examples', 'callback_data': 'trading_examples'}],
                [{'text': '🏠 Back to Menu', 'callback_data': 'dashboard'}]
            ]
        }
        
        bot_instance.send_message_safe(
            chat_id=chat_id,
            text=how_it_works_text,
            reply_markup=keyboard
        )

def register_handlers(bot: TelegramBotOptimized) -> None:
    """Register all production handlers"""
    handlers = ProductionHandlers(bot)
    
    # Command handlers
    bot.add_command_handler('start', handlers.start_handler)
    bot.add_command_handler('dashboard', handlers.dashboard_handler)
    bot.add_command_handler('deposit', handlers.deposit_handler)
    bot.add_command_handler('help', handlers.help_handler)
    
    # Callback handlers
    bot.add_callback_handler('dashboard', handlers.callback_query_handler)
    bot.add_callback_handler('deposit', handlers.callback_query_handler)
    bot.add_callback_handler('start_deposit', handlers.callback_query_handler)
    bot.add_callback_handler('how_it_works', handlers.callback_query_handler)
    bot.add_callback_handler('copy_address', handlers.callback_query_handler)
    
    logger.info("Production handlers registered successfully")