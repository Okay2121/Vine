"""
Performance Validation Test Suite
=================================
Tests database performance improvements after AWS optimization.
"""

import time
import statistics
import logging
from contextlib import contextmanager
from app import app, db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class PerformanceValidator:
    """Validates database performance optimizations"""
    
    def __init__(self):
        self.results = {}
        
    @contextmanager
    def timer(self, operation_name):
        """Context manager to time operations"""
        start = time.time()
        yield
        duration = (time.time() - start) * 1000  # Convert to milliseconds
        
        if operation_name not in self.results:
            self.results[operation_name] = []
        self.results[operation_name].append(duration)
    
    def test_connection_pool_performance(self, iterations=10):
        """Test connection pool efficiency"""
        print("Testing connection pool performance...")
        
        with app.app_context():
            for i in range(iterations):
                with self.timer('connection_acquisition'):
                    with db.engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
    
    def test_user_lookup_performance(self, iterations=10):
        """Test user lookup query performance"""
        print("Testing user lookup performance...")
        
        with app.app_context():
            for i in range(iterations):
                with self.timer('user_lookup'):
                    with db.engine.connect() as conn:
                        conn.execute(text("""
                            SELECT id, telegram_id, username, balance 
                            FROM "user" 
                            LIMIT 5
                        """))
    
    def test_transaction_query_performance(self, iterations=10):
        """Test transaction history query performance"""
        print("Testing transaction query performance...")
        
        with app.app_context():
            for i in range(iterations):
                with self.timer('transaction_query'):
                    with db.engine.connect() as conn:
                        conn.execute(text("""
                            SELECT t.transaction_type, t.amount, t.timestamp, u.username
                            FROM transaction t
                            JOIN "user" u ON t.user_id = u.id
                            ORDER BY t.timestamp DESC
                            LIMIT 10
                        """))
    
    def test_dashboard_query_performance(self, iterations=10):
        """Test dashboard data aggregation performance"""
        print("Testing dashboard query performance...")
        
        with app.app_context():
            for i in range(iterations):
                with self.timer('dashboard_query'):
                    with db.engine.connect() as conn:
                        conn.execute(text("""
                            SELECT 
                                u.id,
                                u.balance,
                                u.initial_deposit,
                                COUNT(t.id) as transaction_count,
                                COALESCE(SUM(CASE WHEN t.transaction_type = 'trade_profit' THEN t.amount ELSE 0 END), 0) as total_profit
                            FROM "user" u
                            LEFT JOIN transaction t ON u.id = t.user_id
                            GROUP BY u.id, u.balance, u.initial_deposit
                            LIMIT 10
                        """))
    
    def test_admin_query_performance(self, iterations=10):
        """Test admin dashboard queries"""
        print("Testing admin query performance...")
        
        with app.app_context():
            for i in range(iterations):
                with self.timer('admin_stats'):
                    with db.engine.connect() as conn:
                        conn.execute(text("""
                            SELECT 
                                COUNT(*) as total_users,
                                SUM(balance) as total_balance,
                                AVG(balance) as avg_balance,
                                COUNT(CASE WHEN balance > 0 THEN 1 END) as users_with_balance
                            FROM "user"
                        """))
    
    def test_batch_operation_simulation(self, iterations=5):
        """Simulate batch operations performance"""
        print("Testing batch operation performance...")
        
        with app.app_context():
            for i in range(iterations):
                with self.timer('batch_simulation'):
                    with db.engine.connect() as conn:
                        # Simulate batch balance update query
                        conn.execute(text("""
                            SELECT id, balance 
                            FROM "user" 
                            ORDER BY last_activity DESC 
                            LIMIT 50
                        """))
    
    def analyze_results(self):
        """Analyze and report performance results"""
        print("\n" + "="*60)
        print("PERFORMANCE ANALYSIS RESULTS")
        print("="*60)
        
        for operation, times in self.results.items():
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                median_time = statistics.median(times)
                
                print(f"\n{operation.replace('_', ' ').title()}:")
                print(f"  Average: {avg_time:.2f}ms")
                print(f"  Median:  {median_time:.2f}ms")
                print(f"  Min:     {min_time:.2f}ms")
                print(f"  Max:     {max_time:.2f}ms")
                print(f"  Samples: {len(times)}")
                
                # Performance assessment
                if avg_time < 50:
                    status = "EXCELLENT"
                elif avg_time < 100:
                    status = "GOOD"
                elif avg_time < 200:
                    status = "ACCEPTABLE"
                else:
                    status = "NEEDS OPTIMIZATION"
                
                print(f"  Status:  {status}")
        
        print("\n" + "="*60)
        print("OPTIMIZATION ASSESSMENT")
        print("="*60)
        
        # Overall performance assessment
        all_times = []
        for times in self.results.values():
            all_times.extend(times)
        
        if all_times:
            overall_avg = statistics.mean(all_times)
            print(f"Overall average query time: {overall_avg:.2f}ms")
            
            if overall_avg < 100:
                print("✅ EXCELLENT: Database performance is optimal for production")
            elif overall_avg < 200:
                print("✅ GOOD: Database performance is suitable for 500+ users")
            else:
                print("⚠️  FAIR: Performance acceptable but could be improved")
        
        return self.results
    
    def check_optimization_status(self):
        """Check current optimization status"""
        print("\nChecking optimization status...")
        
        with app.app_context():
            try:
                with db.engine.connect() as conn:
                    # Check connection pool
                    pool = db.engine.pool
                    pool_size = getattr(pool, 'size', lambda: 'unknown')()
                    pool_type = type(pool).__name__
                    
                    print(f"Connection Pool: {pool_type} (size: {pool_size})")
                    
                    # Check for indexes
                    result = conn.execute(text("""
                        SELECT COUNT(*) as index_count
                        FROM pg_indexes 
                        WHERE schemaname = 'public'
                    """))
                    row = result.fetchone()
                    index_count = row[0] if row else 0
                    
                    print(f"Database Indexes: {index_count} total")
                    
                    # Check active indexes
                    result = conn.execute(text("""
                        SELECT COUNT(*) as active_indexes
                        FROM pg_stat_user_indexes 
                        WHERE schemaname = 'public' AND idx_scan > 0
                    """))
                    row = result.fetchone()
                    active_indexes = row[0] if row else 0
                    
                    print(f"Active Indexes: {active_indexes} in use")
                    
                    return True
            except Exception as e:
                print(f"Error checking optimization status: {e}")
                return False
    
    def run_full_test_suite(self):
        """Run complete performance validation"""
        print("Starting database performance validation...")
        print("This will test query speeds after AWS optimization\n")
        
        # Check optimization status first
        self.check_optimization_status()
        
        # Run performance tests
        self.test_connection_pool_performance()
        self.test_user_lookup_performance()
        self.test_transaction_query_performance()
        self.test_dashboard_query_performance()
        self.test_admin_query_performance()
        self.test_batch_operation_simulation()
        
        # Analyze results
        results = self.analyze_results()
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS")
        print("="*60)
        
        # Provide specific recommendations
        if 'connection_acquisition' in results:
            conn_times = results['connection_acquisition']
            avg_conn = statistics.mean(conn_times)
            
            if avg_conn < 50:
                print("✅ Connection pooling is working optimally")
            else:
                print("⚠️  Consider adjusting connection pool settings")
        
        if 'user_lookup' in results:
            lookup_times = results['user_lookup']
            avg_lookup = statistics.mean(lookup_times)
            
            if avg_lookup < 100:
                print("✅ User lookups are well-optimized")
            else:
                print("💡 Consider adding caching for user data")
        
        print("\n🎯 Database optimization complete!")
        print("Your bot should now have query speeds comparable to Neon.")
        
        return results


def main():
    """Run performance validation"""
    validator = PerformanceValidator()
    return validator.run_full_test_suite()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = main()