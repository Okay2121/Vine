from app import app
import logging
import os
import threading
import time
from dotenv import load_dotenv
from flask import request, Response, jsonify
from utils.deposit_monitor import start_deposit_monitor, stop_deposit_monitor, is_monitor_running
from automated_maintenance import start_maintenance_scheduler, stop_maintenance_scheduler
from database_monitoring import DatabaseMonitor
from environment_detector import should_auto_start, get_environment_info, is_replit_environment
from duplicate_instance_prevention import get_global_instance_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Load environment variables only if not on Replit (Replit handles this automatically)
if not is_replit_environment():
    load_dotenv()
    logger.info("Loaded .env file for non-Replit environment")
else:
    logger.info("Replit environment detected - using built-in environment variables")

# Get the bot token from environment variables
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Global flag to track if bot is running
bot_running = False

# Define basic health-check route for the application
@app.route('/')
def index():
    # Start the bot automatically only in Replit environment
    global bot_running
    
    env_info = get_environment_info()
    
    if should_auto_start() and not bot_running:
        logger.info("Auto-starting bot for Replit environment")
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
        bot_running = True
        bot_status = "auto-started in polling mode"
    elif not should_auto_start():
        bot_status = "manual start required (use /start_bot or run command)"
    else:
        bot_status = "already running in polling mode"
    
    return jsonify({
        "status": "online",
        "message": "Solana Memecoin Trading Bot",
        "environment": env_info['environment_type'],
        "auto_start_enabled": env_info['auto_start_enabled'],
        "bot_status": bot_status,
        "note": "Auto-start only enabled on Replit for remix compatibility"
    })

@app.route('/health')
def health():
    # Check if deposit monitor is running
    deposit_monitor_status = "running" if is_monitor_running() else "stopped"
    
    # Check database health
    try:
        monitor = DatabaseMonitor()
        db_health = monitor.check_database_health()
        db_status = "healthy" if db_health else "error"
        db_size = db_health.get('database_size', 'unknown') if db_health else 'unknown'
    except Exception as e:
        db_status = "error"
        db_size = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "database_size": db_size,
        "bot": "initialized", 
        "deposit_monitor": deposit_monitor_status,
        "maintenance_scheduler": "active"
    })

