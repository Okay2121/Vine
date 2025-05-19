"""
Script to add notes column to Transaction table using Flask-SQLAlchemy
"""
from app import app, db
import sqlalchemy as sa
from sqlalchemy import text

def add_notes_column():
    print("Adding notes column to transaction table...")
    
    with app.app_context():
        # Check if column exists first
        connection = db.engine.connect()
        inspector = sa.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('transaction')]
        
        if 'notes' not in columns:
            # Using raw SQL to add the column
            sql = text("ALTER TABLE transaction ADD COLUMN notes TEXT;")
            connection.execute(sql)
            connection.commit()
            print("Notes column added successfully to transaction table.")
        else:
            print("Notes column already exists in transaction table.")
        
        connection.close()

if __name__ == "__main__":
    add_notes_column()