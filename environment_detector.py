#!/usr/bin/env python3
"""
Environment Detection System
============================
Detects whether the bot is running on Replit or AWS and configures startup behavior accordingly.
"""

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def is_replit_environment():
    """
    Detect if we're running on Replit platform.
    
    Returns:
        bool: True if running on Replit, False otherwise
    """
    # Check for Replit-specific environment variables
    replit_indicators = [
        'REPL_ID',
        'REPL_SLUG', 
        'REPLIT_DB_URL',
        'REPL_OWNER',
        'REPLIT_DOMAINS'
    ]
    
    for indicator in replit_indicators:
        if os.environ.get(indicator):
            return True
    
    # Check for Replit-specific paths
    replit_paths = [
        os.path.expanduser('~'),
        '/opt/virtualenvs/python3'
    ]
    
    for path in replit_paths:
        if Path(path).exists():
            return True
    
    return False

def is_aws_environment():
    """
    Detect if we're running on AWS or similar cloud environment.
    
    Returns:
        bool: True if likely AWS/cloud environment, False otherwise
    """
    # Check for AWS-specific indicators
    aws_indicators = [
        'AWS_REGION',
        'AWS_DEFAULT_REGION',
        'EC2_INSTANCE_ID',
        'AWS_EXECUTION_ENV'
    ]
    
    for indicator in aws_indicators:
        if os.environ.get(indicator):
            return True
    
    # Check if .env file exists (AWS deployment pattern)
    if Path('.env').exists():
        return True
    
    # Check if we're NOT on Replit and have production-like setup
    if not is_replit_environment():
        # Look for production indicators
        production_indicators = [
            os.environ.get('NODE_ENV') == 'production',
            os.environ.get('FLASK_ENV') == 'production',
            os.environ.get('ENVIRONMENT') == 'production',
            Path('/var/log').exists(),  # Linux system
            Path('/etc/systemd').exists()  # Systemd (common on AWS Linux)
        ]
        
        if any(production_indicators):
            return True
    
    return False

def is_direct_execution():
    """
    Check if the bot is being executed directly (python bot_v20_runner.py).
    
    Returns:
        bool: True if direct execution, False if imported
    """
    # Check the main module name in the call stack
    import inspect
    
    for frame_record in inspect.stack():
        frame = frame_record.frame
        if frame.f_globals.get('__name__') == '__main__':
            filename = frame.f_code.co_filename
            if 'bot_v20_runner.py' in filename:
                return True
    
    return False

def should_auto_start():
    """
    Determine if the bot should auto-start based on environment.
    
    Returns:
        bool: True if auto-start should be enabled, False otherwise
    """
    # Auto-start only on Replit when accessed via web interface
    return is_replit_environment() and not is_direct_execution()

def get_environment_info():
    """
    Get comprehensive environment information.
    
    Returns:
        dict: Environment details
    """
    env_type = "unknown"
    
    if is_replit_environment():
        env_type = "replit"
    elif is_aws_environment():
        env_type = "aws"
    else:
        env_type = "local"
    
    return {
        "environment_type": env_type,
        "is_replit": is_replit_environment(),
        "is_aws": is_aws_environment(),
        "is_direct_execution": is_direct_execution(),
        "auto_start_enabled": should_auto_start(),
        "env_file_exists": Path('.env').exists(),
        "repl_id": os.environ.get('REPL_ID'),
        "aws_region": os.environ.get('AWS_REGION'),
        "execution_path": sys.argv[0] if sys.argv else "unknown"
    }

def setup_logging_for_environment():
    """Setup appropriate logging configuration based on environment."""
    env_info = get_environment_info()
    
    if env_info["environment_type"] == "replit":
        # Replit-friendly logging
        logging.basicConfig(
            format='%(asctime)s [REPLIT] %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        logger.info("🎯 Replit Environment Detected")
    elif env_info["environment_type"] == "aws":
        # AWS-friendly logging with more detail
        logging.basicConfig(
            format='%(asctime)s [AWS] %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        logger.info("☁️  AWS Environment Detected")
    else:
        # Local development logging
        logging.basicConfig(
            format='%(asctime)s [LOCAL] %(name)s - %(levelname)s - %(message)s',
            level=logging.DEBUG
        )
        logger.info("💻 Local Environment Detected")
    
    # Log environment details
    logger.info(f"Environment Info: {env_info}")
    
    return env_info

if __name__ == "__main__":
    # Test the environment detection
    info = setup_logging_for_environment()
    print("Environment Detection Results:")
    for key, value in info.items():
        print(f"  {key}: {value}")