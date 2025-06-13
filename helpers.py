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