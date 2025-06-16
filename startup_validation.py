#!/usr/bin/env python3
"""
Startup System Validation Script
================================
Validates the environment-aware startup system for inconsistencies and issues.
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class StartupValidator:
    def __init__(self):
        self.issues_found = []
        self.fixes_applied = []
        
    def validate_environment_detection(self):
        """Validate environment detection works correctly"""
        logger.info("Validating environment detection...")
        
        try:
            from environment_detector import get_environment_info, is_replit_environment, is_aws_environment
            
            env_info = get_environment_info()
            logger.info(f"Environment type detected: {env_info['environment_type']}")
            logger.info(f"Auto-start enabled: {env_info['auto_start_enabled']}")
            logger.info(f"Direct execution: {env_info['is_direct_execution']}")
            
            # Validate required fields are present
            required_fields = ['environment_type', 'is_replit', 'is_aws', 'auto_start_enabled', 'env_file_exists']
            for field in required_fields:
                if field not in env_info:
                    self.issues_found.append(f"Missing required field in environment info: {field}")
                    
            return True
            
        except Exception as e:
            self.issues_found.append(f"Environment detection failed: {e}")
            return False
    
    def validate_dotenv_loading(self):
        """Validate .env loading works correctly"""
        logger.info("Validating .env loading...")
        
        try:
            # Check if .env.template exists
            if not Path('.env.template').exists():
                self.issues_found.append(".env.template file missing")
                
            # Test dotenv import
            try:
                from dotenv import load_dotenv
                logger.info("python-dotenv is available")
            except ImportError:
                self.issues_found.append("python-dotenv not installed")
                
            return True
            
        except Exception as e:
            self.issues_found.append(f"Dotenv validation failed: {e}")
            return False
    
    def validate_bot_imports(self):
        """Validate bot_v20_runner imports work correctly"""
        logger.info("Validating bot imports...")
        
        try:
            # Test importing without running
            spec = importlib.util.spec_from_file_location("bot_v20_runner", "bot_v20_runner.py")
            if spec is None:
                self.issues_found.append("Cannot load bot_v20_runner.py")
                return False
                
            # Check for critical imports in bot file
            with open('bot_v20_runner.py', 'r') as f:
                content = f.read()
                
            required_imports = [
                'from environment_detector import',
                'from config import BOT_TOKEN',
                'from app import app, db',
                'from models import'
            ]
            
            for imp in required_imports:
                if imp not in content:
                    self.issues_found.append(f"Missing required import: {imp}")
                    
            return True
            
        except Exception as e:
            self.issues_found.append(f"Bot import validation failed: {e}")
            return False
    
    def validate_main_py_integration(self):
        """Validate main.py integration with bot"""
        logger.info("Validating main.py integration...")
        
        try:
            with open('main.py', 'r') as f:
                main_content = f.read()
                
            # Check for critical integrations
            required_elements = [
                'from environment_detector import',
                'from bot_v20_runner import run_polling',
                'should_auto_start()',
                'is_replit_environment()'
            ]
            
            for element in required_elements:
                if element not in main_content:
                    self.issues_found.append(f"Missing in main.py: {element}")
                    
            return True
            
        except Exception as e:
            self.issues_found.append(f"Main.py validation failed: {e}")
            return False
    
    def validate_duplicate_prevention(self):
        """Validate duplicate instance prevention"""
        logger.info("Validating duplicate prevention...")
        
        try:
            # Check for global bot running flag
            with open('bot_v20_runner.py', 'r') as f:
                bot_content = f.read()
                
            if '_bot_running = False' not in bot_content:
                self.issues_found.append("Missing global _bot_running flag")
                
            if 'duplicate_instance_prevention' not in bot_content:
                self.issues_found.append("Missing duplicate instance prevention import")
                
            return True
            
        except Exception as e:
            self.issues_found.append(f"Duplicate prevention validation failed: {e}")
            return False
    
    def validate_startup_entry_points(self):
        """Validate startup entry points are correct"""
        logger.info("Validating startup entry points...")
        
        try:
            with open('bot_v20_runner.py', 'r') as f:
                bot_content = f.read()
                
            # Check for proper main function
            if 'def main():' not in bot_content:
                self.issues_found.append("Missing main() function in bot_v20_runner.py")
                
            # Check for proper __name__ == '__main__' guard
            if "if __name__ == '__main__':" not in bot_content:
                self.issues_found.append("Missing __name__ == '__main__' guard")
                
            # Check that main() is called correctly
            lines = bot_content.split('\n')
            main_block_found = False
            for i, line in enumerate(lines):
                if "if __name__ == '__main__':" in line:
                    # Check next few lines for main() call
                    for j in range(i+1, min(i+5, len(lines))):
                        if 'main()' in lines[j]:
                            main_block_found = True
                            break
                    break
                    
            if not main_block_found:
                self.issues_found.append("main() not called in __name__ == '__main__' block")
                
            return True
            
        except Exception as e:
            self.issues_found.append(f"Entry point validation failed: {e}")
            return False
    
    def validate_environment_variables(self):
        """Validate environment variable handling"""
        logger.info("Validating environment variables...")
        
        try:
            # Check if critical environment variables are accessible
            critical_vars = ['TELEGRAM_BOT_TOKEN', 'DATABASE_URL', 'SESSION_SECRET']
            
            for var in critical_vars:
                if not os.environ.get(var):
                    logger.warning(f"Environment variable {var} not set (expected in production)")
                    
            return True
            
        except Exception as e:
            self.issues_found.append(f"Environment variable validation failed: {e}")
            return False
    
    def check_conflicting_startup_files(self):
        """Check for conflicting startup files that could cause issues"""
        logger.info("Checking for conflicting startup files...")
        
        conflicting_files = [
            'simple_bot_runner.py',
            'bot_runner.py', 
            'run_bot_persistent.py',
            'optimized_bot.py'
        ]
        
        for filename in conflicting_files:
            if Path(filename).exists():
                with open(filename, 'r') as f:
                    content = f.read()
                if 'DEPRECATED' not in content and 'disabled' not in content.lower():
                    self.issues_found.append(f"Active conflicting startup file: {filename}")
                    
        return True
    
    def run_validation(self):
        """Run all validation checks"""
        logger.info("Starting comprehensive startup system validation...")
        
        validations = [
            self.validate_environment_detection,
            self.validate_dotenv_loading,
            self.validate_bot_imports,
            self.validate_main_py_integration,
            self.validate_duplicate_prevention,
            self.validate_startup_entry_points,
            self.validate_environment_variables,
            self.check_conflicting_startup_files
        ]
        
        passed = 0
        for validation in validations:
            try:
                if validation():
                    passed += 1
            except Exception as e:
                self.issues_found.append(f"Validation {validation.__name__} crashed: {e}")
        
        # Generate report
        self.generate_report(passed, len(validations))
        
        return len(self.issues_found) == 0
    
    def generate_report(self, passed, total):
        """Generate validation report"""
        print("\n" + "=" * 60)
        print("STARTUP SYSTEM VALIDATION REPORT")
        print("=" * 60)
        print(f"Validations passed: {passed}/{total}")
        
        if self.issues_found:
            print(f"\nIssues found ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"  {i}. {issue}")
        else:
            print("\nNo issues found! Startup system is working correctly.")
            
        print("\n" + "=" * 60)
        print("ENVIRONMENT SUMMARY")
        print("=" * 60)
        
        try:
            from environment_detector import get_environment_info
            env_info = get_environment_info()
            
            print(f"Environment Type: {env_info['environment_type']}")
            print(f"Platform: {'Replit' if env_info['is_replit'] else 'AWS/Local'}")
            print(f"Auto-start: {'Enabled' if env_info['auto_start_enabled'] else 'Disabled'}")
            print(f".env file: {'Present' if env_info['env_file_exists'] else 'Not found'}")
            print(f"Startup method: {'Auto (web interface)' if env_info['auto_start_enabled'] else 'Manual (python bot_v20_runner.py)'}")
            
        except Exception as e:
            print(f"Could not generate environment summary: {e}")

if __name__ == "__main__":
    validator = StartupValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)