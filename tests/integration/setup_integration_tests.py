#!/usr/bin/env python3
"""
Quick setup script for Native IQ integration tests.
Helps configure environment variables and validate credentials.
"""

import os
import sys
from pathlib import Path

def check_file_exists(path: str, description: str) -> bool:
    """Check if a file exists and print status."""
    if os.path.exists(path):
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} (not found)")
        return False

def check_env_var(var: str, description: str, required: bool = True) -> bool:
    """Check if environment variable is set."""
    value = os.getenv(var)
    if value:
        # Hide sensitive values
        display_value = "***" if "password" in var.lower() or "token" in var.lower() else value
        print(f"✅ {description}: {display_value}")
        return True
    else:
        status = "❌" if required else "⚠️"
        print(f"{status} {description}: Not set")
        return not required

def main():
    print("🔧 Native IQ Integration Test Setup Checker")
    print("=" * 50)
    
    # Check test configuration
    print("\n📋 Test Configuration:")
    dry_run = os.getenv("NI_IT_DRY_RUN", "true").lower()
    if dry_run == "true":
        print("⚠️  DRY_RUN mode enabled - tests will simulate actions")
        print("   Set NI_IT_DRY_RUN=false for real service tests")
    else:
        print("🚀 DRY_RUN disabled - tests will use real services")
    
    check_env_var("NI_IT_TEST_RECIPIENT", "Test recipient email")
    check_env_var("NI_IT_DRIVE_FILE_NAME", "Drive file name", required=False)
    check_env_var("NI_IT_ATTACH_PATHS", "Local attachment paths", required=False)
    
    # Check email credentials
    print("\n📧 Email Service (SMTP):")
    email_ok = all([
        check_env_var("SMTP_SERVER", "SMTP server"),
        check_env_var("SMTP_PORT", "SMTP port"),
        check_env_var("SMTP_EMAIL", "SMTP email"),
        check_env_var("SMTP_PASSWORD", "SMTP password"),
    ])
    
    # Check Google Calendar credentials
    print("\n📅 Google Calendar API:")
    cal_creds = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "credentials.json")
    cal_token = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "calendar_token.json")
    
    cal_creds_ok = check_file_exists(cal_creds, "Calendar credentials file")
    cal_token_ok = check_file_exists(cal_token, "Calendar token file")
    
    if cal_creds_ok and not cal_token_ok:
        print("ℹ️  Calendar token will be created on first OAuth flow")
    
    # Check Google Drive credentials  
    print("\n📁 Google Drive API:")
    drive_creds = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "credentials.json")
    drive_token = os.getenv("GOOGLE_DRIVE_TOKEN_PATH", "drive_token.json")
    
    drive_creds_ok = check_file_exists(drive_creds, "Drive credentials file")
    drive_token_ok = check_file_exists(drive_token, "Drive token file")
    
    if drive_creds_ok and not drive_token_ok:
        print("ℹ️  Drive token will be created on first OAuth flow")
    
    # Summary and recommendations
    print("\n📊 Summary:")
    
    if dry_run == "true":
        print("✅ Ready for DRY RUN tests")
        print("   Command: pytest -q -m integration tests/integration/test_native_iq_integration.py")
    else:
        issues = []
        if not email_ok:
            issues.append("Email SMTP credentials")
        if not cal_creds_ok:
            issues.append("Google Calendar credentials")
        if not drive_creds_ok and os.getenv("NI_IT_DRIVE_FILE_NAME"):
            issues.append("Google Drive credentials")
            
        if not issues:
            print("✅ Ready for REAL SERVICE tests")
            print("   Command: pytest -q -m integration tests/integration/test_native_iq_integration.py")
            print("   ⚠️  This will send real emails and create calendar events!")
        else:
            print(f"❌ Missing: {', '.join(issues)}")
            print("   Fix issues above before running real service tests")
    
    print("\n🔗 Next Steps:")
    print("1. Review INTEGRATION_TEST_SETUP.md for detailed setup")
    print("2. Copy env.integration.example to .env.integration")  
    print("3. Fill in your credentials in .env.integration")
    print("4. Load environment: source .env.integration (Linux/Mac)")
    print("5. Run tests: pytest -m integration tests/integration/test_native_iq_integration.py")

if __name__ == "__main__":
    main()
