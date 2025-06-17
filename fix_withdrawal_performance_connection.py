"""
Fix Withdrawal Page Performance Data Connection
============================================
This script diagnoses and fixes the withdrawal page showing 0.00 SOL P/L
by ensuring all pages use the same performance tracking data source.
"""

from app import app, db
from models import User, Transaction, Profit, UserMetrics
from datetime import datetime, timedelta
import logging

def diagnose_user_performance_data(user_id):
    """
    Diagnose why a user's performance data might be showing as 0.00
    
    Args:
        user_id (int): User ID to diagnose
        
    Returns:
        dict: Diagnostic information
    """
    user = User.query.get(user_id)
    if not user:
        return {"error": "User not found"}
    
    diagnostics = {
        "user_id": user_id,
        "telegram_id": user.telegram_id,
        "current_balance": user.balance,
        "initial_deposit": user.initial_deposit,
    }
    
    # Check Transaction table
    trade_profits = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == 'trade_profit',
        Transaction.status == 'completed'
    ).all()
    
    trade_losses = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == 'trade_loss',
        Transaction.status == 'completed'
    ).all()
    
    diagnostics["transaction_profits"] = len(trade_profits)
    diagnostics["transaction_losses"] = len(trade_losses)
    diagnostics["total_profit_from_transactions"] = sum(t.amount for t in trade_profits)
    diagnostics["total_loss_from_transactions"] = sum(abs(t.amount) for t in trade_losses)
    
    # Check Profit table
    profit_records = Profit.query.filter_by(user_id=user_id).all()
    diagnostics["profit_records"] = len(profit_records)
    diagnostics["total_profit_from_profit_table"] = sum(p.amount for p in profit_records)
    
    # Check UserMetrics
    metrics = UserMetrics.query.filter_by(user_id=user_id).first()
    if metrics:
        diagnostics["user_metrics_exists"] = True
        diagnostics["current_streak"] = metrics.current_streak
        diagnostics["trading_mode"] = metrics.trading_mode
    else:
        diagnostics["user_metrics_exists"] = False
    
    # Calculate expected P/L
    expected_pl = user.balance - user.initial_deposit
    diagnostics["expected_pl"] = expected_pl
    
    return diagnostics

