"""
Logger configuration for Solana Memecoin Trading Bot
Provides consistent logging format and error tracking
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from .config import LOG_FILE

def setup_logger():
    """Configure and return a logger that writes to both console and file"""
    
    # Create formatters
    console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console_handler)
    
    # Create file handler
    try:
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setFormatter(logging.Formatter(file_format))
        logger.addHandler(file_handler)
    except Exception as e:
        # Don't fail if file logging is unavailable
        logger.warning(f"Could not set up file logging: {e}")
    
    # Return the configured logger
    return logger

def log_exception(logger, e, context=None):
    """
    Log an exception with detailed traceback and context
    
    Args:
        logger: The logger instance
        e: The exception object
        context: Any additional context about where the error occurred
    """
    error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the error message
    error_msg = [
        f"Exception occurred at {error_time}",
        f"Type: {type(e).__name__}",
        f"Message: {str(e)}",
    ]
    
    if context:
        error_msg.append(f"Context: {context}")
    
    # Add traceback
    error_msg.append("Traceback:")
    for line in traceback.format_exception(type(e), e, e.__traceback__):
        error_msg.append(line.rstrip())
    
    # Log the detailed error
    logger.error("\n".join(error_msg))