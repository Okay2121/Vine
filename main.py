from app import app
import logging
import os
import threading
import time
from dotenv import load_dotenv
from flask import request, Response, jsonify
from utils.deposit_monitor import start_deposit_monitor, stop_deposit_monitor, is_monitor_running

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variables with fallback
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7562541416:AAEET_c3AE1KQuhYYJAHSg7SlCaWbVBg-CU')

# Global flag to track if bot is running
bot_running = False

# Define basic health-check route for the application
@app.route('/')
def index():
    # Start the bot automatically in polling mode
    global bot_running
    
    if not bot_running:
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
        bot_running = True
    
    return jsonify({
        "status": "online",
        "message": "Solana Memecoin Trading Bot",
        "bot_status": "running in polling mode",
        "note": "Bot is running in polling mode for improved reliability"
    })

@app.route('/health')
def health():
    # Check if deposit monitor is running
    deposit_monitor_status = "running" if is_monitor_running() else "stopped"
    
    return jsonify({
        "status": "healthy",
        "database": "connected",
        "bot": "initialized",
        "deposit_monitor": deposit_monitor_status
    })

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
    
    # Set the embedded token directly in environment
    os.environ['TELEGRAM_BOT_TOKEN'] = '7562541416:AAEET_c3AE1KQuhYYJAHSg7SlCaWbVBg-CU'
    token = '7562541416:AAEET_c3AE1KQuhYYJAHSg7SlCaWbVBg-CU'
    
    logger.info(f"Starting bot with embedded token: {token[:10]}...")
    
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
        
        # Try v20 runner first, then fall back to v13 if needed
        try:
            # Start the polling bot in a separate process using v20 compatible runner
            bot_process = subprocess.Popen([sys.executable, 'bot_v20_runner.py'])
            
            if bot_process.poll() is None:
                logger.info("Started bot polling in background (v20)")
                bot_running = True
            else:
                # If v20 fails, try the original polling runner
                logger.warning("v20 bot runner failed, trying v13 compatible runner")
                bot_process = subprocess.Popen([sys.executable, 'bot_polling_runner.py'])
                
                if bot_process.poll() is None:
                    logger.info("Started bot polling in background (v13)")
                    bot_running = True
                else:
                    logger.error(f"Bot process exited immediately with code {bot_process.returncode}")
                    return False
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return False
        
        # Start the deposit monitor system if not already running
        if not is_monitor_running():
            if start_deposit_monitor():
                logger.info("Deposit monitor started successfully")
            else:
                logger.warning("Failed to start deposit monitor")
        
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

# Auto-start the bot immediately when the module is imported
def auto_start_bot():
    """Auto-start the bot when the application starts"""
    global bot_running
    if not bot_running:
        # Set the token and start immediately
        os.environ['TELEGRAM_BOT_TOKEN'] = '7562541416:AAEET_c3AE1KQuhYYJAHSg7SlCaWbVBg-CU'
        logger.info("Auto-starting bot on application startup...")
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()

# Auto-start the bot when this module is imported
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