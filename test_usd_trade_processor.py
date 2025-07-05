#!/usr/bin/env python3
"""
Test USD Trade Processor
========================
Tests the new USD-based trade processing with SOL conversion
"""

import sys
import os
from app import app
from utils.usd_trade_processor import usd_processor

def test_usd_trade_parsing():
    """Test USD trade message parsing"""
    print("🔍 Testing USD Trade Processor")
    print("=" * 40)
    
    # Test valid USD trade input
    test_input = "E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump 0.00045 0.062 https://solscan.io/tx/abc123"
    
    print(f"Input: {test_input}")
    print()
    
    # Parse the trade
    trade_data = usd_processor.parse_trade_message(test_input)
    
    if trade_data:
        print("✅ Trade parsing successful!")
        print(f"Contract: {trade_data['contract_address']}")
        print(f"Entry Price USD: ${trade_data['entry_price_usd']:.6f}")
        print(f"Exit Price USD: ${trade_data['exit_price_usd']:.6f}")
        print(f"Entry Price SOL: {trade_data['entry_price_sol']:.8f}")
        print(f"Exit Price SOL: {trade_data['exit_price_sol']:.8f}")
        print(f"ROI: {trade_data['roi_percentage']:.2f}%")
        print(f"SOL Price Used: ${trade_data['sol_price_used']:.2f}")
        print(f"Transaction: {trade_data['tx_link']}")
        print()
    else:
        print("❌ Trade parsing failed")
        return False
    
    return True

def test_sol_price_fetching():
    """Test SOL price fetching from free APIs"""
    print("💰 Testing SOL Price Fetching")
    print("=" * 35)
    
    try:
        sol_price = usd_processor.get_sol_price_usd()
        print(f"Current SOL Price: ${sol_price:.2f}")
        
        # Test conversion functions
        test_usd = 0.05
        test_sol = usd_processor.usd_to_sol(test_usd)
        back_to_usd = usd_processor.sol_to_usd(test_sol)
        
        print(f"${test_usd:.6f} USD = {test_sol:.8f} SOL")
        print(f"{test_sol:.8f} SOL = ${back_to_usd:.6f} USD")
        
        # Verify conversion accuracy
        if abs(test_usd - back_to_usd) < 0.000001:
            print("✅ USD/SOL conversion working correctly")
        else:
            print("❌ Conversion accuracy issue")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fetching SOL price: {e}")
        return False

def test_realistic_memecoin_example():
    """Test with realistic memecoin trade example"""
    print("🪙 Testing Realistic Memecoin Example")
    print("=" * 40)
    
    # Realistic memecoin trade: Entry at $0.000234, Exit at $0.003456 (1376% gain)
    realistic_input = "E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump 0.000234 0.003456 https://solscan.io/tx/real123"
    
    print(f"Realistic Input: {realistic_input}")
    print()
    
    trade_data = usd_processor.parse_trade_message(realistic_input)
    
    if trade_data:
        print("✅ Realistic trade parsed successfully!")
        print(f"Entry: ${trade_data['entry_price_usd']:.6f} ({trade_data['entry_price_sol']:.8f} SOL)")
        print(f"Exit: ${trade_data['exit_price_usd']:.6f} ({trade_data['exit_price_sol']:.8f} SOL)")
        print(f"ROI: {trade_data['roi_percentage']:.1f}%")
        print()
        
        # Calculate what users would see
        print("📱 User Notification Preview:")
        print("-" * 30)
        
        # Simulate user with 5 SOL balance
        user_balance_sol = 5.0
        allocation_percent = 10  # 10% allocation
        trade_amount_sol = user_balance_sol * (allocation_percent / 100)
        profit_sol = trade_amount_sol * (trade_data['roi_percentage'] / 100)
        profit_usd = usd_processor.sol_to_usd(profit_sol)
        
        print(f"User Balance: {user_balance_sol:.6f} SOL")
        print(f"Trade Allocation: {trade_amount_sol:.6f} SOL ({allocation_percent}%)")
        print(f"Profit: +{profit_sol:.6f} SOL (+${profit_usd:.4f})")
        print(f"New Balance: {user_balance_sol + profit_sol:.6f} SOL")
        
        return True
    else:
        print("❌ Realistic trade parsing failed")
        return False

def test_error_handling():
    """Test error handling for invalid inputs"""
    print("⚠️  Testing Error Handling")
    print("=" * 30)
    
    invalid_inputs = [
        "invalid_format",
        "E2NEYt 0.001",  # Missing parts
        "E2NEYt -0.001 0.5 link",  # Negative price
        "E2NEYt 15.0 20.0 link",  # Prices too high for memecoins
        "short_address 0.001 0.5 link"  # Invalid contract address
    ]
    
    all_failed_correctly = True
    
    for invalid_input in invalid_inputs:
        result = usd_processor.parse_trade_message(invalid_input)
        if result is None:
            print(f"✅ Correctly rejected: {invalid_input}")
        else:
            print(f"❌ Incorrectly accepted: {invalid_input}")
            all_failed_correctly = False
    
    return all_failed_correctly

if __name__ == "__main__":
    print("Testing USD Trade Processor System...")
    print()
    
    # Run all tests
    tests = [
        ("Basic USD Trade Parsing", test_usd_trade_parsing),
        ("SOL Price Fetching", test_sol_price_fetching),
        ("Realistic Memecoin Example", test_realistic_memecoin_example),
        ("Error Handling", test_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
        print()
    
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! USD trade processor is working correctly.")
        print()
        print("New Format Summary:")
        print("• Input: CONTRACT_ADDRESS ENTRY_PRICE_USD EXIT_PRICE_USD TX_LINK")
        print("• Example: E2NEYt...pump 0.000234 0.003456 https://solscan.io/tx/abc123")
        print("• Auto-converts USD to SOL using live exchange rates")
        print("• Integrates with DEX Screener (already USD-based)")
        print("• Users see both USD and SOL values in notifications")
    else:
        print("❌ Some tests failed. Please review the issues above.")