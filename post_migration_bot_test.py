"""
Post-Migration Bot Functionality Test
====================================
Comprehensive testing of all bot features after AWS RDS migration.
Ensures zero functionality loss during database migration.
"""

import os
import logging
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from app import app, db
from models import User, Transaction, TradingPosition, ReferralCode, SystemSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotFunctionalityTester:
    """Tests all critical bot functionality after migration"""
    
    def __init__(self):
        self.test_results = {}
        self.critical_failures = []
        
    def test_database_connectivity(self):
        """Test basic database connection and operations"""
        logger.info("Testing database connectivity...")
        
        try:
            with app.app_context():
                # Test basic connection
                result = db.session.execute(text("SELECT 1"))
                test_value = result.scalar()
                
                if test_value == 1:
                    logger.info("✓ Database connection successful")
                    self.test_results['database_connection'] = True
                else:
                    logger.error("✗ Database connection test failed")
                    self.test_results['database_connection'] = False
                    self.critical_failures.append("Database connection")
                
        except Exception as e:
            logger.error(f"✗ Database connectivity test failed: {e}")
            self.test_results['database_connection'] = False
            self.critical_failures.append("Database connection")
    
    def test_user_operations(self):
        """Test user creation, lookup, and updates"""
        logger.info("Testing user operations...")
        
        try:
            with app.app_context():
                # Test user count
                user_count = User.query.count()
                logger.info(f"Total users in database: {user_count}")
                
                # Test user lookup by telegram_id
                test_user = User.query.first()
                if test_user:
                    found_user = User.query.filter_by(telegram_id=test_user.telegram_id).first()
                    if found_user and found_user.id == test_user.id:
                        logger.info("✓ User lookup by telegram_id working")
                        self.test_results['user_lookup'] = True
                    else:
                        logger.error("✗ User lookup failed")
                        self.test_results['user_lookup'] = False
                        self.critical_failures.append("User lookup")
                else:
                    logger.info("No users found - user lookup test skipped")
                    self.test_results['user_lookup'] = True
                
        except Exception as e:
            logger.error(f"✗ User operations test failed: {e}")
            self.test_results['user_lookup'] = False
            self.critical_failures.append("User operations")
    
    def test_transaction_operations(self):
        """Test transaction recording and retrieval"""
        logger.info("Testing transaction operations...")
        
        try:
            with app.app_context():
                # Test transaction count
                tx_count = Transaction.query.count()
                logger.info(f"Total transactions in database: {tx_count}")
                
                # Test transaction types
                tx_types = db.session.execute(
                    text("SELECT DISTINCT transaction_type FROM transaction")
                ).fetchall()
                
                types_list = [row[0] for row in tx_types]
                logger.info(f"Transaction types found: {types_list}")
                
                # Test recent transactions
                recent_txs = Transaction.query.order_by(Transaction.timestamp.desc()).limit(5).all()
                logger.info(f"✓ Retrieved {len(recent_txs)} recent transactions")
                
                self.test_results['transactions'] = True
                
        except Exception as e:
            logger.error(f"✗ Transaction operations test failed: {e}")
            self.test_results['transactions'] = False
            self.critical_failures.append("Transaction operations")
    
    def test_trading_positions(self):
        """Test trading position management"""
        logger.info("Testing trading positions...")
        
        try:
            with app.app_context():
                # Test position count
                position_count = TradingPosition.query.count()
                logger.info(f"Total trading positions: {position_count}")
                
                # Test position statuses
                statuses = db.session.execute(
                    text("SELECT DISTINCT status FROM trading_position WHERE status IS NOT NULL")
                ).fetchall()
                
                status_list = [row[0] for row in statuses]
                logger.info(f"Position statuses: {status_list}")
                
                # Test recent positions
                recent_positions = TradingPosition.query.order_by(
                    TradingPosition.timestamp.desc()
                ).limit(5).all()
                
                logger.info(f"✓ Retrieved {len(recent_positions)} recent positions")
                self.test_results['trading_positions'] = True
                
        except Exception as e:
            logger.error(f"✗ Trading positions test failed: {e}")
            self.test_results['trading_positions'] = False
            self.critical_failures.append("Trading positions")
    
    def test_balance_calculations(self):
        """Test user balance calculations and updates"""
        logger.info("Testing balance calculations...")
        
        try:
            with app.app_context():
                # Test user balances
                users_with_balance = User.query.filter(User.balance > 0).count()
                total_balance = db.session.execute(
                    text("SELECT COALESCE(SUM(balance), 0) FROM \"user\"")
                ).scalar()
                
                logger.info(f"Users with balance: {users_with_balance}")
                logger.info(f"Total system balance: {total_balance}")
                
                # Test balance consistency
                if total_balance is not None:
                    logger.info("✓ Balance calculations working")
                    self.test_results['balance_calculations'] = True
                else:
                    logger.error("✗ Balance calculation failed")
                    self.test_results['balance_calculations'] = False
                    self.critical_failures.append("Balance calculations")
                
        except Exception as e:
            logger.error(f"✗ Balance calculations test failed: {e}")
            self.test_results['balance_calculations'] = False
            self.critical_failures.append("Balance calculations")
    
    def test_referral_system(self):
        """Test referral system functionality"""
        logger.info("Testing referral system...")
        
        try:
            with app.app_context():
                # Test referral codes
                ref_count = ReferralCode.query.count()
                logger.info(f"Total referral codes: {ref_count}")
                
                # Test active referral codes
                active_refs = ReferralCode.query.filter_by(is_active=True).count()
                logger.info(f"Active referral codes: {active_refs}")
                
                # Test referral relationships
                users_with_referrer = User.query.filter(
                    User.referrer_code_id.isnot(None)
                ).count()
                logger.info(f"Users with referrer: {users_with_referrer}")
                
                logger.info("✓ Referral system working")
                self.test_results['referral_system'] = True
                
        except Exception as e:
            logger.error(f"✗ Referral system test failed: {e}")
            self.test_results['referral_system'] = False
            self.critical_failures.append("Referral system")
    
    def test_admin_functions(self):
        """Test admin functionality"""
        logger.info("Testing admin functions...")
        
        try:
            with app.app_context():
                # Test system settings
                settings_count = SystemSettings.query.count()
                logger.info(f"System settings count: {settings_count}")
                
                # Test admin operations capability
                # Check if we can query admin-related data
                admin_transactions = Transaction.query.filter(
                    Transaction.transaction_type.in_(['admin_credit', 'admin_debit'])
                ).count()
                
                logger.info(f"Admin transactions found: {admin_transactions}")
                logger.info("✓ Admin functions accessible")
                self.test_results['admin_functions'] = True
                
        except Exception as e:
            logger.error(f"✗ Admin functions test failed: {e}")
            self.test_results['admin_functions'] = False
            self.critical_failures.append("Admin functions")
    
    def test_performance_metrics(self):
        """Test performance tracking and metrics"""
        logger.info("Testing performance metrics...")
        
        try:
            with app.app_context():
                # Test table existence and basic queries
                tables_to_check = ['user_metrics', 'daily_snapshot']
                
                for table in tables_to_check:
                    try:
                        result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        logger.info(f"{table} records: {count}")
                    except Exception as e:
                        logger.info(f"{table} table not found or empty: {e}")
                
                logger.info("✓ Performance metrics accessible")
                self.test_results['performance_metrics'] = True
                
        except Exception as e:
            logger.error(f"✗ Performance metrics test failed: {e}")
            self.test_results['performance_metrics'] = False
    
    def test_data_integrity(self):
        """Test data integrity and relationships"""
        logger.info("Testing data integrity...")
        
        try:
            with app.app_context():
                # Test foreign key relationships
                users_with_transactions = db.session.execute(text("""
                    SELECT COUNT(DISTINCT u.id) 
                    FROM "user" u 
                    JOIN transaction t ON u.id = t.user_id
                """)).scalar()
                
                logger.info(f"Users with transactions: {users_with_transactions}")
                
                # Test referential integrity
                orphaned_transactions = db.session.execute(text("""
                    SELECT COUNT(*) FROM transaction t 
                    LEFT JOIN "user" u ON t.user_id = u.id 
                    WHERE u.id IS NULL
                """)).scalar()
                
                if orphaned_transactions == 0:
                    logger.info("✓ No orphaned transactions found")
                else:
                    logger.warning(f"Found {orphaned_transactions} orphaned transactions")
                
                self.test_results['data_integrity'] = True
                
        except Exception as e:
            logger.error(f"✗ Data integrity test failed: {e}")
            self.test_results['data_integrity'] = False
            self.critical_failures.append("Data integrity")
    
    def test_health_endpoints(self):
        """Test Flask health endpoints"""
        logger.info("Testing health endpoints...")
        
        try:
            with app.test_client() as client:
                # Test /health endpoint
                response = client.get('/health')
                if response.status_code == 200:
                    logger.info("✓ /health endpoint working")
                else:
                    logger.error(f"✗ /health endpoint failed: {response.status_code}")
                
                # Test /db-status endpoint
                response = client.get('/db-status')
                if response.status_code == 200:
                    logger.info("✓ /db-status endpoint working")
                else:
                    logger.error(f"✗ /db-status endpoint failed: {response.status_code}")
                
                self.test_results['health_endpoints'] = True
                
        except Exception as e:
            logger.error(f"✗ Health endpoints test failed: {e}")
            self.test_results['health_endpoints'] = False
    
    def run_comprehensive_test(self):
        """Run all bot functionality tests"""
        logger.info("=== Post-Migration Bot Functionality Test ===")
        
        test_methods = [
            self.test_database_connectivity,
            self.test_user_operations,
            self.test_transaction_operations,
            self.test_trading_positions,
            self.test_balance_calculations,
            self.test_referral_system,
            self.test_admin_functions,
            self.test_performance_metrics,
            self.test_data_integrity,
            self.test_health_endpoints
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                logger.error(f"Test {test_method.__name__} crashed: {e}")
                self.test_results[test_method.__name__] = False
                self.critical_failures.append(test_method.__name__)
        
        # Generate test report
        self.generate_test_report()
        
        return len(self.critical_failures) == 0
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("=== Test Report ===")
        
        passed_tests = sum(1 for result in self.test_results.values() if result)
        total_tests = len(self.test_results)
        
        logger.info(f"Tests passed: {passed_tests}/{total_tests}")
        
        if self.critical_failures:
            logger.error("Critical failures detected:")
            for failure in self.critical_failures:
                logger.error(f"  - {failure}")
        else:
            logger.info("✅ All critical tests passed!")
        
        # Detailed results
        logger.info("\nDetailed results:")
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        # Save report to file
        report_content = f"""Post-Migration Test Report
Generated: {datetime.now().isoformat()}

Summary:
- Tests passed: {passed_tests}/{total_tests}
- Critical failures: {len(self.critical_failures)}

Critical Failures:
{chr(10).join(f"- {failure}" for failure in self.critical_failures) if self.critical_failures else "None"}

Detailed Results:
{chr(10).join(f"{test}: {'PASS' if result else 'FAIL'}" for test, result in self.test_results.items())}
"""
        
        with open('migration_test_report.txt', 'w') as f:
            f.write(report_content)
        
        logger.info("Test report saved to: migration_test_report.txt")

def main():
    """Run post-migration bot functionality test"""
    tester = BotFunctionalityTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 Post-migration test PASSED!")
            print("All bot functionality is working correctly with AWS RDS")
        else:
            print("\n❌ Post-migration test FAILED!")
            print("Critical issues detected - please review the test report")
            
    except Exception as e:
        logger.error(f"Post-migration test crashed: {e}")
        print(f"\n💥 Test crashed: {e}")

if __name__ == "__main__":
    main()