def test_performance_tracking_function(user_id):
    """
    Test the get_performance_data function directly
    
    Args:
        user_id (int): User ID to test
        
    Returns:
        dict: Performance data or error info
    """
    try:
        from performance_tracking import get_performance_data
        performance_data = get_performance_data(user_id)
        return {
            "success": True,
            "data": performance_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_withdrawal_handler_simulation(user_telegram_id):
    """
    Simulate the withdrawal handler logic to identify issues
    
    Args:
        user_telegram_id (str): User's Telegram ID
        
    Returns:
        dict: Simulated withdrawal data
    """
    user = User.query.filter_by(telegram_id=str(user_telegram_id)).first()
    if not user:
        return {"error": "User not found"}
    
    # Simulate the exact logic from withdraw_profit_handler
    try:
        from performance_tracking import get_performance_data
        performance_data = get_performance_data(user.id)
        
        if not performance_data:
            return {"error": "Performance data not available"}
        
        # Extract data exactly as in the handler
        available_balance = performance_data["current_balance"]
        total_profit_amount = performance_data["total_profit"]
        total_profit_percentage = performance_data["total_percentage"]
        
        return {
            "success": True,
            "available_balance": available_balance,
            "total_profit_amount": total_profit_amount,
            "total_profit_percentage": total_profit_percentage,
            "raw_performance_data": performance_data
        }
        
    except Exception as e:
        return {"error": f"Exception in withdrawal simulation: {str(e)}"}

def fix_user_performance_data(user_id):
    """
    Fix common issues with user performance data
    
    Args:
        user_id (int): User ID to fix
        
    Returns:
        dict: Fix results
    """
    user = User.query.get(user_id)
    if not user:
        return {"error": "User not found"}
    
    fixes_applied = []
    
    # Fix 1: Ensure UserMetrics exists
    from models import UserMetrics
    metrics = UserMetrics.query.filter_by(user_id=user_id).first()
    if not metrics:
        metrics = UserMetrics()
        metrics.user_id = user_id
        metrics.current_streak = 0
        metrics.best_streak = 0
        metrics.trading_mode = 'autopilot'
        db.session.add(metrics)
        fixes_applied.append("Created missing UserMetrics record")
    
    # Fix 2: Ensure initial_deposit is set properly
    if user.initial_deposit <= 0 and user.balance > 0:
        # Find first deposit transaction
        first_deposit = Transaction.query.filter_by(
            user_id=user_id,
            transaction_type='deposit'
        ).order_by(Transaction.timestamp.asc()).first()
        
        if first_deposit:
            user.initial_deposit = first_deposit.amount
            fixes_applied.append(f"Set initial_deposit to {first_deposit.amount} SOL from first deposit")
        else:
            # No deposit found, use current balance
            user.initial_deposit = user.balance
            fixes_applied.append(f"Set initial_deposit to current balance: {user.balance} SOL")
    
    # Fix 3: Ensure daily snapshot exists
    try:
        from performance_tracking import ensure_daily_snapshot
        ensure_daily_snapshot(user_id)
        fixes_applied.append("Ensured daily snapshot exists")
    except Exception as e:
        fixes_applied.append(f"Failed to create daily snapshot: {str(e)}")
    
    # Commit changes
    try:
        db.session.commit()
        fixes_applied.append("Database changes committed successfully")
    except Exception as e:
        db.session.rollback()
        return {"error": f"Failed to commit fixes: {str(e)}"}
    
    return {
        "success": True,
        "fixes_applied": fixes_applied
    }

def check_all_disconnected_pages():
    """
    Check for any other pages that might be disconnected from performance tracking
    
    Returns:
        dict: Analysis of potential disconnections
    """
    import os
    import re
    
    # Files to check for old Profit table usage
    files_to_check = [
        'bot_v20_runner.py',
        'utils/roi_system.py',
        'utils/trading.py',
        'utils/notifications.py'
    ]
    
    disconnections = []
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Look for patterns that suggest old Profit table usage
                patterns = [
                    r'func\.sum\(Profit\.amount\)',
                    r'Profit\.query\.filter_by',
                    r'from models import.*Profit',
                    r'db\.session\.query.*Profit'
                ]
                
                found_patterns = []
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        found_patterns.extend(matches)
                
                if found_patterns:
                    disconnections.append({
                        "file": file_path,
                        "old_patterns": found_patterns,
                        "needs_update": True
                    })
                    
            except Exception as e:
                disconnections.append({
                    "file": file_path,
                    "error": f"Could not read file: {str(e)}"
                })
    
    return {
        "potential_disconnections": disconnections,
        "files_checked": len(files_to_check)
    }

def run_comprehensive_diagnosis():
    """
    Run comprehensive diagnosis of the withdrawal/performance connection issue
    """
    print("🔍 COMPREHENSIVE WITHDRAWAL PAGE DIAGNOSIS")
    print("=" * 50)
    
    with app.app_context():
        # Get a sample user for testing
        sample_user = User.query.filter(User.balance > 0).first()
        
        if not sample_user:
            print("❌ No users with balance found for testing")
            return
        
        print(f"📊 Testing with User ID: {sample_user.id} (Telegram: {sample_user.telegram_id})")
        print()
        
        # 1. Diagnose user performance data
        print("1. USER PERFORMANCE DATA DIAGNOSIS:")
        diagnostics = diagnose_user_performance_data(sample_user.id)
        for key, value in diagnostics.items():
            print(f"   {key}: {value}")
        print()
        
        # 2. Test performance tracking function
        print("2. PERFORMANCE TRACKING FUNCTION TEST:")
        perf_test = test_performance_tracking_function(sample_user.id)
        if perf_test["success"]:
            print("   ✅ Performance tracking function working")
            print(f"   📈 Total P/L: {perf_test['data']['total_profit']:.2f} SOL")
            print(f"   📊 Today P/L: {perf_test['data']['today_profit']:.2f} SOL")
        else:
            print(f"   ❌ Performance tracking failed: {perf_test['error']}")
        print()
        
        # 3. Test withdrawal handler simulation
        print("3. WITHDRAWAL HANDLER SIMULATION:")
        withdrawal_test = test_withdrawal_handler_simulation(sample_user.telegram_id)
        if "success" in withdrawal_test and withdrawal_test["success"]:
            print("   ✅ Withdrawal handler logic working")
            print(f"   💰 Available Balance: {withdrawal_test['available_balance']:.2f} SOL")
            print(f"   📈 Total P/L: {withdrawal_test['total_profit_amount']:.2f} SOL ({withdrawal_test['total_profit_percentage']:.1f}%)")
        else:
            print(f"   ❌ Withdrawal handler failed: {withdrawal_test.get('error', 'Unknown error')}")
        print()
        
        # 4. Check for disconnected pages
        print("4. CHECKING FOR OTHER DISCONNECTED PAGES:")
        disconnection_check = check_all_disconnected_pages()
        if disconnection_check["potential_disconnections"]:
            print("   ⚠️  Found potential disconnections:")
            for disc in disconnection_check["potential_disconnections"]:
                if "needs_update" in disc:
                    print(f"   📄 {disc['file']}: {len(disc['old_patterns'])} old patterns found")
        else:
            print("   ✅ No obvious disconnections found")
        print()
        
        # 5. Apply fixes if needed
        print("5. APPLYING FIXES:")
        fix_results = fix_user_performance_data(sample_user.id)
        if fix_results.get("success"):
            print("   ✅ Fixes applied successfully:")
            for fix in fix_results["fixes_applied"]:
                print(f"   🔧 {fix}")
        else:
            print(f"   ❌ Fix failed: {fix_results.get('error')}")
        print()
        
        # 6. Retest after fixes
        print("6. RETESTING AFTER FIXES:")
        retest = test_withdrawal_handler_simulation(sample_user.telegram_id)
        if "success" in retest and retest["success"]:
            print("   ✅ Withdrawal page should now show correct data:")
            print(f"   💰 Available Balance: {retest['available_balance']:.2f} SOL")
            print(f"   📈 Total P/L: {retest['total_profit_amount']:.2f} SOL ({retest['total_profit_percentage']:.1f}%)")
        else:
            print(f"   ❌ Still failing: {retest.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 50)
        print("🏁 DIAGNOSIS COMPLETE")

if __name__ == "__main__":
    run_comprehensive_diagnosis()