"""
AWS RDS Migration Testing Framework
==================================
Comprehensive testing to ensure bot functionality remains intact during migration.
Tests all critical bot features with both Neon and AWS RDS databases.
"""

import os
import logging
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationTester:
    """Tests all critical bot functionality during migration"""
    
    def __init__(self):
        self.neon_url = os.environ.get('DATABASE_URL') or \
                       "postgresql://neondb_owner:npg_9Hdj1LfbemJW@ep-cold-hall-a2171yga-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        self.aws_url = "postgresql://postgres:Checker97$@database-1.cxg48muy49z2.eu-north-1.rds.amazonaws.com:5432/Vibe"
        
        # Define critical tables for the bot
        self.critical_tables = [
            'user',
            'transaction', 
            'trading_position',
            'referral_code',
            'system_settings',
            'support_ticket',
            'trading_cycle',
            'user_metrics',
            'daily_snapshot'
        ]
        
        # Define critical bot functions to test
        self.test_functions = [
            self.test_user_operations,
            self.test_transaction_operations,
            self.test_trading_positions,
            self.test_referral_system,
            self.test_balance_operations,
            self.test_admin_operations,
            self.test_performance_tracking
        ]
    
    def test_database_connection(self, db_url, db_name):
        """Test basic database connectivity"""
        logger.info(f"Testing {db_name} database connection...")
        
        try:
            engine = create_engine(db_url, connect_args={'connect_timeout': 10})
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                row = result.fetchone()
                if row:
                    version = str(row[0])[:50] + "..."
                    logger.info(f"✓ {db_name} connected: {version}")
                    return True
                else:
                    logger.error(f"✗ {db_name} connection returned no version")
                    return False
        except Exception as e:
            logger.error(f"✗ {db_name} connection failed: {e}")
            return False
    
    def test_table_existence(self, db_url, db_name):
        """Test that all critical tables exist"""
        logger.info(f"Testing table existence in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                missing_tables = []
                
                for table in self.critical_tables:
                    result = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table}'
                        )
                    """))
                    row = result.fetchone()
                    exists = row[0] if row else False
                    
                    if exists:
                        logger.info(f"✓ Table '{table}' exists in {db_name}")
                    else:
                        logger.error(f"✗ Table '{table}' missing in {db_name}")
                        missing_tables.append(table)
                
                if missing_tables:
                    logger.error(f"Missing tables in {db_name}: {missing_tables}")
                    return False
                else:
                    logger.info(f"✓ All critical tables exist in {db_name}")
                    return True
                    
        except Exception as e:
            logger.error(f"Table existence test failed for {db_name}: {e}")
            return False
    
    def test_user_operations(self, db_url, db_name):
        """Test user-related database operations"""
        logger.info(f"Testing user operations in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Test user count
                result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
                row = result.fetchone()
                user_count = row[0] if row else 0
                logger.info(f"✓ User count in {db_name}: {user_count}")
                
                # Test user table structure
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'user' AND table_schema = 'public'
                """))
                columns = [row[0] for row in result.fetchall()]
                
                required_columns = ['telegram_id', 'balance', 'status', 'joined_at']
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    logger.error(f"✗ Missing user columns in {db_name}: {missing_columns}")
                    return False
                else:
                    logger.info(f"✓ User table structure valid in {db_name}")
                    return True
                    
        except Exception as e:
            logger.error(f"User operations test failed for {db_name}: {e}")
            return False
    
    def test_transaction_operations(self, db_url, db_name):
        """Test transaction-related operations"""
        logger.info(f"Testing transaction operations in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Test transaction count
                result = conn.execute(text("SELECT COUNT(*) FROM transaction"))
                row = result.fetchone()
                tx_count = row[0] if row else 0
                logger.info(f"✓ Transaction count in {db_name}: {tx_count}")
                
                # Test transaction types
                result = conn.execute(text("""
                    SELECT DISTINCT transaction_type FROM transaction 
                    ORDER BY transaction_type
                """))
                tx_types = [row[0] for row in result.fetchall()]
                logger.info(f"✓ Transaction types in {db_name}: {tx_types}")
                
                return True
                
        except Exception as e:
            logger.error(f"Transaction operations test failed for {db_name}: {e}")
            return False
    
    def test_trading_positions(self, db_url, db_name):
        """Test trading position operations"""
        logger.info(f"Testing trading positions in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Test trading position count
                result = conn.execute(text("SELECT COUNT(*) FROM trading_position"))
                row = result.fetchone()
                position_count = row[0] if row else 0
                logger.info(f"✓ Trading position count in {db_name}: {position_count}")
                
                # Test position statuses
                result = conn.execute(text("""
                    SELECT DISTINCT status FROM trading_position 
                    WHERE status IS NOT NULL
                """))
                statuses = [row[0] for row in result.fetchall()]
                logger.info(f"✓ Position statuses in {db_name}: {statuses}")
                
                return True
                
        except Exception as e:
            logger.error(f"Trading positions test failed for {db_name}: {e}")
            return False
    
    def test_referral_system(self, db_url, db_name):
        """Test referral system operations"""
        logger.info(f"Testing referral system in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Test referral codes
                result = conn.execute(text("SELECT COUNT(*) FROM referral_code"))
                row = result.fetchone()
                ref_count = row[0] if row else 0
                logger.info(f"✓ Referral code count in {db_name}: {ref_count}")
                
                return True
                
        except Exception as e:
            logger.error(f"Referral system test failed for {db_name}: {e}")
            return False
    
    def test_balance_operations(self, db_url, db_name):
        """Test balance-related operations"""
        logger.info(f"Testing balance operations in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Test user balances
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as user_count,
                        COALESCE(SUM(balance), 0) as total_balance,
                        COALESCE(AVG(balance), 0) as avg_balance
                    FROM \"user\" 
                    WHERE balance > 0
                """))
                row = result.fetchone()
                if row:
                    user_count, total_balance, avg_balance = row[0], row[1], row[2]
                    logger.info(f"✓ Users with balance in {db_name}: {user_count}")
                    logger.info(f"✓ Total balance in {db_name}: {total_balance}")
                    logger.info(f"✓ Average balance in {db_name}: {avg_balance}")
                
                return True
                
        except Exception as e:
            logger.error(f"Balance operations test failed for {db_name}: {e}")
            return False
    
    def test_admin_operations(self, db_url, db_name):
        """Test admin-related operations"""
        logger.info(f"Testing admin operations in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Test system settings
                result = conn.execute(text("SELECT COUNT(*) FROM system_settings"))
                row = result.fetchone()
                settings_count = row[0] if row else 0
                logger.info(f"✓ System settings count in {db_name}: {settings_count}")
                
                # Test support tickets if table exists
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM support_ticket"))
                    row = result.fetchone()
                    ticket_count = row[0] if row else 0
                    logger.info(f"✓ Support ticket count in {db_name}: {ticket_count}")
                except:
                    logger.info(f"Support ticket table not found in {db_name} (optional)")
                
                return True
                
        except Exception as e:
            logger.error(f"Admin operations test failed for {db_name}: {e}")
            return False
    
    def test_performance_tracking(self, db_url, db_name):
        """Test performance tracking operations"""
        logger.info(f"Testing performance tracking in {db_name}...")
        
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Test user metrics if table exists
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM user_metrics"))
                    row = result.fetchone()
                    metrics_count = row[0] if row else 0
                    logger.info(f"✓ User metrics count in {db_name}: {metrics_count}")
                except:
                    logger.info(f"User metrics table not found in {db_name} (optional)")
                
                # Test daily snapshots if table exists
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM daily_snapshot"))
                    row = result.fetchone()
                    snapshot_count = row[0] if row else 0
                    logger.info(f"✓ Daily snapshot count in {db_name}: {snapshot_count}")
                except:
                    logger.info(f"Daily snapshot table not found in {db_name} (optional)")
                
                return True
                
        except Exception as e:
            logger.error(f"Performance tracking test failed for {db_name}: {e}")
            return False
    
    def run_comprehensive_test(self, db_url, db_name):
        """Run all tests for a database"""
        logger.info(f"=== Running comprehensive test for {db_name} ===")
        
        # Test basic connection
        if not self.test_database_connection(db_url, db_name):
            return False
        
        # Test table existence
        if not self.test_table_existence(db_url, db_name):
            return False
        
        # Run all functional tests
        passed_tests = 0
        total_tests = len(self.test_functions)
        
        for test_func in self.test_functions:
            try:
                if test_func(db_url, db_name):
                    passed_tests += 1
                else:
                    logger.warning(f"Test {test_func.__name__} failed for {db_name}")
            except Exception as e:
                logger.error(f"Test {test_func.__name__} crashed for {db_name}: {e}")
        
        success_rate = (passed_tests / total_tests) * 100
        logger.info(f"{db_name} test results: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
        
        return success_rate >= 80  # Consider 80% pass rate as successful
    
    def compare_databases(self):
        """Compare data between Neon and AWS RDS"""
        logger.info("=== Comparing databases ===")
        
        try:
            neon_engine = create_engine(self.neon_url)
            aws_engine = create_engine(self.aws_url)
            
            comparison_results = {}
            
            with neon_engine.connect() as neon_conn, aws_engine.connect() as aws_conn:
                for table in self.critical_tables:
                    try:
                        # Get row counts
                        neon_result = neon_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        neon_row = neon_result.fetchone()
                        neon_count = neon_row[0] if neon_row else 0
                        
                        aws_result = aws_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        aws_row = aws_result.fetchone()
                        aws_count = aws_row[0] if aws_row else 0
                        
                        match = neon_count == aws_count
                        comparison_results[table] = {
                            'neon_count': neon_count,
                            'aws_count': aws_count,
                            'match': match
                        }
                        
                        status = "✓" if match else "✗"
                        logger.info(f"{status} {table}: Neon {neon_count}, AWS {aws_count}")
                        
                    except Exception as e:
                        logger.error(f"Comparison failed for {table}: {e}")
                        comparison_results[table] = {'error': str(e)}
            
            return comparison_results
            
        except Exception as e:
            logger.error(f"Database comparison failed: {e}")
            return None
    
    def run_migration_readiness_test(self):
        """Run complete migration readiness test"""
        logger.info("=== AWS RDS Migration Readiness Test ===")
        
        # Test Neon DB (source)
        neon_ready = self.run_comprehensive_test(self.neon_url, "Neon DB")
        
        # Test AWS RDS (target) 
        aws_ready = self.run_comprehensive_test(self.aws_url, "AWS RDS")
        
        # Compare databases if both are accessible
        if neon_ready and aws_ready:
            comparison = self.compare_databases()
            if comparison:
                matches = sum(1 for result in comparison.values() 
                            if isinstance(result, dict) and result.get('match', False))
                total = len([r for r in comparison.values() if 'error' not in r])
                match_rate = (matches / total * 100) if total > 0 else 0
                logger.info(f"Data comparison: {matches}/{total} tables match ({match_rate:.1f}%)")
        
        # Overall readiness assessment
        if neon_ready and aws_ready:
            logger.info("✅ Migration readiness: READY")
            logger.info("Both databases are functional and ready for migration")
            return True
        elif aws_ready:
            logger.info("⚠️ Migration readiness: AWS RDS READY, Neon DB issues detected")
            return True  # Can still migrate if target is ready
        else:
            logger.info("❌ Migration readiness: NOT READY")
            logger.info("Critical issues detected - migration not recommended")
            return False

def main():
    """Run migration readiness test"""
    tester = MigrationTester()
    
    try:
        ready = tester.run_migration_readiness_test()
        
        if ready:
            print("\n🎉 Migration readiness test PASSED!")
            print("Your bot is ready for AWS RDS migration")
        else:
            print("\n❌ Migration readiness test FAILED!")
            print("Please resolve issues before migration")
            
    except Exception as e:
        logger.error(f"Migration test failed: {e}")
        print(f"\n💥 Test crashed: {e}")

if __name__ == "__main__":
    main()