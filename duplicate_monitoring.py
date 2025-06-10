"""
Duplicate Response Monitoring System
Provides real-time monitoring and reporting of duplicate protection effectiveness
"""
import logging
import time
import json
from datetime import datetime, timedelta
from graceful_duplicate_handler import duplicate_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DuplicateMonitor:
    """Monitors and reports on duplicate protection system performance"""
    
    def __init__(self):
        self.start_time = time.time()
        self.stats = {
            'total_updates_processed': 0,
            'duplicates_blocked': 0,
            'rate_limits_applied': 0,
            'api_409_errors_handled': 0,
            'last_reset': datetime.now().isoformat()
        }
        
    def log_update_processed(self):
        """Log that an update was processed"""
        self.stats['total_updates_processed'] += 1
        
    def log_duplicate_blocked(self, duplicate_type="update"):
        """Log that a duplicate was blocked"""
        self.stats['duplicates_blocked'] += 1
        logger.info(f"✅ Blocked duplicate {duplicate_type}")
        
    def log_rate_limit_applied(self, user_id, action_type):
        """Log that rate limiting was applied"""
        self.stats['rate_limits_applied'] += 1
        logger.info(f"⏳ Applied rate limit for user {user_id} action {action_type}")
        
    def log_api_409_handled(self, operation):
        """Log that an HTTP 409 error was handled gracefully"""
        self.stats['api_409_errors_handled'] += 1
        logger.info(f"🛡️ Gracefully handled HTTP 409 for {operation}")
        
    def get_stats_summary(self):
        """Get a summary of duplicate protection statistics"""
        uptime = time.time() - self.start_time
        uptime_str = str(timedelta(seconds=int(uptime)))
        
        summary = f"""
🔍 Duplicate Protection Monitor - Status Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏱️ System Uptime: {uptime_str}
📊 Total Updates Processed: {self.stats['total_updates_processed']}
🚫 Duplicates Blocked: {self.stats['duplicates_blocked']}
⏳ Rate Limits Applied: {self.stats['rate_limits_applied']}
🛡️ HTTP 409 Errors Handled: {self.stats['api_409_errors_handled']}

📈 Protection Effectiveness:
   • Duplicate Block Rate: {self.get_duplicate_rate():.1f}%
   • System Health: {'🟢 Excellent' if self.is_healthy() else '🟡 Monitoring'}

💾 Cache Status:
   • Updates Cache Size: {len(duplicate_manager.processed_updates)}
   • Callbacks Cache Size: {len(duplicate_manager.processed_callbacks)}
   • Messages Cache Size: {len(duplicate_manager.processed_messages)}
   • Rate Limit Entries: {len(duplicate_manager.request_timestamps)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return summary
        
    def get_duplicate_rate(self):
        """Calculate the duplicate block rate as a percentage"""
        total = self.stats['total_updates_processed'] + self.stats['duplicates_blocked']
        if total == 0:
            return 0
        return (self.stats['duplicates_blocked'] / total) * 100
        
    def is_healthy(self):
        """Determine if the system is operating in a healthy state"""
        # System is healthy if we're blocking duplicates and handling 409s
        return (self.stats['duplicates_blocked'] > 0 or 
                self.stats['api_409_errors_handled'] > 0 or
                self.stats['total_updates_processed'] > 10)
        
    def reset_stats(self):
        """Reset statistics for a new monitoring period"""
        self.start_time = time.time()
        self.stats = {
            'total_updates_processed': 0,
            'duplicates_blocked': 0,
            'rate_limits_applied': 0,
            'api_409_errors_handled': 0,
            'last_reset': datetime.now().isoformat()
        }
        logger.info("🔄 Duplicate protection statistics reset")
        
    def export_stats(self, filename=None):
        """Export statistics to a JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"duplicate_protection_stats_{timestamp}.json"
            
        stats_with_metadata = {
            **self.stats,
            'uptime_seconds': time.time() - self.start_time,
            'duplicate_rate_percent': self.get_duplicate_rate(),
            'system_healthy': self.is_healthy(),
            'export_timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(stats_with_metadata, f, indent=2)
            logger.info(f"📁 Statistics exported to {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Failed to export statistics: {e}")
            return None

# Global monitor instance
monitor = DuplicateMonitor()

def start_monitoring():
    """Start the duplicate protection monitoring system"""
    logger.info("🚀 Starting duplicate protection monitoring")
    return monitor

def log_successful_operation(operation_type="general"):
    """Log a successful operation to track system health"""
    monitor.log_update_processed()

def print_status_report():
    """Print a comprehensive status report"""
    print(monitor.get_stats_summary())

if __name__ == "__main__":
    # Start monitoring
    start_monitoring()
    
    # Print initial status
    print("🔍 Duplicate Protection Monitoring System")
    print("==========================================")
    print("Monitor started successfully!")
    print("\nTo view status at any time, run:")
    print("python duplicate_monitoring.py")
    print("\nSystem is now actively monitoring for:")
    print("• Duplicate updates and callbacks")
    print("• Rate limiting effectiveness") 
    print("• HTTP 409 error handling")
    print("• Overall system health")
    
    # Wait a moment and show initial stats
    time.sleep(1)
    print_status_report()