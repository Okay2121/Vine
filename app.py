import os
import logging
import time
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, create_engine
from sqlalchemy.exc import OperationalError, DisconnectionError
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import urlparse
from database_connection_handler import initialize_database_handler, get_database_status


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Get the database URL from environment variables with production fallback
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    # Use the production Neon database you provided
    db_url = "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    logger = logging.getLogger(__name__)
    logger.info("Using production Neon database URL")
else:
    # Fix the DATABASE_URL if it starts with postgres://
    # Postgres URLs should start with postgresql://
    logger = logging.getLogger(__name__)
    if db_url.startswith("postgres://"):
        logger.info("Converting postgres:// to postgresql://")
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    logger.info(f"Using PostgreSQL database: {db_url[:40]}...")

# Production-optimized database configuration for 500+ users
from sqlalchemy import NullPool

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "poolclass": NullPool,  # No persistent connections - creates new ones as needed
    "pool_pre_ping": True,
    "pool_recycle": 600,
    "connect_args": {
        "sslmode": "require",
        "connect_timeout": 30,
        "application_name": "telegram_bot_production_500_users",
        "keepalives_idle": 600,
        "keepalives_interval": 60,
        "keepalives_count": 3
    } if db_url.startswith("postgresql://") else {}
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

logger = logging.getLogger(__name__)

def retry_database_operation(operation, max_retries=3, delay=2):
    """Retry database operations with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return operation()
        except (OperationalError, DisconnectionError) as e:
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} database operation attempts failed")
                raise e

def create_tables_with_retry():
    """Create database tables with retry logic."""
    def create_operation():
        db.create_all()
        logger.info("Database tables created successfully")
        return True
    
    return retry_database_operation(create_operation)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401

    try:
        create_tables_with_retry()
    except Exception as e:
        logger.error(f"Error creating database tables after retries: {e}")
        # Continue running even if table creation fails initially

# Health check endpoint for monitoring database connectivity
@app.route('/health')
def health_check():
    """Health check endpoint to verify database connectivity"""
    def test_connection():
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    
    try:
        retry_database_operation(test_connection, max_retries=2, delay=1)
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': str(time.time())
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': str(time.time())
        }), 500

# Database status endpoint for deployment monitoring
@app.route('/db-status')
def database_status():
    """Detailed database status for deployment monitoring"""
    try:
        with db.engine.connect() as connection:
            # Test connection and get database info
            result = connection.execute(text("SELECT version()"))
            row = result.fetchone()
            version = row[0] if row else "Unknown"
            
            # Check table count
            result = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            row = result.fetchone()
            table_count = row[0] if row else 0
            
        return jsonify({
            'status': 'connected',
            'postgresql_version': version[:50] + "..." if len(version) > 50 else version,
            'table_count': int(table_count),
            'database_url_prefix': db_url[:30] + "..." if len(db_url) > 30 else db_url
        }), 200
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Database stability monitoring endpoint
@app.route('/db-stability')
def database_stability():
    """Check database stability system status"""
    try:
        from database_stability_system import get_database_health_status
        status = get_database_health_status()
        
        return jsonify({
            'stability_system': 'active',
            'database_healthy': status['healthy'],
            'last_health_check': status['last_check'],
            'failed_operations': status['failed_operations'],
            'monitoring_active': status['monitoring']
        }), 200
    except Exception as e:
        return jsonify({
            'stability_system': 'error',
            'error': str(e)
        }), 500

@app.route('/performance')
def performance_metrics():
    """Performance metrics for 500+ user optimization"""
    try:
        from performance_optimizer import get_performance_report
        report = get_performance_report()
        return jsonify(report), 200
    except Exception as e:
        return jsonify({
            'error': str(e),
            'fallback_metrics': {
                'timestamp': str(time.time()),
                'status': 'metrics_unavailable'
            }
        }), 500

@app.route('/bot-optimization')
def bot_optimization_status():
    """Bot optimization status for production"""
    try:
        from performance_optimizer import performance_optimizer
        metrics = performance_optimizer.get_metrics()
        
        return jsonify({
            'optimization_active': True,
            'polling_config': {
                'timeout': 30,
                'read_latency': 5,
                'allowed_updates': ['message', 'callback_query']
            },
            'database_config': {
                'pool_type': 'NullPool',
                'connection_strategy': 'create_on_demand',
                'batch_processing': True
            },
            'performance_metrics': metrics,
            'target_capacity': '500+ users'
        }), 200
    except Exception as e:
        return jsonify({
            'optimization_active': False,
            'error': str(e)
        }), 500

# This will run the Flask app on port 5000 if directly executed
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
