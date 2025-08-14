#!/usr/bin/env python3
"""Debug script to test module imports for integration tests."""

import sys
from pathlib import Path

# Add paths like the integration test does
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
for p in [str(SRC), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

print(f"Python path includes:")
for p in sys.path[:5]:
    print(f"  {p}")

# Test email tool import
print("\n=== Testing email tool imports ===")
email_modules = [
    "src.domains.tools.email_tool",
    "domains.tools.email_tool",
]

for mod_path in email_modules:
    try:
        import importlib
        mod = importlib.import_module(mod_path)
        print(f"✅ Successfully imported {mod_path}")
        
        # Check for functions
        candidates = ["email_tool", "send_email", "send"]
        for cand in candidates:
            fn = getattr(mod, cand, None)
            if fn and callable(fn):
                print(f"  ✅ Found callable: {cand}")
            else:
                print(f"  ❌ No callable: {cand}")
                
        # List all functions
        funcs = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith('_')]
        print(f"  All callables: {funcs}")
        
    except Exception as e:
        print(f"❌ Failed to import {mod_path}: {e}")

# Test calendar tool import
print("\n=== Testing calendar tool imports ===")
calendar_modules = [
    "src.domains.tools.calendar_tool",
    "domains.tools.calendar_tool", 
    "src.domains.tools.calandar_tool",
    "domains.tools.calandar_tool",
]

for mod_path in calendar_modules:
    try:
        mod = importlib.import_module(mod_path)
        print(f"✅ Successfully imported {mod_path}")
        
        # Check for functions
        candidates = ["schedule_meeting", "create_event", "schedule"]
        for cand in candidates:
            fn = getattr(mod, cand, None)
            if fn and callable(fn):
                print(f"  ✅ Found callable: {cand}")
            else:
                print(f"  ❌ No callable: {cand}")
                
        # List all functions
        funcs = [name for name in dir(mod) if callable(getattr(mod, name)) and not name.startswith('_')]
        print(f"  All callables: {funcs}")
        
    except Exception as e:
        print(f"❌ Failed to import {mod_path}: {e}")

# Test drive tool import
print("\n=== Testing drive tool imports ===")
drive_modules = [
    "src.domains.tools.google_drive_tool",
    "domains.tools.google_drive_tool",
]

for mod_path in drive_modules:
    try:
        mod = importlib.import_module(mod_path)
        print(f"✅ Successfully imported {mod_path}")
        
        # Check for _drive_service
        drive_service = getattr(mod, "_drive_service", None)
        if drive_service:
            print(f"  ✅ Found _drive_service")
            if hasattr(drive_service, "list_files"):
                print(f"  ✅ _drive_service has list_files method")
            else:
                print(f"  ❌ _drive_service missing list_files method")
        else:
            print(f"  ❌ No _drive_service found")
            
    except Exception as e:
        print(f"❌ Failed to import {mod_path}: {e}")

print("\n=== Done ===")
