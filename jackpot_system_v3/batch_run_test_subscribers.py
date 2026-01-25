#!/usr/bin/env python3
"""
BATCH BOOK3 TEST RUNNER v3.7
Run all 2000 BOOK3 test subscribers with Swiss Ephemeris integration
"""

import os
import sys
import glob
import subprocess
import time
from datetime import datetime

# Set up project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def run_batch_predictions():
    """Run predictions for all 2000 BOOK3 test subscribers"""
    
    print("🚀 BATCH BOOK3 TEST RUNNER v3.7")
    print("="*60)
    print("📊 Swiss Ephemeris Integration: NASA-precision astronomy")
    print("📅 Date Range: January 1 - November 10, 2025")
    print("🎯 Subscribers: 2000 BOOK3 test accounts")
    print("="*60)
    
    # Find all test subscriber files
    subscriber_pattern = "data/subscribers/BOOK3_TEST/*_BOOK3.json"
    subscriber_files = glob.glob(subscriber_pattern)
    
    total_subscribers = len(subscriber_files)
    print(f"\n📋 Found {total_subscribers} BOOK3 test subscribers")
    
    if total_subscribers == 0:
        print("❌ No subscriber files found!")
        return
    
    # Python executable path
    python_exe = "C:/MyBestOdds/.venv/Scripts/python.exe"
    
    # Track progress
    start_time = time.time()
    successful_runs = 0
    failed_runs = 0
    
    print(f"\n🎬 Starting batch run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("⏳ This will take considerable time with Swiss Ephemeris calculations...")
    
    for i, subscriber_file in enumerate(subscriber_files, 1):
        # Extract subscriber ID from filename
        filename = os.path.basename(subscriber_file)
        subscriber_id = filename.replace('_BOOK3.json', '')
        
        print(f"\n📊 [{i:4d}/{total_subscribers}] Processing {subscriber_id}...")
        
        try:
            # Run the kit prediction system
            cmd = [python_exe, "run_kit_v3.py", subscriber_file, "BOOK3"]
            
            # Run with timeout and capture output
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 minute timeout per subscriber
                cwd=PROJECT_ROOT
            )
            
            if result.returncode == 0:
                successful_runs += 1
                print(f"  ✅ {subscriber_id} completed successfully")
            else:
                failed_runs += 1
                print(f"  ❌ {subscriber_id} failed (exit code: {result.returncode})")
                if result.stderr:
                    print(f"     Error: {result.stderr[:200]}...")
                    
        except subprocess.TimeoutExpired:
            failed_runs += 1
            print(f"  ⏰ {subscriber_id} timed out (>5 minutes)")
            
        except Exception as e:
            failed_runs += 1
            print(f"  💥 {subscriber_id} exception: {str(e)[:100]}...")
        
        # Progress update every 50 subscribers
        if i % 50 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (total_subscribers - i) * avg_time
            
            print(f"\n📈 PROGRESS UPDATE:")
            print(f"   Completed: {i}/{total_subscribers} ({i/total_subscribers*100:.1f}%)")
            print(f"   Successful: {successful_runs}")
            print(f"   Failed: {failed_runs}")
            print(f"   Average time per subscriber: {avg_time:.1f}s")
            print(f"   Estimated time remaining: {remaining/60:.1f} minutes")
    
    # Final summary
    total_time = time.time() - start_time
    
    print(f"\n" + "="*60)
    print("🎊 BATCH RUN COMPLETE!")
    print("="*60)
    print(f"📊 Total subscribers processed: {total_subscribers}")
    print(f"✅ Successful runs: {successful_runs}")
    print(f"❌ Failed runs: {failed_runs}")
    print(f"📈 Success rate: {successful_runs/total_subscribers*100:.1f}%")
    print(f"⏱️  Total time: {total_time/60:.1f} minutes")
    print(f"⚡ Average per subscriber: {total_time/total_subscribers:.1f}s")
    print(f"🌟 Swiss Ephemeris calculations: NASA-precision astronomy")
    print(f"🎯 Ready for comprehensive analysis!")

if __name__ == "__main__":
    run_batch_predictions()