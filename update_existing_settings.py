#!/usr/bin/env python
"""
Update Existing Settings Script
This script ensures all necessary settings are created in the database
with default values from the config file.
"""

import os
from app import app, db
from models import SystemSettings
from config import (
    MIN_DEPOSIT, 
    DAILY_UPDATE_HOUR,
    SIMULATED_DAILY_ROI_MIN,
    SIMULATED_DAILY_ROI_MAX,
    SIMULATED_LOSS_PROBABILITY
)

def ensure_settings_exist():
    """Ensure all necessary settings exist in the database with default values."""
    with app.app_context():
        # Default settings to create if they don't exist
        default_settings = {
            "min_deposit": str(MIN_DEPOSIT),
            "daily_update_hour": str(DAILY_UPDATE_HOUR),
            "daily_updates_enabled": "true",
            "daily_roi_min": str(SIMULATED_DAILY_ROI_MIN),
            "daily_roi_max": str(SIMULATED_DAILY_ROI_MAX),
            "loss_probability": str(SIMULATED_LOSS_PROBABILITY),
            "support_username": "@admin"  # Default support username
        }
        
        for setting_name, default_value in default_settings.items():
            # Check if setting exists
            setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
            
            if not setting:
                # Create with default value
                setting = SystemSettings(
                    setting_name=setting_name,
                    setting_value=default_value,
                    updated_by="system"
                )
                db.session.add(setting)
                print(f"Created setting {setting_name} with default value: {default_value}")
            else:
                print(f"Setting {setting_name} already exists with value: {setting.setting_value}")
                
        # Commit changes
        db.session.commit()
        print("All settings updated successfully!")
        
def list_all_settings():
    """List all system settings from the database."""
    with app.app_context():
        settings = SystemSettings.query.all()
        
        if not settings:
            print("No settings found in the database.")
            return
        
        print("\n=== Current System Settings ===")
        for setting in settings:
            print(f"{setting.setting_name} = {setting.setting_value}")

if __name__ == "__main__":
    print("Ensuring all necessary settings exist...")
    ensure_settings_exist()
    
    print("\nListing all current settings...")
    list_all_settings()