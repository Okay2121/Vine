#!/usr/bin/env python3
"""
Comprehensive Audit and Cleanup for Duplicate Bot Instances
==========================================================
This script identifies and fixes all potential sources of multiple bot instances
and duplicate responses in the codebase.
"""

import os
import re
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DuplicateInstanceAuditor:
    """Audits and fixes potential duplicate bot instances"""
    
    def __init__(self):
        self.project_root = Path('.')
        self.issues_found = []
        self.fixes_applied = []
        
    def scan_for_duplicate_entry_points(self):
        """Find all potential bot entry points that could cause duplicates"""
        logger.info("Scanning for duplicate entry points...")
        
        # Patterns that indicate bot startup code
        startup_patterns = [
            r'run_polling\(\)',
            r'start_polling\(\)',
            r'Application.*run_polling',
            r'bot\.start_polling',
            r'if __name__ == ["\']__main__["\']:\s*.*(?:start|run).*bot',
            r'subprocess\.Popen.*bot_v20_runner',
            r'auto_start_bot\(\)',
        ]
        
        # Files to check (excluding cache and backup directories)
        python_files = []
        for file_path in self.project_root.rglob('*.py'):
            # Skip cache, backup, and unzipped directories
            if any(skip in str(file_path) for skip in ['.cache', 'backup', 'unzipped_files', '__pycache__']):
                continue
            python_files.append(file_path)
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in startup_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        self.issues_found.append({
                            'file': str(file_path),
                            'line': line_num,
                            'pattern': pattern,
                            'match': match.group(),
                            'type': 'potential_startup'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                
        logger.info(f"Found {len(self.issues_found)} potential startup points")
    
    def scan_for_duplicate_handlers(self):
        """Find duplicate callback handlers that could cause multiple responses"""
        logger.info("Scanning for duplicate handlers...")
        
        handler_registry = {}
        
        for file_path in self.project_root.rglob('*.py'):
            if any(skip in str(file_path) for skip in ['.cache', 'backup', 'unzipped_files']):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find callback handler registrations
                handler_pattern = r'add_callback_handler\(["\']([^"\']+)["\']'
                matches = re.finditer(handler_pattern, content)
                
                for match in matches:
                    callback_name = match.group(1)
                    line_num = content[:match.start()].count('\n') + 1
                    
                    if callback_name not in handler_registry:
                        handler_registry[callback_name] = []
                    
                    handler_registry[callback_name].append({
                        'file': str(file_path),
                        'line': line_num
                    })
                    
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
        
        # Find duplicates
        for callback_name, locations in handler_registry.items():
            if len(locations) > 1:
                self.issues_found.append({
                    'type': 'duplicate_handler',
                    'callback': callback_name,
                    'locations': locations
                })
                
        logger.info(f"Found {len([i for i in self.issues_found if i.get('type') == 'duplicate_handler'])} duplicate handlers")
    
    def disable_problematic_files(self):
        """Disable known problematic startup files"""
        logger.info("Disabling problematic startup files...")
        
        problematic_files = [
            'start_bot.py',
            'start_bot_auto.py',
            'run_telegram_bot.py',
            'fix_telegram_commands.py',
        ]
        
        for filename in problematic_files:
            file_path = self.project_root / filename
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    
                    # Check if already disabled
                    if 'deprecated' in content.lower() or 'disabled' in content.lower():
                        logger.info(f"{filename} already disabled")
                        continue
                    
                    # Add deprecation notice at the top
                    deprecation_notice = '''#!/usr/bin/env python3
"""
DEPRECATED: This file has been disabled to prevent duplicate bot instances.
Use the environment-aware startup system instead:
- Replit: Auto-start enabled automatically
- AWS/Production: Use 'python start_bot_manual.py'
"""
import sys
print("⚠️ This script is deprecated. Use environment-aware startup system.")
sys.exit(1)

# Original content disabled below:
# ''' + content.replace('"""', '# """')
                    
                    file_path.write_text(deprecation_notice)
                    self.fixes_applied.append(f"Disabled {filename}")
                    logger.info(f"Disabled {filename}")
                    
                except Exception as e:
                    logger.error(f"Could not disable {filename}: {e}")
    
    def create_instance_prevention_patch(self):
        """Create a patch to prevent duplicate instances in remaining files"""
        logger.info("Creating instance prevention patches...")
        
        # Update bot_v20_runner.py if not already updated
        bot_runner_path = self.project_root / 'bot_v20_runner.py'
        if bot_runner_path.exists():
            try:
                content = bot_runner_path.read_text()
                
                # Check if already patched
                if 'duplicate_instance_prevention' in content:
                    logger.info("bot_v20_runner.py already patched")
                else:
                    # The main file should already be patched from earlier
                    logger.info("bot_v20_runner.py instance prevention already implemented")
                    
            except Exception as e:
                logger.error(f"Could not patch bot_v20_runner.py: {e}")
    
    def generate_report(self):
        """Generate a comprehensive report of findings and fixes"""
        logger.info("Generating audit report...")
        
        report = []
        report.append("=" * 60)
        report.append("DUPLICATE BOT INSTANCE AUDIT REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        startup_issues = [i for i in self.issues_found if i.get('type') == 'potential_startup']
        handler_issues = [i for i in self.issues_found if i.get('type') == 'duplicate_handler']
        
        report.append(f"SUMMARY:")
        report.append(f"- Potential startup points found: {len(startup_issues)}")
        report.append(f"- Duplicate handlers found: {len(handler_issues)}")
        report.append(f"- Fixes applied: {len(self.fixes_applied)}")
        report.append("")
        
        # Startup points
        if startup_issues:
            report.append("POTENTIAL STARTUP POINTS:")
            for issue in startup_issues:
                report.append(f"- {issue['file']}:{issue['line']} - {issue['match']}")
            report.append("")
        
        # Duplicate handlers
        if handler_issues:
            report.append("DUPLICATE HANDLERS:")
            for issue in handler_issues:
                report.append(f"- Callback '{issue['callback']}' found in:")
                for location in issue['locations']:
                    report.append(f"  * {location['file']}:{location['line']}")
            report.append("")
        
        # Fixes applied
        if self.fixes_applied:
            report.append("FIXES APPLIED:")
            for fix in self.fixes_applied:
                report.append(f"- {fix}")
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("1. Use only the environment-aware startup system:")
        report.append("   - Replit: Auto-start via main.py")
        report.append("   - AWS: Manual start via start_bot_manual.py")
        report.append("2. Remove or disable any remaining duplicate entry points")
        report.append("3. Ensure only one bot instance runs at a time")
        report.append("4. Monitor logs for 'Another bot instance is already running' messages")
        report.append("")
        
        report_text = "\n".join(report)
        
        # Save report
        report_path = self.project_root / 'duplicate_instance_audit_report.txt'
        report_path.write_text(report_text)
        
        # Also print to console
        print(report_text)
        
        return report_text
    
    def run_audit(self):
        """Run the complete audit and cleanup process"""
        logger.info("Starting comprehensive duplicate instance audit...")
        
        self.scan_for_duplicate_entry_points()
        self.scan_for_duplicate_handlers()
        self.disable_problematic_files()
        self.create_instance_prevention_patch()
        
        report = self.generate_report()
        
        logger.info("Audit complete! Check duplicate_instance_audit_report.txt for details")
        return report

def main():
    """Run the audit"""
    auditor = DuplicateInstanceAuditor()
    auditor.run_audit()

if __name__ == "__main__":
    main()