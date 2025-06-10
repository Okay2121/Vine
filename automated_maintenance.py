"""
Automated Database Maintenance Scheduler
========================================
Runs proactive monitoring and cleanup to prevent database quota exhaustion
"""
import threading
import time
import schedule
import logging
from datetime import datetime
from database_monitoring import DatabaseMonitor, run_daily_maintenance

logger = logging.getLogger(__name__)

class MaintenanceScheduler:
    """Schedules and runs automated database maintenance tasks"""
    
    def __init__(self):
        self.monitor = DatabaseMonitor()
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the maintenance scheduler in a background thread"""
        if self.running:
            logger.warning("Maintenance scheduler already running")
            return
        
        self.running = True
        
        # Schedule daily maintenance at 3 AM
        schedule.every().day.at("03:00").do(self.run_full_maintenance)
        
        # Schedule health checks every 6 hours
        schedule.every(6).hours.do(self.run_health_check)
        
        # Schedule quick cleanup every 2 hours
        schedule.every(2).hours.do(self.run_quick_cleanup)
        
        # Start scheduler thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("Database maintenance scheduler started")
    
    def stop(self):
        """Stop the maintenance scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Database maintenance scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def run_health_check(self):
        """Run health check and log alerts"""
        try:
            logger.info("Running database health check")
            health = self.monitor.check_database_health()
            alerts = self.monitor.get_usage_alerts()
            
            if alerts:
                for alert in alerts:
                    logger.warning(f"ALERT: {alert}")
            else:
                logger.info("Database health check passed - no alerts")
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def run_quick_cleanup(self):
        """Run quick cleanup of recent data"""
        try:
            logger.info("Running quick database cleanup")
            # Clean data older than 60 days (more conservative)
            cleanup = self.monitor.cleanup_old_data(days_to_keep=60)
            if cleanup:
                total_deleted = sum([
                    cleanup.get('deleted_transactions', 0),
                    cleanup.get('deleted_profits', 0),
                    cleanup.get('deleted_positions', 0)
                ])
                logger.info(f"Quick cleanup removed {total_deleted} old records")
            
        except Exception as e:
            logger.error(f"Quick cleanup failed: {e}")
    
    def run_full_maintenance(self):
        """Run full daily maintenance"""
        try:
            logger.info("Running full database maintenance")
            result = run_daily_maintenance()
            
            if result['alerts']:
                logger.warning(f"Daily maintenance found {len(result['alerts'])} alerts")
                for alert in result['alerts']:
                    logger.warning(f"MAINTENANCE ALERT: {alert}")
            else:
                logger.info("Full maintenance completed successfully")
                
        except Exception as e:
            logger.error(f"Full maintenance failed: {e}")

# Global scheduler instance
maintenance_scheduler = MaintenanceScheduler()

def start_maintenance_scheduler():
    """Start the automated maintenance scheduler"""
    maintenance_scheduler.start()

def stop_maintenance_scheduler():
    """Stop the automated maintenance scheduler"""
    maintenance_scheduler.stop()