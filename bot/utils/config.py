"""
Configuration settings for the Solana Memecoin Trading Bot
Centralizes all configurable parameters and environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")

# Referral system
REFERRAL_REWARD = 0.01  # SOL amount for referrals
MAX_REFERRALS = 100  # Maximum referrals per user

# Trading parameters
DEFAULT_ROI_GOAL = 0.12  # 12% ROI target
MIN_DEPOSIT = 0.1  # Minimum SOL deposit
MAX_DEPOSIT = 1000  # Maximum SOL deposit
AUTO_WITHDRAW_THRESHOLD = 10  # Auto-withdraw profits when reaching this amount

# Performance targets
TRADE_SUCCESS_RATE = 0.92  # Target 92% successful trades
AVERAGE_TRADE_TIME = 20  # Average minutes per trade

# Application paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LOG_FILE = os.path.join(DATA_DIR, "logs.txt")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)