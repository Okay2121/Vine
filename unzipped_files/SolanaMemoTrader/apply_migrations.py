from app import app, db
from models import SupportTicket

def apply_migrations():
    """Apply database migrations for new tables."""
    with app.app_context():
        # Create only the new tables
        db.create_all()
        print("Database migrations applied successfully.")

if __name__ == "__main__":
    apply_migrations()