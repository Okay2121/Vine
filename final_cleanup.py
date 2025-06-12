"""
Final Database Cleanup - Direct SQL execution
"""
from dotenv import load_dotenv
load_dotenv()

from app import app, db
from sqlalchemy import text

def execute_cleanup():
    """Execute direct SQL cleanup commands"""
    with app.app_context():
        with db.engine.connect() as conn:
            # Execute deletions in sequence
            commands = [
                "DELETE FROM trading_position;",
                "DELETE FROM transaction;", 
                "DELETE FROM support_ticket;",
                "DELETE FROM referral_reward;",
                "DELETE FROM referral_code;",
                "DELETE FROM profit;",
                "DELETE FROM broadcast_message;",
                "DELETE FROM admin_message;",
                "DELETE FROM \"user\";"
            ]
            
            for cmd in commands:
                try:
                    result = conn.execute(text(cmd))
                    conn.commit()
                    print(f"Executed: {cmd}")
                except Exception as e:
                    print(f"Skip {cmd}: {e}")
            
            # Final verification
            result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
            count = result.scalar()
            print(f"Final user count: {count}")

if __name__ == "__main__":
    execute_cleanup()