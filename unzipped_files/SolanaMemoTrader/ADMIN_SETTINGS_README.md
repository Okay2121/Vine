# Admin Settings System Documentation

This document provides an overview of the Admin Settings system implemented in the Telegram bot.

## Overview

The Admin Settings system allows administrators to modify key parameters of the bot without requiring code changes. These settings are stored in the database and can be adjusted through the Telegram bot's admin interface.

## Available Settings

The following settings can be configured:

| Setting | Description | Default Value |
|---------|-------------|---------------|
| `min_deposit` | Minimum deposit amount in SOL required to activate the bot | 0.5 |
| `daily_update_hour` | Hour (UTC) for sending daily updates and notifications | 9 |
| `daily_updates_enabled` | Toggle to enable/disable daily trading updates | true |
| `daily_roi_min` | Minimum daily ROI percentage | 0.5 |
| `daily_roi_max` | Maximum daily ROI percentage | 1.5 |
| `loss_probability` | Probability percentage of loss days | 0.2 |
| `support_username` | Telegram username for support contact | @admin |

## Admin Interface

Administrators can adjust these settings through the bot's admin panel:

1. Start the bot and use the `/admin` command (requires admin privileges)
2. Select "Bot Settings" from the admin menu
3. Choose the setting you want to modify:
   - Update Minimum Deposit
   - Edit Notification Time
   - Toggle Daily Updates
   - Manage ROI Settings (provides access to min/max ROI and loss probability)
   - Change Support Username

## Technical Implementation

### Database Structure

Settings are stored in the `SystemSettings` table with the following fields:
- `setting_name`: Unique identifier for the setting
- `setting_value`: The current value of the setting
- `updated_by`: Who last updated the setting
- `last_updated`: When the setting was last updated
- `description`: Human-readable description of the setting

### Helper Functions

The `helpers.py` module provides functions to access settings:

```python
get_min_deposit()              # Returns the minimum deposit amount
get_notification_time()        # Returns the daily notification hour (UTC)
are_daily_updates_enabled()    # Returns whether daily updates are enabled
get_daily_roi_min()            # Returns the minimum daily ROI percentage
get_daily_roi_max()            # Returns the maximum daily ROI percentage
get_loss_probability()         # Returns the probability of loss days
get_support_username()         # Returns the support username
```

### Integration Points

These settings are integrated with several components:

1. `handlers/deposit.py` - Uses the minimum deposit setting to verify sufficient deposits
2. `utils/scheduler.py` - Uses notification time and daily updates toggle to schedule jobs
3. `utils/trading.py` - Uses ROI settings to generate realistic trading outcomes
4. Various UI components - Display support username for contact information

## Testing

A test script (`test_admin_settings_integration.py`) verifies that the admin settings system is working correctly. It checks:

1. Settings are properly stored in the database
2. Helper functions retrieve the correct values
3. Changes to settings are immediately reflected in the application
4. Default values are used when settings are not found

## Default Settings Initialization

The `update_existing_settings.py` script ensures all necessary settings exist in the database with appropriate default values. This script runs during application startup.

## Best Practices

1. Always use the helper functions to access settings instead of hardcoding values
2. New settings should be added to `update_existing_settings.py` with appropriate defaults
3. Add a matching helper function in `helpers.py` for any new setting
4. Implement a UI in the admin panel for adjusting the new setting

## Troubleshooting

If settings are not working correctly:

1. Verify the setting exists in the database using the test script
2. Check that the setting name matches exactly (case-sensitive)
3. Ensure the helper function is being used rather than hardcoded values
4. Verify the UI is correctly updating the database value