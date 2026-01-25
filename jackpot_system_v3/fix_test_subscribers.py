#!/usr/bin/env python3
"""
Quick Fix for Test Subscribers - Add Missing Fields
===================================================

Patches the 2000 test subscribers to include required fields for kit processing.
"""

import json
import os
from pathlib import Path

def fix_test_subscribers():
    """Fix all test subscribers by adding missing required fields."""
    
    project_root = Path(__file__).parent.absolute()
    test_subscribers_dir = project_root / "data" / "subscribers" / "BOOK3_TEST"
    
    print("🔧 FIXING TEST SUBSCRIBERS")
    print("=" * 50)
    
    fixed_count = 0
    total_count = 0
    
    # Process all test subscriber files
    for subscriber_file in sorted(test_subscribers_dir.glob("TEST*.json")):
        total_count += 1
        
        try:
            # Load existing subscriber
            with open(subscriber_file, 'r') as f:
                subscriber = json.load(f)
            
            # Add missing required fields
            changes_made = False
            
            # Add coverage_start and coverage_end if missing
            if "coverage_start" not in subscriber:
                subscriber["coverage_start"] = subscriber.get("start_date", "2025-12-22")
                changes_made = True
            
            if "coverage_end" not in subscriber:
                subscriber["coverage_end"] = subscriber.get("end_date", "2025-12-31")  
                changes_made = True
            
            # Add kit_type if missing
            if "kit_type" not in subscriber:
                subscriber["kit_type"] = "BOOK3_TEST"
                changes_made = True
            
            # Add dob if missing (copy from date_of_birth)
            if "dob" not in subscriber and "date_of_birth" in subscriber:
                subscriber["dob"] = subscriber["date_of_birth"]
                changes_made = True
            
            # Add formats if missing
            if "formats" not in subscriber:
                subscriber["formats"] = ["JSON"]
                changes_made = True
            
            # Ensure identity section has birth_date
            if "identity" not in subscriber:
                subscriber["identity"] = {}
                changes_made = True
            
            identity = subscriber["identity"]
            if "birth_date" not in identity and "date_of_birth" in subscriber:
                identity["birth_date"] = subscriber["date_of_birth"]
                changes_made = True
            
            # Add default birth time and location if missing
            if "birth_time" not in identity:
                identity["birth_time"] = "12:00"  # Default noon
                changes_made = True
                
            if "birth_city" not in identity:
                identity["birth_city"] = "Atlanta"
                changes_made = True
                
            if "birth_state" not in identity:
                identity["birth_state"] = "GA"
                changes_made = True
            
            # Copy first_name and last_name to identity if missing
            if "first_name" not in identity and "first_name" in subscriber:
                identity["first_name"] = subscriber["first_name"]
                changes_made = True
                
            if "last_name" not in identity and "last_name" in subscriber:
                identity["last_name"] = subscriber["last_name"]
                changes_made = True
            
            # Save fixed subscriber if changes were made
            if changes_made:
                with open(subscriber_file, 'w') as f:
                    json.dump(subscriber, f, indent=2)
                fixed_count += 1
            
            if total_count % 100 == 0:
                print(f"   ✅ Processed: {total_count}/2000")
                
        except Exception as e:
            print(f"   ❌ Error fixing {subscriber_file.name}: {e}")
            continue
    
    print(f"\n🏆 RESULTS:")
    print(f"   📊 Total subscribers: {total_count}")
    print(f"   🔧 Fixed subscribers: {fixed_count}")
    print(f"   ✅ Success rate: {fixed_count/total_count*100:.1f}%")

def test_fixed_subscriber():
    """Test that a fixed subscriber now works."""
    
    print(f"\n🧪 TESTING FIXED SUBSCRIBER")
    print("=" * 30)
    
    import subprocess
    
    try:
        result = subprocess.run([
            "C:/MyBestOdds/.venv/Scripts/python.exe",
            "run_kit_v3.py", 
            "data/subscribers/BOOK3_TEST/TEST0001_BOOK3.json",
            "BOOK3_TEST"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("   ✅ TEST PASSED! Subscriber can now be processed")
            return True
        else:
            print(f"   ❌ TEST FAILED: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ TEST ERROR: {e}")
        return False

def main():
    fix_test_subscribers()
    test_fixed_subscriber()
    
    print(f"\n🎯 Next steps:")
    print("   1. Stop current batch processor (Ctrl+C)")
    print("   2. Restart with fixed subscribers")
    print("   3. Should now see successful processing!")

if __name__ == "__main__":
    main()