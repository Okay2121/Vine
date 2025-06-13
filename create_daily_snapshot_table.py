#!/usr/bin/env python3
"""
Create DailySnapshot table for performance tracking
"""
import os
import sys
from app import app, db
from models import DailySnapshot

def create_daily_snapshot_table():
    """Create the DailySnapshot table"""
    try:
        with app.app_context():
            # Create the table
            db.create_all()
            print("✓ DailySnapshot table created successfully")
            return True
    except Exception as e:
        print(f"✗ Error creating DailySnapshot table: {e}")
        return False

if __name__ == "__main__":
    success = create_daily_snapshot_table()
    if success:
        print("Database tables updated successfully")
        sys.exit(0)
    else:
        print("Failed to update database tables")
        sys.exit(1)