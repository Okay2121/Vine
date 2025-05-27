"""
Create sample trading positions for broadcasted trades
This will make the trades appear in active users' position feeds
"""
from app import app, db
from models import User, TradingPosition, UserStatus
from datetime import datetime

def create_broadcast_positions():
    """Create sample positions for all active users based on recent broadcasts"""
    
    with app.app_context():
        # Get all active users
        active_users = User.query.filter_by(status=UserStatus.ACTIVE).all()
        
        if not active_users:
            print("No active users found. Let me check all users...")
            all_users = User.query.all()
            print(f"Found {len(all_users)} total users")
            
            # Use users with balance > 0 instead
            active_users = User.query.filter(User.balance > 0).all()
            print(f"Found {len(active_users)} users with balance > 0")
        
        if not active_users:
            print("No users found to create positions for")
            return
            
        print(f"Creating positions for {len(active_users)} users...")
        
        # Sample broadcast trades (you can modify these to match your actual broadcasts)
        sample_trades = [
            {
                'token_name': 'ZING',
                'amount': 812345,
                'entry_price': 0.004107,
                'current_price': 0.004107,
                'trade_type': 'buy',
                'status': 'open'
            },
            {
                'token_name': 'PEPE',
                'amount': 1000000,
                'entry_price': 0.000023,
                'current_price': 0.000025,
                'trade_type': 'buy', 
                'status': 'open'
            }
        ]
        
        created_count = 0
        current_time = datetime.utcnow()
        
        for user in active_users:
            for trade in sample_trades:
                try:
                    # Check if position already exists for this user and token
                    existing = TradingPosition.query.filter_by(
                        user_id=user.id,
                        token_name=trade['token_name'],
                        trade_type=trade['trade_type']
                    ).first()
                    
                    if existing:
                        print(f"Position already exists for user {user.id} - {trade['token_name']}")
                        continue
                    
                    # Create new position
                    position = TradingPosition(
                        user_id=user.id,
                        token_name=trade['token_name'],
                        amount=trade['amount'],
                        entry_price=trade['entry_price'],
                        current_price=trade['current_price'],
                        timestamp=current_time,
                        status=trade['status'],
                        trade_type=trade['trade_type']
                    )
                    
                    # Add buy-specific fields
                    if hasattr(position, 'buy_timestamp'):
                        position.buy_timestamp = current_time
                    
                    db.session.add(position)
                    created_count += 1
                    print(f"Created {trade['token_name']} position for user {user.telegram_id}")
                    
                except Exception as e:
                    print(f"Error creating position for user {user.id}: {e}")
                    continue
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"✅ Successfully created {created_count} trading positions!")
            print("These should now appear in users' Position feeds")
        except Exception as e:
            print(f"❌ Error committing to database: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_broadcast_positions()