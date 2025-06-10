"""
Create Performance Tracking Tables
Creates the missing database tables needed for real-time performance data
"""
from app import app, db
from performance_tracking import DailySnapshot, UserMetrics, TradeLog

def create_performance_tables():
    """Create all performance tracking tables"""
    with app.app_context():
        try:
            # Create all tables defined in performance_tracking module
            db.create_all()
            
            print("Performance tracking tables created successfully:")
            print("- DailySnapshot")
            print("- UserMetrics") 
            print("- TradeLog")
            
            return True
            
        except Exception as e:
            print(f"Error creating tables: {e}")
            return False

if __name__ == "__main__":
    success = create_performance_tables()
    if success:
        print("\nDatabase is ready for real-time performance tracking")
    else:
        print("\nFailed to create performance tables")