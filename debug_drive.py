#!/usr/bin/env python3
"""
Debug script to test Google Drive file lookup for integration tests.
"""

import os
import sys
from pathlib import Path

# Add paths like the integration test does
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
for p in [str(SRC), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

def test_drive_connection():
    """Test Google Drive API connection and file search."""
    print("🔍 Testing Google Drive API Connection")
    print("=" * 50)
    
    # Test import
    try:
        from domains.tools.google_drive_tool import _drive_service
        print("✅ Successfully imported Google Drive service")
    except Exception as e:
        print(f"❌ Failed to import Drive service: {e}")
        return False
    
    # Test authentication
    if _drive_service.service is None:
        print("❌ Drive service not authenticated")
        return False
    else:
        print("✅ Drive service authenticated")
    
    # Test file listing
    drive_file_name = os.getenv("NI_IT_DRIVE_FILE_NAME", "test_doc")
    print(f"\n🔍 Searching for file: '{drive_file_name}'")
    
    try:
        # Search for exact match
        query = f"name = '{drive_file_name}' and trashed = false"
        print(f"Query: {query}")
        
        files = _drive_service.list_files(query=query, max_results=5)
        
        if files:
            print(f"✅ Found {len(files)} matching file(s):")
            for i, file_obj in enumerate(files, 1):
                print(f"  {i}. Name: {file_obj.name}")
                print(f"     ID: {file_obj.id}")
                print(f"     Type: {file_obj.mime_type}")
                if hasattr(file_obj, 'size') and file_obj.size:
                    print(f"     Size: {file_obj.size} bytes")
                print()
        else:
            print(f"❌ No files found with exact name '{drive_file_name}'")
            
            # Try partial search
            print(f"\n🔍 Trying partial search for files containing '{drive_file_name}'...")
            partial_query = f"name contains '{drive_file_name}' and trashed = false"
            partial_files = _drive_service.list_files(query=partial_query, max_results=10)
            
            if partial_files:
                print(f"✅ Found {len(partial_files)} files containing '{drive_file_name}':")
                for i, file_obj in enumerate(partial_files, 1):
                    print(f"  {i}. Name: {file_obj.name}")
                    print(f"     ID: {file_obj.id}")
                print(f"\n💡 Consider updating NI_IT_DRIVE_FILE_NAME to match one of these exact names")
            else:
                print(f"❌ No files found containing '{drive_file_name}'")
                
                # List recent files
                print(f"\n📁 Listing your 10 most recent Drive files:")
                recent_files = _drive_service.list_files(query="trashed = false", max_results=10)
                if recent_files:
                    for i, file_obj in enumerate(recent_files, 1):
                        print(f"  {i}. {file_obj.name}")
                else:
                    print("❌ No files found in Drive")
        
        return len(files) > 0
        
    except Exception as e:
        print(f"❌ Error searching Drive: {e}")
        return False

def main():
    print("🔧 Google Drive Integration Test Debug")
    print("=" * 50)
    
    # Check environment
    drive_file_name = os.getenv("NI_IT_DRIVE_FILE_NAME", "test_doc")
    print(f"Target file name: {drive_file_name}")
    
    creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "credentials.json")
    token_path = os.getenv("GOOGLE_DRIVE_TOKEN_PATH", "drive_token.json")
    
    print(f"Credentials file: {creds_path}")
    print(f"Token file: {token_path}")
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return
    
    if not os.path.exists(token_path):
        print(f"⚠️  Token file not found: {token_path}")
        print("   This will be created on first OAuth flow")
    
    # Test connection
    success = test_drive_connection()
    
    print("\n📊 Summary:")
    if success:
        print("✅ Drive integration should work - file found!")
        print("   The integration test should pass now.")
    else:
        print("❌ Drive integration will skip - file not found")
        print("   Solutions:")
        print("   1. Upload a file to Google Drive with the exact name from NI_IT_DRIVE_FILE_NAME")
        print("   2. Update NI_IT_DRIVE_FILE_NAME to match an existing file name")
        print("   3. Check Google Drive API permissions")

if __name__ == "__main__":
    main()
