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

# Enforce PostgreSQL database usage - critical for production deployment
PRODUCTION_DATABASE_URL = "postgresql://neondb_owner:npg_fckEhtMz23gx@ep-odd-wildflower-a212fu4p-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"

# Get the database URL from environment variables with production fallback
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    logger = logging.getLogger(__name__)
    logger.warning("DATABASE_URL environment variable is not set. Using production PostgreSQL database.")
    db_url = PRODUCTION_DATABASE_URL
else:
    # Fix the DATABASE_URL if it starts with postgres://
    # Postgres URLs should start with postgresql://
    logger = logging.getLogger(__name__)
    if db_url.startswith("postgres://"):
        logger.info("Converting postgres:// to postgresql://")
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    # Validate that we're using PostgreSQL (no SQLite fallback for production)
    if not db_url.startswith("postgresql://"):
        logger.warning(f"Invalid database URL format: {db_url[:20]}... Enforcing production PostgreSQL.")
        db_url = PRODUCTION_DATABASE_URL
    
    logger.info(f"Using PostgreSQL database: {db_url[:40]}...")

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
            'timestamp': 'connected'
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

# This will run the Flask app on port 5000 if directly executed
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
