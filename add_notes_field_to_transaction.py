"""
Add notes field to Transaction table migration script
"""
from app import app, db
from alembic import op
import sqlalchemy as sa

def run_migration():
    print("Adding notes column to transaction table...")
    
    with app.app_context():
        # Check if the column already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('transaction')]
        
        if 'notes' not in columns:
            # Add the notes column
            op.add_column('transaction', sa.Column('notes', sa.Text, nullable=True))
            print("Notes column added successfully to transaction table.")
        else:
            print("Notes column already exists in transaction table.")

if __name__ == "__main__":
    run_migration()