#!/usr/bin/env python3
"""
Database Maintenance Runner
===========================
Standalone script to run database maintenance tasks manually or via cron
"""
import sys
import os
import logging
from datetime import datetime

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_monitoring import run_daily_maintenance, DatabaseMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maintenance.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run maintenance with detailed reporting"""
    logger.info("=" * 60)
    logger.info("Database Maintenance Script Started")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)
    
    try:
        # Run comprehensive maintenance
        result = run_daily_maintenance()
        
        # Log detailed results
        if result['health']:
            health = result['health']
            logger.info(f"Database Size: {health['database_size']}")
            logger.info(f"Active Connections: {health['active_connections']}")
            logger.info(f"Total Connections: {health['total_connections']}")
        
        if result['cleanup']:
            cleanup = result['cleanup']
            total_deleted = sum([
                cleanup.get('deleted_transactions', 0),
                cleanup.get('deleted_profits', 0),
                cleanup.get('deleted_positions', 0)
            ])
            logger.info(f"Cleanup: {total_deleted} old records removed")
        
        if result['vacuum_success']:
            logger.info("Database VACUUM completed successfully")
        else:
            logger.warning("Database VACUUM failed")
        
        # Report alerts
        alerts = result.get('alerts', [])
        if alerts:
            logger.warning(f"Found {len(alerts)} alerts:")
            for alert in alerts:
                logger.warning(f"  ALERT: {alert}")
        else:
            logger.info("No alerts detected - database health is optimal")
        
        logger.info("=" * 60)
        logger.info("Database Maintenance Completed Successfully")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Maintenance failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    sys.exit(main())