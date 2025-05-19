#!/usr/bin/env python
"""
Admin Balance Report Tool - Generates detailed reports on balance adjustments
"""
import os
import csv
import logging
import argparse
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app import app, db
from models import User, Transaction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def generate_adjustment_report(days=7, username=None, export_csv=False):
    """
    Generate a report of all admin balance adjustments for a specified time period
    
    Args:
        days (int): Number of days to look back for adjustments (default: 7)
        username (str): Optional username to filter report for a specific user
        export_csv (bool): Whether to export the report as CSV
        
    Returns:
        tuple: (report_text, csv_path or None)
    """
    with app.app_context():
        try:
            # Calculate the start date
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Build base query for admin adjustments
            query = (
                db.session.query(
                    Transaction, 
                    User.username, 
                    User.telegram_id
                )
                .join(User, User.id == Transaction.user_id)
                .filter(
                    Transaction.transaction_type.in_(['admin_credit', 'admin_debit']),
                    Transaction.timestamp >= start_date
                )
            )
            
            # Apply username filter if provided
            if username:
                # Handle @ prefix
                if username.startswith('@'):
                    username = username[1:]
                # Case-insensitive search
                query = query.filter(func.lower(User.username) == func.lower(username))
            
            # Order by timestamp (most recent first)
            query = query.order_by(desc(Transaction.timestamp))
            
            # Execute query
            adjustments = query.all()
            
            if not adjustments:
                return f"No admin balance adjustments found in the past {days} days.", None
            
            # Generate text report
            report_lines = [
                f"📊 Admin Balance Adjustment Report",
                f"Period: Past {days} days ({start_date.strftime('%Y-%m-%d')} to {datetime.utcnow().strftime('%Y-%m-%d')})",
                f"Total Adjustments: {len(adjustments)}",
                f"",
                f"{'ID':<5} {'Date':<12} {'User':<15} {'Type':<10} {'Amount':<10} {'Reason':<30}"
            ]
            
            # Calculate totals
            total_added = 0
            total_deducted = 0
            
            # Add adjustment details
            for tx, username, telegram_id in adjustments:
                username_display = f"@{username}" if username else f"ID:{telegram_id}"
                tx_type = "ADDED" if tx.transaction_type == 'admin_credit' else "DEDUCTED"
                date_str = tx.timestamp.strftime("%Y-%m-%d")
                
                report_lines.append(
                    f"{tx.id:<5} {date_str:<12} {username_display:<15} {tx_type:<10} {tx.amount:<10.4f} {tx.notes[:30]:<30}"
                )
                
                # Update totals
                if tx.transaction_type == 'admin_credit':
                    total_added += tx.amount
                else:
                    total_deducted += tx.amount
            
            # Add summary
            report_lines.append("")
            report_lines.append(f"Summary:")
            report_lines.append(f"  Total Added: {total_added:.4f} SOL")
            report_lines.append(f"  Total Deducted: {total_deducted:.4f} SOL")
            report_lines.append(f"  Net Change: {total_added - total_deducted:.4f} SOL")
            
            # Export to CSV if requested
            csv_path = None
            if export_csv:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                user_filter = f"_{username}" if username else ""
                csv_path = f"admin_balance_report{user_filter}_{timestamp}.csv"
                
                with open(csv_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['ID', 'Date', 'Username', 'Telegram ID', 'Type', 'Amount', 'Reason'])
                    
                    for tx, username, telegram_id in adjustments:
                        writer.writerow([
                            tx.id,
                            tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            username,
                            telegram_id,
                            tx.transaction_type,
                            tx.amount,
                            tx.notes
                        ])
                
                logger.info(f"CSV report exported to {csv_path}")
            
            return "\n".join(report_lines), csv_path
            
        except Exception as e:
            logger.error(f"Error generating adjustment report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error generating report: {str(e)}", None

def main():
    """Run the report tool from command line"""
    parser = argparse.ArgumentParser(description='Generate admin balance adjustment report')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back (default: 7)')
    parser.add_argument('--username', type=str, help='Filter by username (with or without @)')
    parser.add_argument('--csv', action='store_true', help='Export report to CSV file')
    
    args = parser.parse_args()
    
    report, csv_path = generate_adjustment_report(args.days, args.username, args.csv)
    
    print(report)
    if csv_path:
        print(f"\nCSV report exported to: {csv_path}")

if __name__ == "__main__":
    main()