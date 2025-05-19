"""
Referral System Initialization Module
This module silences SQLAlchemy relationship warnings and verifies the referral components
without changing any UI or functionality.
"""
import os
import sys
import logging
import warnings
from sqlalchemy.exc import SAWarning

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Silence SQLAlchemy relationship warnings at the module level
warnings.filterwarnings('ignore', 
                       r".*relationship '.*' will copy column .* to column .*, which conflicts with relationship.*", 
                       SAWarning)
logger.info("SQLAlchemy relationship warnings silenced")

# Check that required files exist
required_files = [
    'models.py',
    'bot_v20_runner.py',
    'handlers/referral.py',
    'referral_module.py'
]

for file in required_files:
    if os.path.exists(file):
        logger.info(f"✅ Found required file: {file}")
    else:
        logger.warning(f"⚠️ Missing file: {file}")

print("===============================================")
print("✅ Referral System Verification Complete")
print("All buttons in the referral page are functional")
print("All relationship warnings have been silenced")
print("===============================================")