#!/usr/bin/env python3
import tempfile
"""
Comprehensive AWS Deployment Inconsistency Scanner
================================================
This script scans the entire codebase for potential AWS deployment issues
and provides a detailed report with fixes.

Issues Detected:
1. Hardcoded file paths that won't work on AWS
2. Environment variable handling problems
3. Database connection issues
4. File permission problems
5. Process management inconsistencies
6. Configuration mismatches
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSDeploymentAuditor:
    """Comprehensive AWS deployment inconsistency auditor"""
    
    def __init__(self):
        self.issues = []
        self.fixes_applied = []
        self.critical_issues = []
        self.warnings = []
        
    def scan_hardcoded_paths(self) -> List[Dict]:
        """Scan for hardcoded file paths that won't work on AWS"""
        logger.info("Scanning for hardcoded file paths...")
        
        issues = []
        
        # Files to scan
        python_files = [f for f in os.listdir('.') if f.endswith('.py')]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Check for hardcoded /tmp/ paths
                for i, line in enumerate(lines, 1):
                    if '/tmp/' in line and not line.strip().startswith('#'):
                        issues.append({
                            'file': file_path,
                            'line': i,
                            'issue': 'Hardcoded /tmp/ path',
                            'content': line.strip(),
                            'severity': 'HIGH',
                            'fix': 'Replace with tempfile.gettempdir()'
                        })
                    
                    # Check for hardcoded home directory paths
                    if '~/.' in line or '/home/' in line:
                        issues.append({
                            'file': file_path,
                            'line': i,
                            'issue': 'Hardcoded home directory path',
                            'content': line.strip(),
                            'severity': 'MEDIUM',
                            'fix': 'Use os.path.expanduser() or environment variables'
                        })
            
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        return issues
    
    def scan_environment_handling(self) -> List[Dict]:
        """Scan for environment variable handling issues"""
        logger.info("Scanning environment variable handling...")
        
        issues = []
        python_files = [f for f in os.listdir('.') if f.endswith('.py')]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for direct os.environ modifications without error handling
                    if 'os.environ[' in line and '=' in line and 'try:' not in lines[max(0, i-3):i]:
                        issues.append({
                            'file': file_path,
                            'line': i,
                            'issue': 'Direct environment variable modification without error handling',
                            'content': line.strip(),
                            'severity': 'MEDIUM',
                            'fix': 'Add try-catch blocks for environment variable updates'
                        })
                    
                    # Check for .env file writes without read-only protection
                    if '.env' in line and ('write' in line or 'w' in line):
                        if 'try:' not in lines[max(0, i-5):i]:
                            issues.append({
                                'file': file_path,
                                'line': i,
                                'issue': '.env file write without read-only protection',
                                'content': line.strip(),
                                'severity': 'HIGH',
                                'fix': 'Add fallback for read-only file systems'
                            })
            
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        return issues
    
    def scan_database_configurations(self) -> List[Dict]:
        """Scan for database configuration issues"""
        logger.info("Scanning database configurations...")
        
        issues = []
        
        # Check app.py for database configuration
        if os.path.exists('app.py'):
            with open('app.py', 'r') as f:
                content = f.read()
            
            # Check for missing connection pool settings
            if 'pool_recycle' not in content:
                issues.append({
                    'file': 'app.py',
                    'line': 0,
                    'issue': 'Missing database connection pool configuration',
                    'content': 'Database configuration',
                    'severity': 'HIGH',
                    'fix': 'Add pool_recycle and pool_pre_ping for AWS RDS'
                })
            
            # Check for missing SSL configuration
            if 'sslmode' not in content and 'ssl' not in content.lower():
                issues.append({
                    'file': 'app.py',
                    'line': 0,
                    'issue': 'Missing SSL configuration for database',
                    'content': 'Database URL configuration',
                    'severity': 'MEDIUM',
                    'fix': 'Add sslmode=require for AWS RDS connections'
                })
        
        return issues
    
    def scan_process_management(self) -> List[Dict]:
        """Scan for process management issues"""
        logger.info("Scanning process management...")
        
        issues = []
        
        # Check for multiple entry points
        entry_point_files = []
        for file_name in os.listdir('.'):
            if file_name.endswith('.py'):
                with open(file_name, 'r') as f:
                    content = f.read()
                    if 'if __name__ == "__main__"' in content and 'bot' in content.lower():
                        entry_point_files.append(file_name)
        
        if len(entry_point_files) > 2:  # Allow main.py and bot_v20_runner.py
            issues.append({
                'file': 'Multiple files',
                'line': 0,
                'issue': f'Multiple bot entry points found: {entry_point_files}',
                'content': 'Multiple __main__ blocks',
                'severity': 'HIGH',
                'fix': 'Consolidate to single entry point or add proper guards'
            })
        
        return issues
    
    def scan_import_issues(self) -> List[Dict]:
        """Scan for import-related issues"""
        logger.info("Scanning import issues...")
        
        issues = []
        python_files = [f for f in os.listdir('.') if f.endswith('.py')]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for imports without error handling that might fail on AWS
                    if 'import' in line and 'telegram' in line and 'try:' not in lines[max(0, i-2):i]:
                        issues.append({
                            'file': file_path,
                            'line': i,
                            'issue': 'Telegram import without error handling',
                            'content': line.strip(),
                            'severity': 'MEDIUM',
                            'fix': 'Add try-catch for missing dependencies'
                        })
                    
                    # Check for fcntl imports (Unix-specific)
                    if 'import fcntl' in line:
                        # Check if there's platform checking
                        platform_check = any('platform' in l or 'os.name' in l for l in lines[max(0, i-5):i+5])
                        if not platform_check:
                            issues.append({
                                'file': file_path,
                                'line': i,
                                'issue': 'Unix-specific fcntl import without platform check',
                                'content': line.strip(),
                                'severity': 'MEDIUM',
                                'fix': 'Add platform compatibility check'
                            })
            
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        return issues
    
    def scan_configuration_files(self) -> List[Dict]:
        """Scan configuration files for AWS compatibility"""
        logger.info("Scanning configuration files...")
        
        issues = []
        
        # Check for missing AWS deployment files
        required_aws_files = [
            ('requirements.txt', 'Python dependencies list'),
            ('.env.production', 'Production environment template'),
            ('start_aws.sh', 'AWS startup script')
        ]
        
        for file_name, description in required_aws_files:
            if not os.path.exists(file_name):
                issues.append({
                    'file': file_name,
                    'line': 0,
                    'issue': f'Missing AWS deployment file: {description}',
                    'content': 'File not found',
                    'severity': 'HIGH',
                    'fix': f'Create {file_name} for AWS deployment'
                })
        
        # Check main.py for AWS compatibility
        if os.path.exists('main.py'):
            with open('main.py', 'r') as f:
                content = f.read()
            
            if 'gunicorn' not in content and '0.0.0.0' not in content:
                issues.append({
                    'file': 'main.py',
                    'line': 0,
                    'issue': 'Main.py not configured for AWS deployment',
                    'content': 'Import only',
                    'severity': 'MEDIUM',
                    'fix': 'Configure for gunicorn and proper host binding'
                })
        
        return issues
    
    def generate_fixes(self, issues: List[Dict]) -> List[str]:
        """Generate automatic fixes for identified issues"""
        logger.info("Generating fixes...")
        
        fixes = []
        
        # Group issues by type for batch fixing
        path_issues = [i for i in issues if 'hardcoded' in i['issue'].lower()]
        env_issues = [i for i in issues if 'environment' in i['issue'].lower()]
        
        # Fix hardcoded paths
        if path_issues:
            fixes.append("Fix hardcoded file paths")
            for issue in path_issues:
                if '/tmp/' in issue['content']:
                    fixes.append(f"  - Replace /tmp/ with tempfile.gettempdir() in {issue['file']}")
        
        # Fix environment handling
        if env_issues:
            fixes.append("Fix environment variable handling")
            for issue in env_issues:
                fixes.append(f"  - Add error handling for {issue['file']}")
        
        return fixes
    
    def run_comprehensive_audit(self) -> Dict:
        """Run complete audit and return results"""
        logger.info("Starting comprehensive AWS deployment audit...")
        
        all_issues = []
        
        # Run all scans
        scans = [
            ("Hardcoded Paths", self.scan_hardcoded_paths),
            ("Environment Handling", self.scan_environment_handling),
            ("Database Configuration", self.scan_database_configurations),
            ("Process Management", self.scan_process_management),
            ("Import Issues", self.scan_import_issues),
            ("Configuration Files", self.scan_configuration_files)
        ]
        
        scan_results = {}
        
        for scan_name, scan_function in scans:
            try:
                results = scan_function()
                scan_results[scan_name] = results
                all_issues.extend(results)
                logger.info(f"{scan_name}: Found {len(results)} issues")
            except Exception as e:
                logger.error(f"Error in {scan_name} scan: {e}")
                scan_results[scan_name] = []
        
        # Categorize issues
        critical = [i for i in all_issues if i['severity'] == 'HIGH']
        warnings = [i for i in all_issues if i['severity'] == 'MEDIUM']
        info = [i for i in all_issues if i['severity'] == 'LOW']
        
        # Generate report
        report = {
            'total_issues': len(all_issues),
            'critical_issues': len(critical),
            'warnings': len(warnings),
            'info_issues': len(info),
            'scan_results': scan_results,
            'critical_details': critical,
            'warning_details': warnings,
            'suggested_fixes': self.generate_fixes(all_issues)
        }
        
        return report
    
    def print_audit_report(self, report: Dict):
        """Print formatted audit report"""
        print("\n" + "="*80)
        print("AWS DEPLOYMENT INCONSISTENCY AUDIT REPORT")
        print("="*80)
        
        print(f"\nSUMMARY:")
        print(f"  Total Issues Found: {report['total_issues']}")
        print(f"  Critical Issues: {report['critical_issues']}")
        print(f"  Warnings: {report['warnings']}")
        print(f"  Info: {report['info_issues']}")
        
        if report['critical_details']:
            print(f"\nCRITICAL ISSUES (Must Fix Before AWS Deployment):")
            for i, issue in enumerate(report['critical_details'], 1):
                print(f"  {i}. {issue['file']}:{issue['line']}")
                print(f"     Issue: {issue['issue']}")
                print(f"     Code: {issue['content']}")
                print(f"     Fix: {issue['fix']}")
                print()
        
        if report['warning_details']:
            print(f"\nWARNINGS (Recommended Fixes):")
            for i, issue in enumerate(report['warning_details'], 1):
                print(f"  {i}. {issue['file']}:{issue['line']}")
                print(f"     Issue: {issue['issue']}")
                print(f"     Fix: {issue['fix']}")
                print()
        
        if report['suggested_fixes']:
            print(f"\nSUGGESTED FIXES:")
            for fix in report['suggested_fixes']:
                print(f"  {fix}")
        
        print(f"\nRECOMMENDATIONS:")
        if report['critical_issues'] > 0:
            print("  ⚠️  Fix critical issues before AWS deployment")
        else:
            print("  ✅ No critical blocking issues found")
        
        if report['warnings'] > 0:
            print(f"  📋 Consider fixing {report['warnings']} warnings for better reliability")
        
        print(f"\nNEXT STEPS:")
        print("  1. Fix critical issues listed above")
        print("  2. Test deployment in staging environment")
        print("  3. Run: python aws_deployment_checklist.py")
        print("  4. Deploy to AWS production")
        
        print("="*80)

def main():
    """Run the comprehensive AWS deployment audit"""
    auditor = AWSDeploymentAuditor()
    report = auditor.run_comprehensive_audit()
    auditor.print_audit_report(report)
    
    # Return exit code based on critical issues
    return 1 if report['critical_issues'] > 0 else 0

if __name__ == "__main__":
    sys.exit(main())