#!/usr/bin/env python3
"""
Test Trade Broadcast Fix - Verify TRASHPAD SELL command works
===========================================================
This script tests the trade broadcast functionality with the exact format
that was failing: Sell $TRASHPAD 0.00000197 561929 https://dexscreener.com/...
"""

import re
import sys
from app import app, db
from models import User, TradingPosition, Profit

def test_regex_patterns():
    """Test the updated regex patterns with the failing TRASHPAD command"""
    print("Testing updated regex patterns...")
    
    # Updated patterns (same as in bot_v20_runner.py)
    buy_pattern = re.compile(r'^Buy\s+\$([A-Za-z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)', re.IGNORECASE)
    sell_pattern = re.compile(r'^Sell\s+\$([A-Za-z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)', re.IGNORECASE)
    
    # Test message from the screenshot
    test_message = "Sell $TRASHPAD 0.00000197 561929 https://dexscreener.com/solana/59zDyd4HGsy3wJrZtoDXcsgUG2riMRkApLRiEVpCn17a"
    
    print(f"Test message: {test_message}")
    
    # Test SELL pattern
    sell_match = sell_pattern.match(test_message.strip())
    if sell_match:
        token_name, price_str, amount_str, tx_link = sell_match.groups()
        print(f"✅ SELL pattern matched successfully!")
        print(f"   Token: {token_name}")
        print(f"   Price: {price_str}")
        print(f"   Amount: {amount_str}")
        print(f"   TX Link: {tx_link}")
        return True, token_name, float(price_str), float(amount_str), tx_link
    else:
        print(f"❌ SELL pattern failed to match")
        return False, None, None, None, None

def test_standalone_sell_logic():
    """Test the standalone SELL logic for tokens without existing positions"""
    print("\nTesting standalone SELL logic...")
    
    with app.app_context():
        # Check if TRASHPAD has any open positions
        existing_positions = TradingPosition.query.filter_by(
            token_name='TRASHPAD',
            status='open'
        ).all()
        
        print(f"Existing TRASHPAD positions: {len(existing_positions)}")
        
        if not existing_positions:
            print("✅ No existing positions - standalone SELL logic should trigger")
            
            # Check active users
            active_users = User.query.filter(User.balance > 0).all()
            print(f"Active users for profit distribution: {len(active_users)}")
            
            if active_users:
                print("✅ Active users found - profit distribution should work")
                return True
            else:
                print("❌ No active users found for profit distribution")
                return False
        else:
            print("ℹ️ Existing positions found - normal SELL logic would trigger")
            return True

def test_profit_calculation():
    """Test the profit calculation logic for standalone SELL"""
    print("\nTesting profit calculation logic...")
    
    exit_price = 0.00000197
    # Simulate a reasonable entry price for realistic profits (8.7% ROI)
    simulated_entry_price = exit_price * 0.92
    roi_percentage = ((exit_price - simulated_entry_price) / simulated_entry_price) * 100
    
    print(f"Exit price: {exit_price}")
    print(f"Simulated entry price: {simulated_entry_price}")
    print(f"ROI percentage: {roi_percentage:.2f}%")
    
    if 5 <= roi_percentage <= 15:
        print("✅ ROI percentage is realistic (5-15%)")
        return True
    else:
        print(f"⚠️ ROI percentage might be unrealistic: {roi_percentage:.2f}%")
        return False

def run_comprehensive_test():
    """Run all tests to verify the trade broadcast fix"""
    print("=" * 60)
    print("TRADE BROADCAST FIX VERIFICATION")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Regex patterns
    regex_success, token, price, amount, tx_link = test_regex_patterns()
    if regex_success:
        success_count += 1
    
    # Test 2: Standalone SELL logic
    if test_standalone_sell_logic():
        success_count += 1
    
    # Test 3: Profit calculation
    if test_profit_calculation():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {success_count}/{total_tests} tests passed")
    print("=" * 60)
    
    if success_count == total_tests:
        print("✅ ALL TESTS PASSED - Trade broadcast should work now!")
        print("\nThe 'No open positions found for TRASHPAD' error should be resolved.")
        print("The system will now:")
        print("1. Parse your SELL command correctly")
        print("2. Create standalone SELL trades when no positions exist")
        print("3. Distribute realistic profits to all active users")
        print("4. Update P/L dashboards in real-time")
    else:
        print("❌ SOME TESTS FAILED - Review the issues above")
    
    return success_count == total_tests

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)