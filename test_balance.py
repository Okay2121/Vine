from app import app, db
from models import User, Transaction

def check_balances():
    with app.app_context():
        users = User.query.all()
        for user in users:
            print(f'User: {user.username}, Balance: {user.balance}')

if __name__ == "__main__":
    check_balances()
