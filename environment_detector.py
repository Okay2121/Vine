"""
Environment Detection Utility
=============================
This module detects whether the bot is running on Replit or AWS/other environments
to enable conditional auto-start behavior.
"""

import os
import logging

logger = logging.getLogger(__name__)

def is_replit_environment():
    """
    Detect if we're running on Replit by checking for Replit-specific indicators.
    
    Returns:
        bool: True if running on Replit, False otherwise
    """
    # Check for Replit-specific environment variables
    replit_indicators = [
        'REPLIT_CLUSTER',
        'REPLIT_DB_URL', 
        'REPL_ID',
        'REPL_SLUG',
        'REPLIT_DOMAIN'
    ]
    
    # Check if any Replit indicator is present
    for indicator in replit_indicators:
        if os.environ.get(indicator):
            logger.info(f"Detected Replit environment via {indicator}")
            return True
    
    # Check for explicit environment setting
    env_setting = os.environ.get('BOT_ENVIRONMENT', '').lower()
    if env_setting == 'replit':
        logger.info("Detected Replit environment via BOT_ENVIRONMENT setting")
        return True
    elif env_setting == 'aws':
        logger.info("Detected AWS environment via BOT_ENVIRONMENT setting")
        return False
    
    # Check for AWS-specific indicators
    aws_indicators = [
        'AWS_REGION',
        'AWS_EXECUTION_ENV',
        'AWS_LAMBDA_FUNCTION_NAME'
    ]
    
    for indicator in aws_indicators:
        if os.environ.get(indicator):
            logger.info(f"Detected AWS environment via {indicator}")
            return False
    
    # Default to non-Replit (manual start) if we can't determine
    logger.info("Could not determine environment - defaulting to manual start mode")
    return False

def get_environment_info():
    """
    Get detailed environment information for logging and debugging.
    
    Returns:
        dict: Environment information
    """
    return {
        'is_replit': is_replit_environment(),
        'environment_type': 'replit' if is_replit_environment() else 'aws/manual',
        'auto_start_enabled': is_replit_environment(),
        'detected_indicators': {
            'replit_cluster': bool(os.environ.get('REPLIT_CLUSTER')),
            'repl_id': bool(os.environ.get('REPL_ID')),
            'aws_region': bool(os.environ.get('AWS_REGION')),
            'bot_environment': os.environ.get('BOT_ENVIRONMENT', 'not_set')
        }
    }

def should_auto_start():
    """
    Determine if the bot should auto-start based on the environment.
    
    Returns:
        bool: True if bot should auto-start, False if manual start required
    """
    auto_start = is_replit_environment()
    
    if auto_start:
        logger.info("Auto-start enabled for Replit environment")
    else:
        logger.info("Auto-start disabled - manual start required for AWS/production environment")
    
    return auto_start