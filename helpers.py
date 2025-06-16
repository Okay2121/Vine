#!/usr/bin/env python
"""
Helper functions for accessing system settings across the application
"""

from app import app
from models import SystemSettings
import config

def get_system_setting(setting_name, default_value=None):
    """
    Get a system setting from the database, or return a default value if not found.
    
    Args:
        setting_name: The name of the setting to retrieve
        default_value: The default value to return if the setting is not found
        
    Returns:
        The setting value or the default value
    """
    with app.app_context():
        setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
        if setting:
            return setting.setting_value
        return default_value

def get_min_deposit():
    """Get the minimum deposit amount."""
    min_deposit = get_system_setting('min_deposit', config.MIN_DEPOSIT)
    return float(min_deposit)

def get_notification_time():
    """Get the daily notification hour."""
    notification_time = get_system_setting('daily_update_hour', config.DAILY_UPDATE_HOUR)
    return int(notification_time)

def are_daily_updates_enabled():
    """Check if daily updates are enabled."""
    enabled = get_system_setting('daily_updates_enabled', 'true')
    return enabled.lower() == 'true'

def get_daily_roi_min():
    """Get the minimum daily ROI percentage."""
    roi_min = get_system_setting('daily_roi_min', config.SIMULATED_DAILY_ROI_MIN)
    return float(roi_min)

def get_daily_roi_max():
    """Get the maximum daily ROI percentage."""
    roi_max = get_system_setting('daily_roi_max', config.SIMULATED_DAILY_ROI_MAX)
    return float(roi_max)

def get_support_username():
    """Get the support username."""
    support_username = get_system_setting('support_username', config.SUPPORT_USERNAME)
    return support_username

def get_global_deposit_wallet():
    """Get the global deposit wallet address from database or fallback to config."""
    deposit_wallet = get_system_setting('deposit_wallet', config.GLOBAL_DEPOSIT_WALLET)
    return deposit_wallet

def set_system_setting(setting_name, setting_value, updated_by=None):
    """
    Set a system setting in the database.
    
    Args:
        setting_name: The name of the setting to set
        setting_value: The value to set
        updated_by: User ID who updated the setting (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with app.app_context():
            from models import SystemSettings
            from app import db
            
            # Check if setting exists and update, or create new setting
            setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
            
            if setting:
                setting.setting_value = setting_value
                if updated_by:
                    setting.updated_by = str(updated_by)
            else:
                new_setting = SystemSettings(
                    setting_name=setting_name,
                    setting_value=setting_value,
                    updated_by=str(updated_by) if updated_by else None
                )
                db.session.add(new_setting)
                
            db.session.commit()
            return True
            
    except Exception as e:
        import logging
        logging.error(f"Error setting system setting {setting_name}: {str(e)}")
        return False

def update_env_variable(key, value):
    """
    Update an environment variable in the .env file.
    
    Args:
        key: The environment variable name
        value: The new value to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import os
        import re
        
        env_file_path = '.env'
        
        # Read current .env file
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
        
        # Find and update the line, or add it if not found
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break
        
        # If not found, add the new variable
        if not updated:
            lines.append(f"{key}={value}\n")
        
        # Write back to .env file
        with open(env_file_path, 'w') as f:
            f.writelines(lines)
            
        import logging
        logging.info(f"Updated .env file: {key}={value}")
        return True
        
    except Exception as e:
        import logging
        logging.error(f"Error updating .env file: {str(e)}")
        return False

def update_all_user_deposit_wallets():
    """
    Update all user deposit wallets to use the current global deposit wallet.
    This is called when admin changes the global wallet address.
    
    Returns:
        int: Number of users updated
    """
    try:
        with app.app_context():
            from models import User
            from app import db
            
            current_wallet = get_global_deposit_wallet()
            
            # Update all users to use the new global deposit wallet
            updated_count = User.query.update({User.deposit_wallet: current_wallet})
            db.session.commit()
            
            import logging
            logging.info(f"Updated {updated_count} users to use new deposit wallet: {current_wallet}")
            return updated_count
            
    except Exception as e:
        import logging
        logging.error(f"Error updating user deposit wallets: {str(e)}")
        return 0
