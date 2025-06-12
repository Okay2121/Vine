"""
Startup Configuration Manager
============================
Centralized configuration for bot startup behavior across different environments.
"""

import os
import logging
from environment_detector import is_replit_environment, get_environment_info

logger = logging.getLogger(__name__)

class StartupConfig:
    """Manages startup configuration based on environment detection"""
    
    def __init__(self):
        self.env_info = get_environment_info()
        self.is_replit = self.env_info['is_replit']
        
    def should_auto_start(self):
        """Determine if bot should auto-start"""
        return self.is_replit
    
    def get_startup_message(self):
        """Get appropriate startup message for the environment"""
        if self.is_replit:
            return "Auto-start enabled for Replit environment"
        else:
            return "Manual start mode - use 'python start_bot_manual.py' to start"
    
    def get_environment_summary(self):
        """Get a summary of the current environment"""
        return {
            'environment_type': self.env_info['environment_type'],
            'auto_start_enabled': self.env_info['auto_start_enabled'],
            'startup_mode': 'automatic' if self.is_replit else 'manual',
            'detected_indicators': self.env_info['detected_indicators']
        }
    
    def log_startup_info(self):
        """Log startup information for debugging"""
        summary = self.get_environment_summary()
        logger.info(f"Environment: {summary['environment_type']}")
        logger.info(f"Auto-start: {'enabled' if summary['auto_start_enabled'] else 'disabled'}")
        logger.info(f"Startup mode: {summary['startup_mode']}")
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Environment indicators: {summary['detected_indicators']}")

# Global startup configuration instance
startup_config = StartupConfig()