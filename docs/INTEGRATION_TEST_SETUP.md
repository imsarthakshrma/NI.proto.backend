# Integration Test Setup Guide

This guide helps you configure and run the Native IQ integration tests with real services (email, calendar, Google Drive).

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.integration.example .env.integration
   ```

2. **Edit `.env.integration` with your credentials**

3. **Load environment and run tests:**
   ```bash
   # Load environment variables
   source .env.integration  # Linux/Mac
   # OR for Windows:
   # set /p < .env.integration

   # Run integration tests
   pytest -q -m integration tests/integration/test_native_iq_integration.py
   ```

## Environment Variables

### Core Test Configuration
```bash
# Disable dry-run mode to use real services
NI_IT_DRY_RUN=false

# Your email address for receiving test emails
NI_IT_TEST_RECIPIENT=your.email@gmail.com

# Google Drive file name to test attachments (optional)
NI_IT_DRIVE_FILE_NAME=test_doc

# Local file paths for email attachments (optional, comma-separated)
NI_IT_ATTACH_PATHS=/path/to/file1.pdf,/path/to/file2.txt

# Meeting start time for calendar tests (optional, defaults to future date)
NI_IT_MEETING_START=2025-12-31T15:00:00+05:30
```

### Email Service (SMTP)
```bash
# Gmail example:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your.email@gmail.com
SMTP_PASSWORD=your_app_password  # Use App Password, not regular password
SMTP_SENDER_NAME=Native IQ Bot

# Outlook example:
# SMTP_SERVER=smtp-mail.outlook.com
# SMTP_PORT=587
# SMTP_EMAIL=your.email@outlook.com
# SMTP_PASSWORD=your_app_password
```

### Google Calendar API
```bash
# Path to your Google OAuth credentials file
GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=calendar_token.json

# Calendar ID (optional, defaults to primary)
GOOGLE_CALENDAR_ID=primary
```

### Google Drive API
```bash
# Path to your Google OAuth credentials file  
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_TOKEN_PATH=drive_token.json
```

## Setting Up Credentials

### 1. Gmail SMTP (for Email Tests)

1. **Enable 2-Factor Authentication** on your Google account
2. **Generate App Password:**
   - Go to Google Account settings → Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
   - Use this password in `SMTP_PASSWORD`

### 2. Google Calendar API

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing

2. **Enable Calendar API:**
   - Go to APIs & Services → Library
   - Search "Google Calendar API" → Enable

3. **Create OAuth Credentials:**
   - Go to APIs & Services → Credentials
   - Create Credentials → OAuth 2.0 Client IDs
   - Application type: Desktop application
   - Download JSON file as `credentials.json`

4. **First-time OAuth Flow:**
   ```bash
   # Run any calendar test to trigger OAuth flow
   pytest -k "schedule_meeting" tests/integration/test_native_iq_integration.py
   # Follow browser prompts to authorize
   # Token will be saved to calendar_token.json
   ```

### 3. Google Drive API

1. **Enable Drive API** (same project as Calendar):
   - Go to APIs & Services → Library  
   - Search "Google Drive API" → Enable

2. **Use same OAuth credentials** or create Drive-specific ones
3. **Create test file in Drive:**
   - Upload a file named "test_doc" to your Google Drive
   - Or set `NI_IT_DRIVE_FILE_NAME` to an existing file name

## Test Scenarios

### Email Only
```bash
export NI_IT_DRY_RUN=false
export NI_IT_TEST_RECIPIENT=you@gmail.com
# Set SMTP_* variables

pytest -k "email" tests/integration/test_native_iq_integration.py
```

### Calendar Only  
```bash
export NI_IT_DRY_RUN=false
export NI_IT_TEST_RECIPIENT=you@gmail.com
# Set Google Calendar credentials

pytest -k "schedule_meeting" tests/integration/test_native_iq_integration.py
```

### Drive + Email (Attachment Test)
```bash
export NI_IT_DRY_RUN=false
export NI_IT_TEST_RECIPIENT=you@gmail.com
export NI_IT_DRIVE_FILE_NAME=test_doc
# Set SMTP_* and Google Drive credentials

pytest -k "drive_attachment" tests/integration/test_native_iq_integration.py
```

### Full Integration (All Services)
```bash
# Set all environment variables above
pytest -m integration tests/integration/test_native_iq_integration.py
```

## Troubleshooting

### Common Issues

1. **"Could not resolve email tool callable"**
   - Check that `src/domains/tools/email_tool.py` exists
   - Verify SMTP credentials are set

2. **"Invalid scope" for Google APIs**
   - Delete existing token files (`*_token.json`)
   - Re-run tests to trigger fresh OAuth flow
   - Ensure correct scopes in your tool implementation

3. **"Drive tool not available"**
   - Check `NI_IT_DRIVE_FILE_NAME` is set
   - Verify file exists in your Google Drive
   - Ensure Drive API credentials are configured

4. **SMTP Authentication Failed**
   - Use App Password instead of regular password
   - Check 2FA is enabled on Google account
   - Verify SMTP server and port settings

### Debug Mode  
```bash
# Enable verbose logging
export PYTHONPATH=src:$PYTHONPATH
python -m pytest -v -s -m integration tests/integration/test_native_iq_integration.py
```

## Security Notes

- **Never commit credentials** to version control
- Use `.env.integration` (add to `.gitignore`)
- Use App Passwords instead of main account passwords
- Limit OAuth scopes to minimum required
- Consider using separate test Google account

## Expected Results

When tests pass with real services:

- ✅ **Email test**: Sends actual email to `NI_IT_TEST_RECIPIENT`
- ✅ **Calendar test**: Creates real meeting in your Google Calendar  
- ✅ **Drive test**: Downloads file and sends as email attachment
- ✅ **Chained test**: Schedules meeting + sends invite email with meeting link

Check your email inbox and Google Calendar to verify real actions occurred!