def update_env_variable_aws_safe(key, value):
    """
    AWS-safe environment variable update with multiple fallback strategies.
    
    Args:
        key: The environment variable name
        value: The new value to set
        
    Returns:
        bool: True if any update method succeeded, False otherwise
    """
    success_methods = []
    
    # Method 1: Update in-memory environment (always works)
    try:
        os.environ[key] = value
        success_methods.append("in-memory")
        import logging
        logging.info(f"Updated {key} in memory")
    except Exception as e:
        import logging
        logging.error(f"Failed to update {key} in memory: {e}")
    
    # Method 2: Try to update .env file (may fail on read-only systems)
    try:
        env_file_path = '.env'
        
        if os.path.exists(env_file_path) and os.access(env_file_path, os.W_OK):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
            
            # Find and update the line, or add it if not found
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break
            
            # If not found, add the new variable
            if not updated:
                lines.append(f"{key}={value}\n")
            
            # Write back to .env file
            with open(env_file_path, 'w') as f:
                f.writelines(lines)
                
            success_methods.append(".env file")
            import logging
            logging.info(f"Updated {key} in .env file")
            
        else:
            import logging
            logging.warning(f".env file not writable or missing - using in-memory fallback for {key}")
            
    except Exception as e:
        import logging
        logging.error(f"Error updating .env file for {key}: {str(e)}")
    
    # Method 3: Try to update system environment (for systemd services)
    try:
        if os.environ.get('BOT_ENVIRONMENT') == 'aws':
            # For AWS, we rely on in-memory and .env file updates
            pass
    except Exception as e:
        import logging
        logging.error(f"Error in system environment update for {key}: {e}")
    
    return len(success_methods) > 0

def ensure_file_permissions(file_path, mode=0o644):
    """
    Ensure file has proper permissions, with fallback for different environments.
    
    Args:
        file_path: Path to the file
        mode: Desired file mode (default: 0o644)
    """
    try:
        if os.path.exists(file_path):
            os.chmod(file_path, mode)
            return True
    except (OSError, PermissionError) as e:
        import logging
        logging.warning(f"Could not set permissions for {file_path}: {e}")
        return False
    return False

def create_temp_file_aws_safe(prefix="temp_", suffix=".tmp"):
    """
    Create a temporary file that works across all deployment environments.
    
    Args:
        prefix: File prefix
        suffix: File suffix
        
    Returns:
        str: Path to created temporary file
    """
    import tempfile
    try:
        # Use system temp directory
        temp_dir = tempfile.gettempdir()
        fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=temp_dir)
        os.close(fd)  # Close file descriptor, keep the file
        return temp_path
    except Exception as e:
        import logging
        logging.error(f"Error creating temp file: {e}")
        # Fallback to current directory
        import uuid
        fallback_path = f"{prefix}{uuid.uuid4().hex[:8]}{suffix}"
        return fallback_path

def detect_deployment_environment():
    """
    Detect the current deployment environment with enhanced AWS support.
    
    Returns:
        str: 'replit', 'aws', or 'local'
    """
    # Check for explicit environment variable
    env_override = os.environ.get('BOT_ENVIRONMENT', '').lower()
    if env_override in ['aws', 'replit', 'local']:
        return env_override
    
    # AWS detection indicators
    aws_indicators = [
        os.path.exists('/opt/aws'),  # AWS CLI installed
        os.environ.get('AWS_REGION'),  # AWS region set
        os.environ.get('AWS_EXECUTION_ENV'),  # AWS execution environment
        'amazonaws.com' in os.environ.get('AWS_LAMBDA_RUNTIME_API', ''),
        os.path.exists('/var/task'),  # Lambda task directory
    ]
    
    if any(aws_indicators):
        return 'aws'
    
    # Replit detection indicators  
    replit_indicators = [
        os.environ.get('REPL_ID'),
        os.environ.get('REPL_SLUG'),
        os.environ.get('REPLIT_DB_URL'),
        os.path.exists(os.path.expanduser('~')),
    ]
    
    if any(replit_indicators):
        return 'replit'
    
    return 'local'

def get_deployment_config():
    """
    Get deployment-specific configuration.
    
    Returns:
        dict: Configuration for the current environment
    """
    env = detect_deployment_environment()
    
    configs = {
        'replit': {
            'auto_start': True,
            'temp_dir': '/tmp',
            'log_level': 'DEBUG',
            'worker_processes': 1,
        },
        'aws': {
            'auto_start': False,
            'temp_dir': tempfile.gettempdir(),
            'log_level': 'INFO',
            'worker_processes': 2,
        },
        'local': {
            'auto_start': False,
            'temp_dir': tempfile.gettempdir(),
            'log_level': 'DEBUG', 
            'worker_processes': 1,
        }
    }
    
    return configs.get(env, configs['local'])
