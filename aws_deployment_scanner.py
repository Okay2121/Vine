#!/usr/bin/env python3
"""
AWS Deployment Inconsistency Scanner
===================================
Scans the codebase for potential issues that could occur during or after AWS deployment.
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class AWSDeploymentScanner:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.fixes_needed = []
        
    def scan_hardcoded_paths(self) -> List[Dict]:
        """Scan for hardcoded file paths that won't work on AWS"""
        logger.info("Scanning for hardcoded paths...")
        
        issues = []
        python_files = list(Path('.').glob('*.py'))
        
        problematic_patterns = [
            (r'/home/runner', 'Replit-specific path'),
            (r'/opt/virtualenvs', 'Replit virtualenv path'),
            (r'C:\\', 'Windows-specific path'),
            (r'/Users/', 'macOS-specific path'),
            (r'/tmp/[^/\s]+\.(png|jpg|jpeg|gif)', 'Hardcoded temp file paths'),
            (r'\.cache/', 'Hardcoded cache paths'),
        ]
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    for pattern, desc in problematic_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append({
                                'file': str(file_path),
                                'line': i,
                                'issue': f'Hardcoded path: {desc}',
                                'content': line.strip(),
                                'severity': 'HIGH' if 'runner' in line else 'MEDIUM'
                            })
                            
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        return issues
    
    def scan_environment_handling(self) -> List[Dict]:
        """Scan for environment variable handling issues"""
        logger.info("Scanning environment variable handling...")
        
        issues = []
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for direct os.environ access without fallbacks
                    if re.search(r'os\.environ\[[\'"][^\'"][\'\"]\]', line) and 'get(' not in line:
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Direct environment variable access without fallback',
                            'content': line.strip(),
                            'severity': 'MEDIUM'
                        })
                    
                    # Check for missing dotenv loading in production files
                    if 'load_dotenv' in line and 'import' in line:
                        # Check if there's a conditional around it
                        context = '\n'.join(lines[max(0, i-3):i+2])
                        if 'if' not in context and 'try:' not in context:
                            issues.append({
                                'file': str(file_path),
                                'line': i,
                                'issue': 'Unconditional dotenv loading - may cause issues',
                                'content': line.strip(),
                                'severity': 'LOW'
                            })
                            
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        return issues
    
    def scan_database_configurations(self) -> List[Dict]:
        """Scan for database configuration issues"""
        logger.info("Scanning database configurations...")
        
        issues = []
        
        # Check app.py for database configuration
        if Path('app.py').exists():
            content = Path('app.py').read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check for hardcoded database URLs
                if 'postgresql://' in line and 'localhost' in line:
                    issues.append({
                        'file': 'app.py',
                        'line': i,
                        'issue': 'Hardcoded localhost database URL',
                        'content': line.strip(),
                        'severity': 'HIGH'
                    })
                
                # Check for missing connection pooling
                if 'SQLALCHEMY_DATABASE_URI' in line:
                    context = '\n'.join(lines[max(0, i-5):i+5])
                    if 'pool_' not in context:
                        issues.append({
                            'file': 'app.py',
                            'line': i,
                            'issue': 'Missing database connection pool configuration',
                            'content': line.strip(),
                            'severity': 'MEDIUM'
                        })
                        
        return issues
    
    def scan_file_permissions(self) -> List[Dict]:
        """Scan for file permission issues"""
        logger.info("Scanning file permission issues...")
        
        issues = []
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for file operations without permission handling
                    if re.search(r'open\([^)]*[\'"]w[\'"]', line):
                        # Check if there's error handling around it
                        context = '\n'.join(lines[max(0, i-3):i+3])
                        if 'try:' not in context and 'except' not in context:
                            issues.append({
                                'file': str(file_path),
                                'line': i,
                                'issue': 'File write operation without error handling',
                                'content': line.strip(),
                                'severity': 'MEDIUM'
                            })
                    
                    # Check for chmod operations
                    if 'chmod' in line:
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'File permission change - may fail on some AWS setups',
                            'content': line.strip(),
                            'severity': 'LOW'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        return issues
    
    def scan_network_bindings(self) -> List[Dict]:
        """Scan for network binding issues"""
        logger.info("Scanning network bindings...")
        
        issues = []
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for localhost bindings (exclude comments and scanner code)
                    if re.search(r'localhost|127\.0\.0\.1', line) and 'bind' in line.lower() and not line.strip().startswith('#') and 'scanner' not in str(file_path).lower():
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Localhost binding - should use 0.0.0.0 for AWS',
                            'content': line.strip(),
                            'severity': 'HIGH'
                        })
                    
                    # Check for hardcoded ports
                    if re.search(r'port\s*=\s*\d{4,5}', line) and '5000' not in line:
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Hardcoded port - should use environment variable',
                            'content': line.strip(),
                            'severity': 'MEDIUM'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        return issues
    
    def scan_process_management(self) -> List[Dict]:
        """Scan for process management issues"""
        logger.info("Scanning process management...")
        
        issues = []
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for subprocess calls without proper handling
                    if 'subprocess.' in line and 'Popen' in line:
                        context = '\n'.join(lines[max(0, i-2):i+3])
                        if 'try:' not in context:
                            issues.append({
                                'file': str(file_path),
                                'line': i,
                                'issue': 'Subprocess call without error handling',
                                'content': line.strip(),
                                'severity': 'MEDIUM'
                            })
                    
                    # Check for signal handling
                    if 'signal.' in line and 'SIGTERM' not in line:
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Signal handling - ensure SIGTERM is handled for AWS',
                            'content': line.strip(),
                            'severity': 'LOW'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        return issues
    
    def scan_import_issues(self) -> List[Dict]:
        """Scan for import-related issues"""
        logger.info("Scanning import issues...")
        
        issues = []
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for relative imports that might break
                    if re.search(r'from \. import|from \.\w+ import', line):
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Relative import - may break in AWS deployment',
                            'content': line.strip(),
                            'severity': 'MEDIUM'
                        })
                    
                    # Check for imports without error handling
                    if line.strip().startswith('import ') and 'telegram' in line:
                        context = '\n'.join(lines[max(0, i-2):i+2])
                        if 'try:' not in context:
                            issues.append({
                                'file': str(file_path),
                                'line': i,
                                'issue': 'Critical import without error handling',
                                'content': line.strip(),
                                'severity': 'MEDIUM'
                            })
                            
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        return issues
    
    def scan_logging_configuration(self) -> List[Dict]:
        """Scan for logging configuration issues"""
        logger.info("Scanning logging configuration...")
        
        issues = []
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for print statements in production code
                    if line.strip().startswith('print(') and 'debug' not in file_path.name:
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Print statement in production code - use logging',
                            'content': line.strip(),
                            'severity': 'LOW'
                        })
                    
                    # Check for hardcoded log levels
                    if 'level=logging.DEBUG' in line and 'production' not in line:
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Hardcoded DEBUG logging - should be configurable',
                            'content': line.strip(),
                            'severity': 'LOW'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        return issues
    
    def run_comprehensive_scan(self) -> Dict:
        """Run all scans and return comprehensive report"""
        logger.info("Starting comprehensive AWS deployment scan...")
        
        all_issues = []
        
        scanners = [
            ('Hardcoded Paths', self.scan_hardcoded_paths),
            ('Environment Handling', self.scan_environment_handling),
            ('Database Configuration', self.scan_database_configurations),
            ('File Permissions', self.scan_file_permissions),
            ('Network Bindings', self.scan_network_bindings),
            ('Process Management', self.scan_process_management),
            ('Import Issues', self.scan_import_issues),
            ('Logging Configuration', self.scan_logging_configuration),
        ]
        
        for scanner_name, scanner_func in scanners:
            try:
                issues = scanner_func()
                for issue in issues:
                    issue['category'] = scanner_name
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Scanner {scanner_name} failed: {e}")
        
        # Categorize by severity
        high_severity = [i for i in all_issues if i.get('severity') == 'HIGH']
        medium_severity = [i for i in all_issues if i.get('severity') == 'MEDIUM']
        low_severity = [i for i in all_issues if i.get('severity') == 'LOW']
        
        return {
            'total_issues': len(all_issues),
            'high_severity': high_severity,
            'medium_severity': medium_severity,
            'low_severity': low_severity,
            'all_issues': all_issues
        }
    
    def print_report(self, report: Dict):
        """Print formatted scan report"""
        print("\n" + "=" * 80)
        print("AWS DEPLOYMENT INCONSISTENCY SCAN REPORT")
        print("=" * 80)
        
        print(f"Total Issues Found: {report['total_issues']}")
        print(f"High Severity: {len(report['high_severity'])}")
        print(f"Medium Severity: {len(report['medium_severity'])}")
        print(f"Low Severity: {len(report['low_severity'])}")
        
        if report['high_severity']:
            print("\n🚨 HIGH SEVERITY ISSUES (Must Fix Before AWS Deployment):")
            for i, issue in enumerate(report['high_severity'], 1):
                print(f"  {i}. {issue['file']}:{issue['line']} - {issue['issue']}")
                print(f"     Code: {issue['content']}")
        
        if report['medium_severity']:
            print("\n⚠️  MEDIUM SEVERITY ISSUES (Should Fix):")
            for i, issue in enumerate(report['medium_severity'], 1):
                print(f"  {i}. {issue['file']}:{issue['line']} - {issue['issue']}")
                
        if report['low_severity']:
            print(f"\n💡 LOW SEVERITY ISSUES: {len(report['low_severity'])} (Consider fixing)")
        
        if report['total_issues'] == 0:
            print("\n✅ No AWS deployment issues found!")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    scanner = AWSDeploymentScanner()
    report = scanner.run_comprehensive_scan()
    scanner.print_report(report)
    
    # Exit with error code if high severity issues found
    sys.exit(1 if len(report['high_severity']) > 0 else 0)