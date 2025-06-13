"""
Test Dashboard Profit Calculations
"""
from app import app, db
from models import User, Transaction, Profit
from sqlalchemy import func
from datetime import datetime, timedelta

def test_dashboard_profits():
    """Test the corrected profit calculation logic"""
    with app.app_context():
        # Get the user
        user = User.query.filter_by(telegram_id="5488280696").first()
        if not user:
            print("User not found!")
            return
            
        print(f"Testing dashboard profits for user: {user.username}")
        print(f"Balance: {user.balance} SOL")
        print(f"Initial Deposit: {user.initial_deposit} SOL")
        print(f"Status: {user.status}")
        
        # Test the corrected profit calculation logic
        total_profit_amount = 0
        total_profit_percentage = 0
        today_profit_amount = 0
        today_profit_percentage = 0
        
        # Calculate profits for users with deposits (regardless of status)
        if user.initial_deposit > 0:
            # Calculate total profit as current balance minus initial deposit
            total_profit_amount = max(0, user.balance - user.initial_deposit)
            total_profit_percentage = (total_profit_amount / user.initial_deposit) * 100 if user.initial_deposit > 0 else 0
            
            # Get today's profits from Transaction table (trade_profit transactions)
            today = datetime.utcnow().date()
            today_profit = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type == 'trade_profit',
                Transaction.timestamp >= today,
                Transaction.status == 'completed'
            ).scalar() or 0
            
            # If no trade_profit transactions today, check Profit table as fallback
            if today_profit == 0:
                today_profit = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id, date=today).scalar() or 0
            
            today_profit_amount = today_profit
            today_profit_percentage = (today_profit / user.balance) * 100 if user.balance > 0 else 0
        
        print(f"\n--- CALCULATED PROFIT METRICS ---")
        print(f"Total Profit Amount: {total_profit_amount:.2f} SOL")
        print(f"Total Profit Percentage: {total_profit_percentage:.1f}%")
        print(f"Today's Profit Amount: {today_profit_amount:.2f} SOL")
        print(f"Today's Profit Percentage: {today_profit_percentage:.1f}%")
        
        # Simulate the dashboard message formatting
        dashboard_message = (
            "📊 *Autopilot Dashboard*\n\n"
            f"• *Balance:* {user.balance:.2f} SOL\n"
            f"• *Today's Profit:* {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}% of balance)\n"
            f"• *Total Profit:* +{total_profit_percentage:.1f}% ({total_profit_amount:.2f} SOL)\n"
        )
        
        print(f"\n--- DASHBOARD MESSAGE ---")
        print(dashboard_message)

if __name__ == "__main__":
    test_dashboard_profits()