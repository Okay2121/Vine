"""
Debug User Data - Check actual user data in database
"""
from app import app, db
from models import User, Transaction, Profit
from sqlalchemy import func

def debug_user_data():
    """Debug user data to understand profit calculation issues"""
    with app.app_context():
        # Get all users
        users = User.query.all()
        print(f"Total users in database: {len(users)}")
        
        for user in users:
            print(f"\n--- USER: {user.username} (ID: {user.id}) ---")
            print(f"Telegram ID: {user.telegram_id}")
            print(f"Balance: {user.balance} SOL")
            print(f"Initial Deposit: {user.initial_deposit} SOL")
            print(f"Status: {user.status}")
            
            # Calculate expected profit
            expected_profit = user.balance - user.initial_deposit
            print(f"Expected Total Profit: {expected_profit} SOL")
            
            # Check Profit table
            profit_records = Profit.query.filter_by(user_id=user.id).all()
            print(f"Profit records in Profit table: {len(profit_records)}")
            
            total_profit_from_table = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
            print(f"Total profit from Profit table: {total_profit_from_table} SOL")
            
            # Check Transaction table for trade_profit
            trade_profit_transactions = Transaction.query.filter_by(
                user_id=user.id, 
                transaction_type='trade_profit',
                status='completed'
            ).all()
            print(f"Trade profit transactions: {len(trade_profit_transactions)}")
            
            total_trade_profit = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type == 'trade_profit',
                Transaction.status == 'completed'
            ).scalar() or 0
            print(f"Total trade profit from transactions: {total_trade_profit} SOL")
            
            # Check all transaction types
            all_transactions = Transaction.query.filter_by(user_id=user.id).all()
            print(f"Total transactions: {len(all_transactions)}")
            
            transaction_types = {}
            for tx in all_transactions:
                tx_type = tx.transaction_type
                if tx_type not in transaction_types:
                    transaction_types[tx_type] = {'count': 0, 'total': 0}
                transaction_types[tx_type]['count'] += 1
                transaction_types[tx_type]['total'] += tx.amount
            
            print("Transaction breakdown:")
            for tx_type, data in transaction_types.items():
                print(f"  {tx_type}: {data['count']} transactions, {data['total']} SOL")

if __name__ == "__main__":
    debug_user_data()