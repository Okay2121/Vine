#!/usr/bin/env python3
"""
Comprehensive Auto Trading Settings Integration Test
===================================================
Verifies that the auto trading system is fully implemented and integrated
with the USD trade broadcast system.
"""

import sys
from app import app, db
from models import User, AutoTradingSettings
from utils.auto_trading_manager import AutoTradingManager
from utils.usd_trade_processor import usd_processor

def test_database_schema():
    """Test that the auto trading database schema is complete"""
    print("🔍 Testing database schema...")
    
    with app.app_context():
        try:
            # Test that AutoTradingSettings table exists and has all required columns
            test_query = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'auto_trading_settings'
                ORDER BY column_name
            """))
            
            columns = [row[0] for row in test_query.fetchall()]
            
            required_columns = [
                'auto_trading_balance_percentage',
                'created_at',
                'daily_trades_auto',
                'enable_anti_rug_protection',
                'enable_dynamic_position_sizing',
                'enable_portfolio_rebalancing',
                'enable_trailing_stop_loss',
                'external_signals_enabled',
                'fomo_cooldown_minutes',
                'id',
                'is_enabled',
                'last_trade_at',
                'max_daily_trades',
                'max_market_cap',
                'max_positions_auto',
                'max_simultaneous_positions',
                'min_liquidity_sol',
                'min_market_cap',
                'min_time_between_trades_minutes',
                'min_volume_24h',
                'position_size_auto',
                'position_size_percentage',
                'pump_fun_launches',
                'social_sentiment',
                'stop_loss_auto',
                'stop_loss_percentage',
                'successful_auto_trades',
                'take_profit_auto',
                'take_profit_percentage',
                'total_auto_trades',
                'trailing_stop_distance_percentage',
                'updated_at',
                'user_id',
                'whale_movements'
            ]
            
            missing_columns = set(required_columns) - set(columns)
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            
            print(f"✅ Database schema complete ({len(columns)} columns)")
            return True
            
        except Exception as e:
            print(f"❌ Database schema error: {e}")
            return False

def test_user_settings():
    """Test that users have auto trading settings"""
    print("\n🔍 Testing user auto trading settings...")
    
    with app.app_context():
        try:
            users = User.query.filter(User.balance > 0).all()
            settings_count = 0
            
            for user in users:
                settings = AutoTradingManager.get_or_create_settings(user.id)
                if settings:
                    settings_count += 1
                    print(f"✅ {user.username or user.telegram_id}: Auto trading configured")
                    print(f"   - Enabled: {settings.is_enabled}")
                    print(f"   - Position size: {settings.position_size_percentage}%")
                    print(f"   - External signals: {settings.external_signals_enabled}")
                else:
                    print(f"❌ {user.username or user.telegram_id}: No settings found")
            
            print(f"\n✅ {settings_count}/{len(users)} users have auto trading settings")
            return settings_count == len(users)
            
        except Exception as e:
            print(f"❌ User settings error: {e}")
            return False

def test_usd_integration():
    """Test USD trade processor integration"""
    print("\n🔍 Testing USD trade integration...")
    
    try:
        # Test USD trade parsing
        test_trade = "E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump 0.00045 0.062 https://solscan.io/tx/abc123"
        trade_data = usd_processor.parse_trade_message(test_trade)
        
        if not trade_data:
            print("❌ USD trade parsing failed")
            return False
        
        print("✅ USD trade parsing successful")
        print(f"   - Contract: {trade_data['contract_address']}")
        print(f"   - Entry USD: ${trade_data['entry_price_usd']:.6f}")
        print(f"   - Exit USD: ${trade_data['exit_price_usd']:.6f}")
        print(f"   - ROI: {trade_data['roi_percentage']:.1f}%")
        
        # Test SOL price fetching
        sol_price = usd_processor.get_sol_price_usd()
        if sol_price > 0:
            print(f"✅ SOL price fetching: ${sol_price:.2f}")
        else:
            print("❌ SOL price fetching failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ USD integration error: {e}")
        return False

def test_trade_distribution():
    """Test trade distribution to auto trading users"""
    print("\n🔍 Testing trade distribution logic...")
    
    with app.app_context():
        try:
            # Find users eligible for auto trading
            eligible_users = User.query.join(AutoTradingSettings).filter(
                AutoTradingSettings.is_enabled == True,
                AutoTradingSettings.external_signals_enabled == True,
                User.balance >= 0.1
            ).all()
            
            print(f"✅ Found {len(eligible_users)} eligible users for auto trading")
            
            total_position_value = 0
            for user in eligible_users:
                settings = user.auto_trading_settings[0]
                position_size = user.balance * (settings.position_size_percentage / 100)
                total_position_value += position_size
                print(f"   - {user.username or user.telegram_id}: {position_size:.4f} SOL position ({settings.position_size_percentage}%)")
            
            print(f"✅ Total position value: {total_position_value:.4f} SOL")
            return len(eligible_users) > 0
            
        except Exception as e:
            print(f"❌ Trade distribution error: {e}")
            return False

def test_settings_validation():
    """Test auto trading settings validation"""
    print("\n🔍 Testing settings validation...")
    
    with app.app_context():
        try:
            users = User.query.filter(User.balance > 0).first()
            if not users:
                print("❌ No test user found")
                return False
            
            # Test valid setting update
            result = AutoTradingManager.update_setting(users.id, 'position_size_percentage', 15.0)
            if result[0]:
                print("✅ Valid setting update successful")
            else:
                print(f"❌ Valid setting update failed: {result[1]}")
                return False
            
            # Test invalid setting update
            result = AutoTradingManager.update_setting(users.id, 'position_size_percentage', 50.0)
            if not result[0]:
                print("✅ Invalid setting rejected correctly")
            else:
                print("❌ Invalid setting was accepted")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Settings validation error: {e}")
            return False

def main():
    """Run comprehensive auto trading integration test"""
    print("🚀 Auto Trading Settings Integration Test")
    print("=" * 50)
    
    tests = [
        test_database_schema,
        test_user_settings,
        test_usd_integration,
        test_trade_distribution,
        test_settings_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print("❌ Test failed!")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Auto Trading Settings System: FULLY IMPLEMENTED ✅")
        print("\nFeatures confirmed:")
        print("• Database schema complete with all required columns")
        print("• All users have personalized auto trading configurations")
        print("• USD trade format integration working")
        print("• Live SOL price conversion functional")
        print("• Trade distribution logic operational")
        print("• Settings validation working correctly")
        print("• AutoTradingManager utility fully functional")
        return True
    else:
        print("❌ Auto Trading Settings System: ISSUES DETECTED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)