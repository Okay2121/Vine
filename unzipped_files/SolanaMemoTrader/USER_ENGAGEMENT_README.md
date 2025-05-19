# User Engagement and Behavioral Triggers System

This document outlines the behavioral triggers and user engagement features implemented in the SolanaMemobot.

## Overview

The engagement system is designed to increase user interaction with three main behavioral triggers:

1. **Daily Profit Updates** - Sent daily at 9:00 UTC
2. **Milestone Achievement Notifications** - Triggered when specific profit/streak thresholds are reached
3. **Inactivity Nudges** - Sent to users inactive for 3+ days

These triggers aim to improve user retention by providing timely, relevant information that encourages continued interaction.

## 1. Daily Profit Updates

### Implementation

Daily updates are configured to send at 9:00 UTC (configurable in `config.py`), providing users with:

- Previous day's profit amount and percentage
- Current balance and total profit
- Progress toward monthly goals
- Win rate and other performance metrics
- One-click access to key features via buttons

### Customization

- Adjust timing in `config.py` by changing `DAILY_UPDATE_HOUR`
- Enable/disable via admin panel or by setting `DAILY_UPDATES_ENABLED` to `False`

## 2. Milestone Achievement Notifications

### Profit Milestones

Triggered when users reach specific profit percentage thresholds:
- 10%, 25%, 50%, 75%, and 100% profit milestones

Features:
- Celebratory messages tailored to the milestone level
- Growth projections showing potential future earnings
- Compound growth calculations
- Projection of time to reach next milestone

### Streak Milestones

Triggered when users maintain consistent profitable days:
- 3, 5, 7, 10, and 14-day streak milestones

Features:
- Personalized congratulatory messages with achievement context 
- Streak profit calculations
- Growth metrics and performance statistics

## 3. Inactivity Nudges

Sent to users who haven't interacted with the bot for 3+ days, with:

- Personalized messages based on inactivity duration
- Current bot performance status
- Win rate and other performance statistics
- Quick access buttons to key features

Messages become progressively more urgent the longer a user remains inactive.

## Implementation Details

### Key Files

- `utils/notifications.py` - Contains the core notification logic
- `utils/scheduler.py` - Manages scheduled triggers
- `utils/engagement.py` - Handles engagement message logic
- `config.py` - Contains configuration settings for thresholds

### Configuration

Adjust engagement settings in `config.py`:

```python
# User Engagement Settings
PROFIT_MILESTONES = [10, 25, 50, 75, 100]  # Profit percentage milestones
STREAK_MILESTONES = [3, 5, 7, 10, 14]  # Consecutive profitable days milestones
INACTIVITY_THRESHOLD = 3  # Days of inactivity before sending a reminder
```

## Best Practices

1. **Message Timing**: Avoid sending too many notifications (max one per day)
2. **Personalization**: Use username and personal stats to create relevance
3. **Clear CTAs**: Each message includes clear buttons for next actions
4. **Value First**: Focus on providing valuable information before asking for action
5. **Context Awareness**: Messages adapt based on user history and performance

## Metric Tracking

The system tracks user response rates to different trigger types in the database, allowing for optimization of message content and timing.