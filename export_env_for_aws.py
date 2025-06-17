#!/usr/bin/env python3
"""
Export Environment Variables for AWS Deployment
===============================================
This script extracts all environment variables from your current setup
and creates AWS-ready files for deployment.
"""

import os
from datetime import datetime
from dotenv import load_dotenv

def export_current_env():
    """Export current environment variables to AWS format"""
    print("Extracting environment variables for AWS deployment...")
    
    # Load current .env file with override
    load_dotenv(override=True)
    
    # Define required variables with their current values
    env_vars = {
        # Core required variables
        'DATABASE_URL': os.environ.get('DATABASE_URL', ''),
        'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
        'ADMIN_USER_ID': os.environ.get('ADMIN_USER_ID', ''),
        'ADMIN_CHAT_ID': os.environ.get('ADMIN_CHAT_ID', ''),
        'SESSION_SECRET': os.environ.get('SESSION_SECRET', ''),
        
        # Trading configuration
        'MIN_DEPOSIT': os.environ.get('MIN_DEPOSIT', '0.1'),
        'SOLANA_RPC_URL': os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
        'GLOBAL_DEPOSIT_WALLET': os.environ.get('GLOBAL_DEPOSIT_WALLET', ''),
        
        # Deployment settings
        'BOT_ENVIRONMENT': 'aws',
        'NODE_ENV': 'production',
        'FLASK_ENV': 'production',
        
        # Optional variables
        'SUPPORT_USERNAME': os.environ.get('SUPPORT_USERNAME', 'thrivesupport'),
        'DAILY_UPDATE_HOUR': os.environ.get('DAILY_UPDATE_HOUR', '9'),
        'AWS_REGION': os.environ.get('AWS_REGION', 'us-east-1'),
    }
    
    # Create .env.aws file
    aws_env_content = "# AWS Environment Variables\n"
    aws_env_content += f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    aws_env_content += "# === CORE REQUIRED VARIABLES ===\n"
    for var in ['DATABASE_URL', 'TELEGRAM_BOT_TOKEN', 'ADMIN_USER_ID', 'ADMIN_CHAT_ID', 'SESSION_SECRET']:
        value = env_vars[var]
        if value:
            aws_env_content += f"{var}={value}\n"
        else:
            aws_env_content += f"# {var}=YOUR_VALUE_HERE\n"
    
    aws_env_content += "\n# === TRADING CONFIGURATION ===\n"
    for var in ['MIN_DEPOSIT', 'SOLANA_RPC_URL', 'GLOBAL_DEPOSIT_WALLET']:
        value = env_vars[var]
        aws_env_content += f"{var}={value}\n"
    
    aws_env_content += "\n# === DEPLOYMENT SETTINGS ===\n"
    for var in ['BOT_ENVIRONMENT', 'NODE_ENV', 'FLASK_ENV']:
        value = env_vars[var]
        aws_env_content += f"{var}={value}\n"
    
    aws_env_content += "\n# === OPTIONAL VARIABLES ===\n"
    for var in ['SUPPORT_USERNAME', 'DAILY_UPDATE_HOUR', 'AWS_REGION']:
        value = env_vars[var]
        aws_env_content += f"{var}={value}\n"
    
    # Write to file
    with open('.env.aws', 'w') as f:
        f.write(aws_env_content)
    
    print("✓ Created .env.aws file for AWS deployment")
    
    # Create shell export format
    shell_export = "#!/bin/bash\n"
    shell_export += "# AWS Environment Variables Export Script\n"
    shell_export += f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for var, value in env_vars.items():
        if value:
            # Escape special characters in shell
            escaped_value = value.replace('"', '\\"').replace('$', '\\$')
            shell_export += f'export {var}="{escaped_value}"\n'
        else:
            shell_export += f'# export {var}="YOUR_VALUE_HERE"\n'
    
    with open('export_env_aws.sh', 'w') as f:
        f.write(shell_export)
    
    # Make executable
    os.chmod('export_env_aws.sh', 0o755)
    
    print("✓ Created export_env_aws.sh shell script")
    
    # Create deployment summary
    summary = f"""
AWS Deployment Environment Summary
=================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Files Created:
- .env.aws (Environment file for AWS)
- export_env_aws.sh (Shell export script)

Required Variables Status:
"""
    
    missing_vars = []
    for var in ['DATABASE_URL', 'TELEGRAM_BOT_TOKEN', 'ADMIN_USER_ID', 'ADMIN_CHAT_ID']:
        value = env_vars[var]
        if value:
            # Mask sensitive values
            if 'TOKEN' in var or 'SECRET' in var or 'URL' in var:
                masked = value[:10] + "..." + value[-5:] if len(value) > 15 else "***"
                summary += f"✓ {var}: {masked}\n"
            else:
                summary += f"✓ {var}: {value}\n"
        else:
            summary += f"✗ {var}: MISSING\n"
            missing_vars.append(var)
    
    if missing_vars:
        summary += f"\nWARNING: Missing variables: {', '.join(missing_vars)}\n"
        summary += "Please update .env.aws with the missing values before deployment.\n"
    else:
        summary += "\n✅ All required variables are present.\n"
    
    summary += """
AWS Deployment Steps:
1. Copy .env.aws to your AWS server as .env
2. Set permissions: chmod 600 .env
3. Start bot: python3 aws_start_bot.py

Alternative using shell script:
1. Copy export_env_aws.sh to your AWS server
2. Run: source export_env_aws.sh
3. Start bot: python3 aws_start_bot.py
"""
    
    with open('AWS_ENV_DEPLOYMENT_SUMMARY.txt', 'w') as f:
        f.write(summary)
    
    print("✓ Created AWS_ENV_DEPLOYMENT_SUMMARY.txt")
    print("\n" + summary)
    
    return True

if __name__ == '__main__':
    export_current_env()