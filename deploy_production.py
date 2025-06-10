#!/usr/bin/env python3
"""
Production Deployment Script
===========================
Deploy optimized Telegram bot to handle 500+ users efficiently
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionDeployer:
    """Handle production deployment tasks"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.required_files = [
            'production_bot.py',
            'production_config.py',
            'main_production.py',
            'models.py',
            'app.py'
        ]
        
    def check_environment(self):
        """Check required environment variables"""
        required_env = [
            'TELEGRAM_BOT_TOKEN',
            'DATABASE_URL'
        ]
        
        missing = []
        for env_var in required_env:
            if not os.getenv(env_var):
                missing.append(env_var)
        
        if missing:
            logger.error(f"Missing environment variables: {', '.join(missing)}")
            return False
        
        logger.info("Environment variables validated")
        return True
    
    def check_files(self):
        """Check required files exist"""
        missing = []
        for file_path in self.required_files:
            if not (self.project_root / file_path).exists():
                missing.append(file_path)
        
        if missing:
            logger.error(f"Missing required files: {', '.join(missing)}")
            return False
        
        logger.info("Required files validated")
        return True
    
    def install_dependencies(self):
        """Install production dependencies"""
        try:
            logger.info("Installing dependencies...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                'requests', 'sqlalchemy', 'psycopg2-binary',
                'python-dotenv', 'flask', 'psutil'
            ], check=True)
            logger.info("Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    def test_database_connection(self):
        """Test database connectivity"""
        try:
            from production_bot import DatabaseManager
            from production_config import ProductionConfig
            
            logger.info("Testing database connection...")
            db = DatabaseManager(ProductionConfig.DATABASE_URL)
            
            # Test basic query
            result = db.execute_query("SELECT 1 as test", fetch_one=True)
            if result and result[0] == 1:
                logger.info("Database connection successful")
                return True
            else:
                logger.error("Database connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False
    
    def create_systemd_service(self):
        """Create systemd service file for production"""
        service_content = f"""[Unit]
Description=Telegram Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={self.project_root}
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart={sys.executable} main_production.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_path = self.project_root / 'telegram-bot.service'
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        logger.info(f"Systemd service file created: {service_path}")
        logger.info("To install: sudo cp telegram-bot.service /etc/systemd/system/")
        logger.info("Then run: sudo systemctl enable telegram-bot && sudo systemctl start telegram-bot")
    
    def create_nginx_config(self):
        """Create nginx configuration for webhook support"""
        nginx_config = """server {
    listen 80;
    listen 443 ssl;
    server_name your-domain.com;
    
    # SSL configuration (add your certificates)
    # ssl_certificate /path/to/cert.pem;
    # ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /webhook {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}"""
        
        nginx_path = self.project_root / 'nginx-telegram-bot.conf'
        with open(nginx_path, 'w') as f:
            f.write(nginx_config)
        
        logger.info(f"Nginx config created: {nginx_path}")
        logger.info("Copy to /etc/nginx/sites-available/ and enable")
    
    def deploy(self):
        """Run complete deployment process"""
        logger.info("Starting production deployment...")
        
        steps = [
            ("Checking environment", self.check_environment),
            ("Checking files", self.check_files),
            ("Installing dependencies", self.install_dependencies),
            ("Testing database", self.test_database_connection),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            if not step_func():
                logger.error(f"Deployment failed at: {step_name}")
                return False
        
        # Create optional deployment files
        self.create_systemd_service()
        self.create_nginx_config()
        
        logger.info("Deployment completed successfully!")
        logger.info("To start the bot: python main_production.py")
        return True

if __name__ == "__main__":
    deployer = ProductionDeployer()
    success = deployer.deploy()
    sys.exit(0 if success else 1)