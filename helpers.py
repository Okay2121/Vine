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