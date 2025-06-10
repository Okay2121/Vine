#!/usr/bin/env python3
"""
Production Main Entry Point
===========================
Optimized Telegram bot with deposit monitoring integration for 500+ users
"""

import os
import sys
import threading
import logging
import time
from datetime import datetime
from flask import Flask
from production_bot import ProductionBot, BotConfig
from production_config import ProductionConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import existing services
try:
    from utils.deposit_monitor import DepositMonitor
    from app import app as flask_app
    DEPOSIT_MONITOR_AVAILABLE = True
except ImportError:
    logger.warning("Deposit monitor not available, will run bot only")
    DEPOSIT_MONITOR_AVAILABLE = False
    flask_app = Flask(__name__)

class ProductionIntegration:
    """Integrates optimized bot with existing deposit monitoring"""
    
    def __init__(self):
        self.bot = None
        self.deposit_monitor = None
        self.flask_app = flask_app
        self.running = False
        
    def initialize_bot(self):
        """Initialize the production bot"""
        try:
            if not ProductionConfig.validate():
                raise ValueError("Invalid configuration")
            
            config = BotConfig(
                bot_token=ProductionConfig.TELEGRAM_BOT_TOKEN,
                database_url=ProductionConfig.DATABASE_URL,
                admin_user_id=ProductionConfig.ADMIN_USER_ID,
                polling_timeout=ProductionConfig.POLLING_TIMEOUT,
                max_concurrent_users=500,
                cache_ttl=ProductionConfig.CACHE_TTL_SECONDS,
                rate_limit_messages=ProductionConfig.RATE_LIMIT_MESSAGES,
                rate_limit_window=ProductionConfig.RATE_LIMIT_WINDOW
            )
            
            self.bot = ProductionBot(config)
            self.register_handlers()
            logger.info("Production bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def register_handlers(self):
        """Register all bot handlers"""
        # Import and register handlers
        from production_bot import (
            start_handler, dashboard_handler, deposit_handler, 
            help_handler, callback_handler
        )
        
        # Command handlers
        self.bot.add_command_handler('start', start_handler)
        self.bot.add_command_handler('dashboard', dashboard_handler)
        self.bot.add_command_handler('deposit', deposit_handler)
        self.bot.add_command_handler('help', help_handler)
        
        # Callback handlers  
        self.bot.add_callback_handler('dashboard', callback_handler)
        self.bot.add_callback_handler('deposit', callback_handler)
        self.bot.add_callback_handler('how_it_works', callback_handler)
        self.bot.add_callback_handler('copy:', callback_handler)
        self.bot.add_callback_handler('check_deposit', callback_handler)
        self.bot.add_callback_handler('withdraw', callback_handler)
        self.bot.add_callback_handler('positions', callback_handler)
        self.bot.add_callback_handler('history', callback_handler)
        
        logger.info("Bot handlers registered")
    
    def initialize_deposit_monitor(self):
        """Initialize deposit monitoring if available"""
        if not DEPOSIT_MONITOR_AVAILABLE:
            logger.info("Deposit monitor not available, skipping")
            return
        
        try:
            # Initialize deposit monitor with existing logic
            self.deposit_monitor = DepositMonitor()
            logger.info("Deposit monitor initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize deposit monitor: {e}")
            self.deposit_monitor = None
    
    def start_deposit_monitoring(self):
        """Start deposit monitoring in background thread"""
        if not self.deposit_monitor:
            return
        
        def monitor_loop():
            while self.running:
                try:
                    self.deposit_monitor.run_scan_cycle()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Error in deposit monitor: {e}")
                    time.sleep(60)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Deposit monitoring started")
    
    def start_flask_server(self):
        """Start Flask server in background thread"""
        def flask_server():
            try:
                self.flask_app.run(
                    host='0.0.0.0',
                    port=5000,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"Flask server error: {e}")
        
        flask_thread = threading.Thread(target=flask_server, daemon=True)
        flask_thread.start()
        logger.info("Flask server started on port 5000")
    
    def run(self):
        """Run the complete production system"""
        try:
            logger.info("Starting production system...")
            ProductionConfig.print_config()
            
            # Initialize components
            self.initialize_bot()
            self.initialize_deposit_monitor()
            
            self.running = True
            
            # Start background services
            self.start_flask_server()
            self.start_deposit_monitoring()
            
            # Start bot (main thread)
            logger.info("Production system fully initialized, starting bot...")
            self.bot.run()
            
        except KeyboardInterrupt:
            logger.info("Shutting down production system...")
            self.running = False
        except Exception as e:
            logger.error(f"Production system error: {e}")
            sys.exit(1)

# Enhanced handlers for production
def enhanced_start_handler(message, bot):
    """Enhanced start handler with activity tracking"""
    from production_bot import start_handler
    
    # Track user activity
    telegram_id = str(message['from']['id'])
    bot.queue_db_operation(
        "UPDATE \"user\" SET last_activity = :now WHERE telegram_id = :telegram_id",
        {"telegram_id": telegram_id, "now": datetime.utcnow()}
    )
    
    # Call original handler
    start_handler(message, bot)

def enhanced_dashboard_handler(message, bot):
    """Enhanced dashboard with real-time position data"""
    from production_bot import dashboard_handler
    
    # Invalidate cache to get fresh data
    telegram_id = str(message['from']['id'])
    user = bot.get_user_cached(telegram_id)
    if user:
        bot.cache.delete(f"user:{telegram_id}")
        bot.cache.delete(f"positions:{user['id']}")
        bot.cache.delete(f"stats:{user['id']}")
    
    # Call original handler
    dashboard_handler(message, bot)

def enhanced_deposit_handler(message, bot):
    """Enhanced deposit handler with real-time status"""
    from production_bot import deposit_handler
    chat_id = str(message['chat']['id'])
    telegram_id = str(message['from']['id'])
    
    # Check for recent deposits
    user = bot.get_user_cached(telegram_id)
    if user:
        try:
            recent_deposits = bot.db.execute_query(
                """
                SELECT amount, timestamp FROM transaction 
                WHERE user_id = :user_id AND transaction_type = 'deposit' 
                AND timestamp > :recent
                ORDER BY timestamp DESC LIMIT 3
                """,
                {
                    "user_id": user['id'],
                    "recent": datetime.utcnow() - timedelta(hours=24)
                }
            )
            
            if recent_deposits:
                deposit_list = []
                for dep in recent_deposits:
                    deposit_list.append(f"• {dep[0]:.4f} SOL - {dep[1].strftime('%H:%M')}")
                
                recent_text = "\n<b>Recent deposits (24h):</b>\n" + "\n".join(deposit_list) + "\n\n"
            else:
                recent_text = ""
        except:
            recent_text = ""
    else:
        recent_text = ""
    
    # Call original handler with enhancement
    deposit_handler(message, bot)

# Additional production endpoints
@flask_app.route('/bot-status')
def bot_status():
    """Bot status endpoint for monitoring"""
    from flask import jsonify
    
    try:
        return jsonify({
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat(),
            'config': {
                'polling_timeout': ProductionConfig.POLLING_TIMEOUT,
                'cache_ttl': ProductionConfig.CACHE_TTL_SECONDS,
                'rate_limit': f"{ProductionConfig.RATE_LIMIT_MESSAGES}/{ProductionConfig.RATE_LIMIT_WINDOW}s"
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@flask_app.route('/performance')
def performance_metrics():
    """Performance metrics endpoint"""
    from flask import jsonify
    import psutil
    
    try:
        process = psutil.Process()
        return jsonify({
            'cpu_percent': process.cpu_percent(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'threads': process.num_threads(),
            'connections': len(process.connections()),
            'uptime_seconds': time.time() - process.create_time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def main():
    """Main entry point"""
    try:
        integration = ProductionIntegration()
        integration.run()
    except Exception as e:
        logger.error(f"Failed to start production system: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()