@app.route('/database/health')
def database_health():
    """Detailed database health endpoint"""
    try:
        monitor = DatabaseMonitor()
        health_report = monitor.check_database_health()
        alerts = monitor.get_usage_alerts()
        
        return jsonify({
            "status": "success",
            "health": health_report,
            "alerts": alerts
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/database/cleanup', methods=['POST'])
def database_cleanup():
    """Manual database cleanup endpoint"""
    try:
        monitor = DatabaseMonitor()
        cleanup_report = monitor.cleanup_old_data(days_to_keep=30)
        
        return jsonify({
            "status": "success",
            "cleanup_report": cleanup_report
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

# Function to send a message to a Telegram chat
def send_telegram_message(chat_id, text, parse_mode="Markdown"):
    """Send a message to a Telegram chat."""
    try:
        import requests
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return None

# Webhook route for Telegram (disabled in favor of polling)
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        logger.info("Webhook received, but webhook mode is disabled in favor of polling mode")
        
        # Don't process webhook updates - we're using polling mode
        return Response("Bot is now running in polling mode. Webhooks are disabled.", status=200)
    
    return Response('Method not allowed', status=405)

# Route to set webhook URL (disabled in favor of polling)
@app.route('/set_webhook')
def set_webhook():
    # Delete any existing webhook since we're using polling mode now
    import requests
    response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    result = response.json()
    
    if result.get("ok", False):
        logger.info("Webhook removed successfully")
    else:
        logger.error(f"Failed to remove webhook: {result}")
    
    # Start the polling bot instead
    start_bot_thread()
    
    return jsonify({
        "status": "polling_mode_active",
        "message": "Bot is now running in polling mode instead of webhook mode for improved reliability.",
        "webhook_status": "removed" if result.get("ok", False) else "webhook_error"
    })

def start_bot_thread():
    """Start the Telegram bot in a separate thread."""
    global bot_running
    # Additional duplicate prevention
    instance_manager = get_global_instance_manager()
    if not instance_manager.acquire_lock():
        logger.warning("Another bot instance detected in start_bot_thread, aborting")
        return False

    
    # Use the token from environment variables
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("No bot token found in environment variables")
        return False
    
    logger.info(f"Starting bot with token: {token[:10]}...")
    
    try:
        # Start the bot in a separate subprocess
        import subprocess
        import sys
        
        # Remove any existing webhook
        import requests
        response = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
        result = response.json()
        
        if result.get("ok", False):
            logger.info("Webhook removed successfully")
        else:
            logger.warning(f"Failed to remove webhook: {result}")
        
        # Import and start the bot directly without subprocess to avoid conflicts
        try:
            # Import the bot module and start it in the current thread
            from bot_v20_runner import run_polling
            
            # Start bot in a background thread (not subprocess) to prevent AWS/Replit conflicts
            def run_bot():
                try:
                    run_polling()
                except Exception as e:
                    logger.error(f"Bot polling error: {e}")
            
            bot_thread = threading.Thread(target=run_bot)
            bot_thread.daemon = True
            bot_thread.start()
            
            logger.info("Started bot polling in background thread (Replit mode)")
            bot_running = True
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return False
        
        # Start the deposit monitor system if not already running
        if not is_monitor_running():
            if start_deposit_monitor():
                logger.info("Deposit monitor started successfully")
            else:
                logger.warning("Failed to start deposit monitor")
        
        # Start the automated database maintenance scheduler
        try:
            start_maintenance_scheduler()
            logger.info("Database maintenance scheduler started successfully")
        except Exception as e:
            logger.warning(f"Failed to start database maintenance scheduler: {e}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error starting the Telegram bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Start bot in a separate thread when the application loads
# using a function called from routes instead of @app.before_first_request which is deprecated
def start_bot_on_first_request():
    logger.info("Starting bot in a background thread on first request")
    bot_thread = threading.Thread(target=start_bot_thread)
    bot_thread.daemon = True  # Thread will exit when main thread exits
    bot_thread.start()

# Auto-start the bot immediately when the module is imported (Replit only)
def auto_start_bot():
    """Auto-start the bot when the application starts (Replit environment only)"""
    global bot_running
    
    if should_auto_start() and not bot_running:
        # Token should already be in environment from .env file
        logger.info("Auto-starting bot on application startup for Replit environment...")
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
    elif not should_auto_start():
        logger.info("Skipping auto-start - manual start required for AWS/production environment")
        logger.info("Use 'python main.py' command or /start_bot endpoint to start the bot")

# Auto-start the bot when this module is imported (conditional)
auto_start_bot()

# Route to manually start the bot
@app.route('/start_bot')
def start_bot_route():
    global bot_running
    if not bot_running:
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
        return jsonify({"status": "starting_bot"})
    else:
        return jsonify({"status": "bot_already_running"})

# Routes to manually control the deposit monitor
@app.route('/deposit_monitor/start')
def start_deposit_monitor_route():
    if is_monitor_running():
        return jsonify({"status": "already_running"})
    
    if start_deposit_monitor():
        return jsonify({"status": "started"})
    else:
        return jsonify({"status": "failed_to_start"})

@app.route('/deposit_monitor/stop')
def stop_deposit_monitor_route():
    if not is_monitor_running():
        return jsonify({"status": "not_running"})
    
    if stop_deposit_monitor():
        return jsonify({"status": "stopped"})
    else:
        return jsonify({"status": "failed_to_stop"})

@app.route('/deposit_monitor/status')
def deposit_monitor_status_route():
    status = "running" if is_monitor_running() else "stopped"
    return jsonify({"status": status})

@app.route('/environment')
def environment_info():
    """Detailed environment information for debugging"""
    env_info = get_environment_info()
    return jsonify({
        "environment_detection": env_info,
        "startup_behavior": {
            "auto_start_enabled": env_info['auto_start_enabled'],
            "startup_mode": "automatic" if env_info['auto_start_enabled'] else "manual",
            "recommended_start_method": "automatic (remix works)" if env_info['auto_start_enabled'] else "python start_bot_manual.py"
        },
        "bot_status": {
            "currently_running": bot_running,
            "process_type": "polling_mode"
        }
    })

@app.route('/admin/deposit_logs')
def admin_deposit_logs_route():
    """API route to retrieve recent deposit logs for admin panel"""
    from app import db
    from models import Transaction, User
    
    try:
        # Get the most recent deposit transactions (limit 50)
        with app.app_context():
            deposits = (
                db.session.query(Transaction, User)
                .join(User, Transaction.user_id == User.id)
                .filter(Transaction.transaction_type == "deposit")
                .order_by(Transaction.timestamp.desc())
                .limit(50)
                .all()
            )
            
            # Format the results - prioritizing telegram_id for user identification
            results = []
            for transaction, user in deposits:
                results.append({
                    "telegram_id": user.telegram_id,
                    "id": transaction.id,
                    "user_id": transaction.user_id,
                    "username": user.username or "N/A",
                    "amount": transaction.amount,
                    "timestamp": transaction.timestamp.isoformat(),
                    "status": transaction.status,
                    "notes": transaction.notes or ""
                })
            
            return jsonify({
                "status": "success",
                "deposits": results
            })
    except Exception as e:
        logger.error(f"Error retrieving deposit logs: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/admin/users')
def admin_users_route():
    """Web route to view all users with detailed information"""
    from app import db
    from models import User, Transaction, Profit, UserStatus, ReferralCode
    from flask import render_template
    from sqlalchemy import func
    
    try:
        with app.app_context():
            # Get all users, ordered by most recent first
            users = User.query.order_by(User.joined_at.desc()).all()
            
            # Get additional information for each user
            user_details = []
            for user in users:
                # Calculate total deposits
                total_deposits = db.session.query(
                    func.sum(Transaction.amount)
                ).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == "deposit",
                    Transaction.status == "completed"
                ).scalar() or 0.0
                
                # Calculate total withdrawals
                total_withdrawn = db.session.query(
                    func.sum(Transaction.amount)
                ).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == "withdraw",
                    Transaction.status == "completed"
                ).scalar() or 0.0
                
                # Calculate total profit
                total_profit = db.session.query(
                    func.sum(Profit.amount)
                ).filter(
                    Profit.user_id == user.id
                ).scalar() or 0.0
                
                # Get referral count
                referral_count = ReferralCode.query.filter_by(
                    inviter_id=user.id
                ).count() if hasattr(ReferralCode, 'inviter_id') else 0
                
                # Format user status
                status = user.status.value if hasattr(user.status, 'value') else str(user.status)
                
                # Append user details
                user_details.append({
                    'user': user,
                    'total_deposits': total_deposits,
                    'total_withdrawn': total_withdrawn,
                    'total_profit': total_profit,
                    'referral_count': referral_count,
                    'status': status
                })
            
            # Render the template with user data
            return render_template('admin_users.html', user_details=user_details)
    
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return render_template('error.html', error=str(e))

# Run the app when this script is executed in development mode
if __name__ == "__main__":
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=start_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    logger.info("Bot thread started")
    
    # Wait a moment to see if the bot starts successfully
    time.sleep(2)
    
    # Run the Flask app (in development mode)
    app.run(host="0.0.0.0", port=5000, debug=True)