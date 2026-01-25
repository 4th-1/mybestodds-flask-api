#!/usr/bin/env python3
"""
fix_subscriber_ids.py

Quick utility to analyze and fix subscriber ID conflicts.
Run this whenever you add new subscribers to prevent naming conflicts.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from core.subscriber_id_manager import SubscriberIDManager

def main():
    manager = SubscriberIDManager(PROJECT_ROOT)
    
    print("🔍 Checking for subscriber ID conflicts...")
    conflicts = manager.check_existing_conflicts()
    
    if not conflicts:
        print("✅ No conflicts found! All subscriber IDs are unique.")
        return
    
    print(f"\n⚠️  Found conflicts involving {sum(len(files) for files in conflicts.values())} files:")
    
    for conflict_id, files in conflicts.items():
        print(f"\n🔴 '{conflict_id}' used by:")
        for file_path in files:
            file_name = Path(file_path).name
            print(f"   - {file_name}")
    
    print(f"\n💡 Run the full manager to see suggested fixes:")
    print(f"   python core/subscriber_id_manager.py")

if __name__ == "__main__":
    main()