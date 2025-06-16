# Environment-Aware Startup System Summary

## Overview

Your Telegram bot now supports two distinct startup modes with proper environment detection and isolation:

### 1. Replit Auto-Start Mode
- **Trigger**: When someone remixes your Replit project
- **Entry Point**: `main.py` (Flask web server)
- **Environment Variables**: Replit's built-in secrets manager
- **Behavior**: Bot automatically starts when the web interface is accessed

### 2. AWS Manual Start Mode  
- **Trigger**: Direct execution via `python bot_v20_runner.py`
- **Entry Point**: `bot_v20_runner.py` 
- **Environment Variables**: `.env` file loaded via python-dotenv
- **Behavior**: Bot starts immediately with comprehensive logging

## File Structure

```
project/
├── main.py                    # Flask app + Replit auto-start logic
├── bot_v20_runner.py         # Main bot code + AWS manual start entry point
├── environment_detector.py   # Environment detection system
├── .env.template             # Template for AWS deployment
├── .env                      # Your actual environment variables (AWS only)
├── AWS_DEPLOYMENT_GUIDE.md   # Complete deployment instructions
└── requirements.txt          # Python dependencies
```

## Environment Detection Logic

The system automatically detects the environment using:

1. **Replit Detection**:
   - Checks for `REPL_ID`, `REPL_SLUG`, `REPLIT_DB_URL` environment variables
   - Looks for Replit-specific file paths like `/home/runner`

2. **AWS Detection**:
   - Checks for `.env` file presence
   - Looks for AWS environment variables (`AWS_REGION`, etc.)
   - Detects production indicators (`/var/log`, `/etc/systemd`)

3. **Execution Mode Detection**:
   - Direct execution: `python bot_v20_runner.py` 
   - Import mode: When imported by `main.py`

## Startup Behavior Matrix

| Environment | Execution Method | .env Loading | Auto-Start | Entry Point |
|-------------|------------------|--------------|------------|-------------|
| Replit | Web access | ❌ No | ✅ Yes | main.py |
| Replit | Direct execution | ❌ No | ❌ No | bot_v20_runner.py |
| AWS | Direct execution | ✅ Yes | ❌ No | bot_v20_runner.py |
| Local | Direct execution | ✅ Yes | ❌ No | bot_v20_runner.py |

## Duplicate Prevention

The system prevents multiple bot instances through:

1. **Global running flag** (`_bot_running`)
2. **Instance manager locks** (duplicate_instance_prevention.py)
3. **Execution mode detection** (skips if already running via import)

## Logging Configuration

Each environment gets appropriate logging:

- **Replit**: `[REPLIT]` prefix, INFO level
- **AWS**: `[AWS]` prefix, INFO level  
- **Local**: `[LOCAL]` prefix, DEBUG level

## Environment Variables

### Replit (Built-in Secrets)
```
TELEGRAM_BOT_TOKEN=your_token
DATABASE_URL=your_database_url
SESSION_SECRET=your_session_secret
```

### AWS (.env file)
```env
TELEGRAM_BOT_TOKEN=your_token_here
DATABASE_URL=postgresql://user:pass@host:port/db
SESSION_SECRET=your_generated_secret
FLASK_ENV=production
ENVIRONMENT=production
LOG_LEVEL=INFO
AWS_REGION=us-east-1
```

## Usage Instructions

### For Replit Users
1. Remix the project
2. Set environment variables in Replit's Secrets tab
3. The bot will auto-start when you access the web interface
4. No manual commands needed

### For AWS Users
1. Upload your code to EC2 instance
2. Copy `.env.template` to `.env`
3. Fill in your actual environment variables
4. Run: `python bot_v20_runner.py`
5. The bot starts immediately with full monitoring

## Key Features

✅ **Environment Auto-Detection**: Automatically detects Replit vs AWS vs Local
✅ **Conditional .env Loading**: Only loads .env when needed (AWS/Local)
✅ **Duplicate Instance Prevention**: Prevents multiple bot instances
✅ **Comprehensive Logging**: Environment-specific log formatting
✅ **Database Health Checks**: Verifies connectivity before starting
✅ **Graceful Error Handling**: Clear error messages for missing configs
✅ **Production Ready**: Includes monitoring, maintenance, and cleanup systems

## Troubleshooting

### Bot Not Starting on Replit
- Check if environment variables are set in Replit Secrets
- Verify the web interface is being accessed (triggers auto-start)
- Check console logs for errors

### Bot Not Starting on AWS
- Verify `.env` file exists and contains required variables
- Check file permissions: `chmod 600 .env`
- Test environment detection: `python environment_detector.py`
- Verify database connectivity

### Duplicate Bot Instances
- Check logs for "already running" messages
- Restart with `python bot_v20_runner.py` (kills existing instances)
- Verify only one startup method is being used

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Replit Mode   │    │    AWS Mode     │
│                 │    │                 │
│ Web Interface   │    │ SSH Terminal    │
│       ↓         │    │       ↓         │
│    main.py      │    │ bot_v20_runner  │
│       ↓         │    │       ↓         │
│ Auto-Start Bot  │    │ Manual Start    │
│       ↓         │    │       ↓         │
│ Import Runner   │    │ Direct Execute  │
└─────────────────┘    └─────────────────┘
        ↓                       ↓
        └───────────────────────┘
                    ↓
        ┌─────────────────────┐
        │  Environment        │
        │  Detection System   │
        │                     │
        │ • Load .env if AWS  │
        │ • Set logging mode  │
        │ • Prevent duplicates│
        │ • Health checks     │
        └─────────────────────┘
                    ↓
        ┌─────────────────────┐
        │    Bot Polling      │
        │                     │
        │ • Telegram API      │
        │ • Database Monitor  │
        │ • Maintenance Tasks │
        │ • Admin Functions   │
        └─────────────────────┘
```

Your bot now supports seamless deployment across both platforms with zero configuration conflicts.