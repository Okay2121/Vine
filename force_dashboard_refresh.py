#!/usr/bin/env python3
"""
Force Dashboard Refresh
======================
Clear any cached data and force refresh of dashboard calculations
"""

from app import app, db
from models import User, Transaction, DailySnapshot
from performance_tracking import get_performance_data, update_daily_snapshot
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

def force_refresh_user_data(telegram_id='7611754415'):
    """Force refresh performance data for a specific user."""
    
    with app.app_context():
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            print(f"User with telegram_id {telegram_id} not found")
            return
            
        print(f"Force refreshing data for user {user.id} ({telegram_id})")
        
        # Force update daily snapshot
        today = datetime.utcnow().date()
        existing_snapshot = DailySnapshot.query.filter_by(
            user_id=user.id,
            date=today
        ).first()
        
        if existing_snapshot:
            print(f"Deleting existing daily snapshot for {today}")
            db.session.delete(existing_snapshot)
            db.session.commit()
        
        # Create fresh snapshot
        update_daily_snapshot(user.id)
        
        # Get fresh performance data
        performance_data = get_performance_data(user.id)
        
        if performance_data:
            print("\nFresh Performance Data:")
            print(f"  Current Balance: {performance_data['current_balance']:.6f} SOL")
            print(f"  Today's Profit: {performance_data['today_profit']:.6f} SOL ({performance_data['today_percentage']:.2f}%)")
            print(f"  Total Profit: {performance_data['total_profit']:.6f} SOL ({performance_data['total_percentage']:.2f}%)")
            
            # Calculate what the starting balance should be
            starting_balance = performance_data['current_balance'] - performance_data['today_profit']
            print(f"  Starting Balance Today: {starting_balance:.6f} SOL")
            
            # Verify percentage calculation
            if starting_balance > 0:
                expected_percentage = (performance_data['today_profit'] / starting_balance) * 100
                print(f"  Expected Percentage: {expected_percentage:.2f}%")
                
                if abs(expected_percentage - performance_data['today_percentage']) < 0.01:
                    print("  ✅ Percentage calculation is correct")
                else:
                    print(f"  ⚠️ Percentage mismatch: expected {expected_percentage:.2f}%, got {performance_data['today_percentage']:.2f}%")
            
            return performance_data
        else:
            print("❌ Failed to get performance data")
            return None

def simulate_dashboard_messages(performance_data):
    """Simulate how the dashboard messages will look with the new data."""
    
    if not performance_data:
        print("No performance data to simulate")
        return
        
    print("\n" + "="*50)
    print("SIMULATED DASHBOARD OUTPUTS")
    print("="*50)
    
    # Autopilot Dashboard simulation
    current_balance = performance_data['current_balance']
    today_profit_amount = performance_data['today_profit']
    today_profit_percentage = performance_data['today_percentage']
    total_profit_amount = performance_data['total_profit']
    total_profit_percentage = performance_data['total_percentage']
    
    autopilot_message = (
        "📊 *Autopilot Dashboard*\n\n"
        f"• *Balance:* {current_balance:.2f} SOL\n"
        f"• *Today's Profit:* {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}%)\n"
        f"• *Total Profit:* +{total_profit_percentage:.1f}% ({total_profit_amount:.2f} SOL)\n"
    )
    
    print("\nAUTOPILOT DASHBOARD:")
    print(autopilot_message)
    
    # Performance Dashboard simulation
    performance_message = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
    performance_message += "💰 *BALANCE*\n"
    performance_message += f"Current: {current_balance:.2f} SOL\n"
    
    if total_profit_amount >= 0:
        performance_message += f"Profit: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)\n\n"
    else:
        performance_message += f"Profit: {total_profit_amount:.2f} SOL ({total_profit_percentage:.1f}%)\n\n"
    
    performance_message += "📈 *TODAY'S PERFORMANCE*\n"
    starting_balance = current_balance - today_profit_amount
    
    if today_profit_amount > 0:
        performance_message += f"Profit today: +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)\n"
    elif today_profit_amount < 0:
        performance_message += f"Today: {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}%)\n"
    else:
        performance_message += "No profit recorded yet today\n"
    
    performance_message += f"Starting: {starting_balance:.2f} SOL\n"
    
    print("\nPERFORMANCE DASHBOARD:")
    print(performance_message)

def main():
    """Main function to force refresh dashboard data."""
    
    print("Dashboard Data Force Refresh")
    print("=" * 40)
    
    # Force refresh the data
    performance_data = force_refresh_user_data()
    
    # Simulate the dashboard outputs
    simulate_dashboard_messages(performance_data)
    
    print("\n" + "=" * 40)
    print("Dashboard refresh complete. The bot should now show updated values.")

if __name__ == "__main__":
    main()