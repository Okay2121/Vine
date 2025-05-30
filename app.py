import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Get the database URL from environment variables
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    logger = logging.getLogger(__name__)
    logger.warning("DATABASE_URL environment variable is not set. Using SQLite database.")
    # Use SQLite for development/testing
    db_url = "sqlite:///solana_memecoin_bot.db"
else:
    # Fix the DATABASE_URL if it starts with postgres:// or https://
    # Postgres URLs should start with postgresql://
    logger = logging.getLogger(__name__)
    if db_url.startswith("postgres://"):
        logger.info("Converting postgres:// to postgresql://")
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    elif db_url.startswith("https://"):
        logger.warning("Invalid database URL format. Using SQLite database instead.")
        db_url = "sqlite:///solana_memecoin_bot.db"
    
    logger.info(f"Using database URL: {db_url[:10]}...")

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "connect_args": {
        "sslmode": "require",
        "connect_timeout": 30,
        "application_name": "solana_memecoin_bot"
    } if db_url.startswith("postgresql://") else {}
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

logger = logging.getLogger(__name__)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401

    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Health check endpoint for monitoring database connectivity
@app.route('/health')
def health_check():
    """Health check endpoint to verify database connectivity"""
    try:
        # Test database connection
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': db.func.now()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

# Database status endpoint for deployment monitoring
@app.route('/db-status')
def database_status():
    """Detailed database status for deployment monitoring"""
    try:
        with db.engine.connect() as connection:
            # Test connection and get database info
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            
            # Check table count
            result = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.fetchone()[0]
            
        return jsonify({
            'status': 'connected',
            'postgresql_version': version,
            'table_count': table_count,
            'connection_pool_size': db.engine.pool.size(),
            'database_url_prefix': db_url[:30] + "..." if len(db_url) > 30 else db_url
        }), 200
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# This will run the Flask app on port 5000 if directly executed
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
