#!/usr/bin/env python3
"""
batch_run_all_book3_with_excel.py

Complete BOOK3 processing for all 14 subscribers plus Excel generation
- Runs the remaining subscribers that haven't been processed
- Generates Excel files for all subscribers (existing and new)
"""

import os
import subprocess
import sys
from pathlib import Path
import time

# Project root setup
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# List of all 14 BOOK3 subscribers
BOOK3_SUBSCRIBERS = [
    "JHD_BOOK3.json",      # John HF Douglas
    "AA_BOOK3.json",       # Alisha Asha  
    "JDR_BOOK3.json",      # Jimmy Deshawn Roberts
    "BO_BOOK3.json",       # Bakiea Owens
    "VAL_BOOK3.json",      # Valencia Allen-Love
    "MT_BOOK3.json",       # Martin Taylor
    "CP_BOOK3.json",       # Corey Patterson
    "TN_BOOK3.json",       # Tad Newton
    "YTL_BOOK3.json",      # Yadonnis Tucker Lee
    "JDSII_BOOK3.json",    # Joseph David Smith II
    "JDS_BOOK3.json",      # Joseph D Smith
    "AJS_BOOK3.json",      # Adonna Janay Smith
    "YRS_BOOK3.json",      # Yolanda Renee Smith
    "CW_BOOK3.json",       # Consuela Ward
]

def run_single_subscriber(subscriber_json):
    """Run kit processing for a single subscriber."""
    print(f"\\n{'='*60}")
    print(f"🚀 Processing: {subscriber_json}")
    print(f"{'='*60}")
    
    # Run the kit processing
    cmd = ["python", "run_kit_v3.py", f"BOOK3/{subscriber_json}", "BOOK3"]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ SUCCESS: {subscriber_json}")
            # Look for key output indicators
            output_lines = result.stdout.split('\\n')
            interesting_lines = [line for line in output_lines 
                               if any(keyword in line.lower() 
                                      for keyword in ['saved', 'generated', 'complete', 'summary'])]
            
            if interesting_lines:
                for line in interesting_lines[-3:]:  # Show last 3 interesting lines
                    print(f"   {line}")
            
            return True
        else:
            print(f"❌ FAILED: {subscriber_json}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {subscriber_json} (>5 minutes)")
        return False
    except Exception as e:
        print(f"💥 EXCEPTION: {subscriber_json} - {str(e)}")
        return False

def create_excel_for_subscriber(subscriber_code):
    """Generate Excel file for a subscriber."""
    # Find the output directory
    outputs_dir = PROJECT_ROOT / "outputs"
    pattern = f"BOOK3_{subscriber_code}_2025-12-22_to_2025-12-31"
    
    output_dir = None
    for d in outputs_dir.glob(f"*{subscriber_code}*2025-12-22*"):
        if d.is_dir():
            output_dir = d
            break
    
    if not output_dir:
        print(f"❌ No output directory found for {subscriber_code}")
        return False
    
    print(f"📊 Creating Excel for {subscriber_code}...")
    
    # Run Excel creation
    cmd = ["python", "create_excel_from_daily_jsons.py", str(output_dir)]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ Excel created for {subscriber_code}")
            return True
        else:
            print(f"❌ Excel creation failed for {subscriber_code}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"💥 Excel error for {subscriber_code}: {e}")
        return False

def check_existing_outputs():
    """Check which subscribers already have output directories."""
    outputs_dir = PROJECT_ROOT / "outputs"
    existing = {}
    
    if outputs_dir.exists():
        for output_dir in outputs_dir.iterdir():
            if output_dir.is_dir() and "BOOK3_" in output_dir.name and "2025-12-22" in output_dir.name:
                # Extract subscriber code
                parts = output_dir.name.split("_")
                if len(parts) >= 2:
                    subscriber_code = parts[1]  # e.g., "AA" from "BOOK3_AA_2025-12-22_to_2025-12-31"
                    existing[subscriber_code] = output_dir
    
    return existing

def main():
    print("🎯 BOOK3 Complete Processing & Excel Generation")
    print("=" * 60)
    
    # Check existing outputs
    existing_outputs = check_existing_outputs()
    print(f"\\n📋 Found {len(existing_outputs)} existing outputs:")
    for code, path in existing_outputs.items():
        print(f"   ✅ {code}: {path.name}")
    
    # Map JSON files to subscriber codes
    subscriber_codes = {
        "JHD_BOOK3.json": "JHD",
        "AA_BOOK3.json": "AA",  
        "JDR_BOOK3.json": "JDR",
        "BO_BOOK3.json": "BO",
        "VAL_BOOK3.json": "VAL",
        "MT_BOOK3.json": "MT",
        "CP_BOOK3.json": "CP",
        "TN_BOOK3.json": "TN",
        "YTL_BOOK3.json": "YTL",
        "JDSII_BOOK3.json": "JDSII",
        "JDS_BOOK3.json": "JDS",
        "AJS_BOOK3.json": "AJS",
        "YRS_BOOK3.json": "YRS",
        "CW_BOOK3.json": "CW",
    }
    
    # Process missing subscribers
    missing_subscribers = []
    for json_file, code in subscriber_codes.items():
        if code not in existing_outputs:
            missing_subscribers.append(json_file)
    
    print(f"\\n🔄 Need to process {len(missing_subscribers)} subscribers:")
    for sub in missing_subscribers:
        print(f"   ⏳ {sub}")
    
    # Process missing subscribers
    successful_runs = 0
    if missing_subscribers:
        print(f"\\n🚀 Processing {len(missing_subscribers)} missing subscribers...")
        
        for i, subscriber_json in enumerate(missing_subscribers, 1):
            print(f"\\n[{i}/{len(missing_subscribers)}] Processing {subscriber_json}...")
            
            success = run_single_subscriber(subscriber_json)
            if success:
                successful_runs += 1
            
            # Small delay between processing
            if i < len(missing_subscribers):
                time.sleep(2)
    
    # Generate Excel files for ALL subscribers
    print(f"\\n📊 Generating Excel files for ALL subscribers...")
    excel_successes = 0
    
    # Refresh existing outputs after processing
    existing_outputs = check_existing_outputs()
    
    for code in subscriber_codes.values():
        if code in existing_outputs:
            success = create_excel_for_subscriber(code)
            if success:
                excel_successes += 1
        else:
            print(f"❌ No output directory for {code}")
    
    # Final summary
    print(f"\\n{'='*60}")
    print(f"🏆 FINAL SUMMARY:")
    print(f"{'='*60}")
    print(f"📁 Subscribers processed: {successful_runs}/{len(missing_subscribers)}")
    print(f"📊 Excel files created: {excel_successes}/{len(subscriber_codes)}")
    print(f"💡 Total subscribers: {len(existing_outputs)}/{len(subscriber_codes)}")
    
    if len(existing_outputs) == len(subscriber_codes) and excel_successes == len(subscriber_codes):
        print(f"\\n🎉 SUCCESS: All 14 BOOK3 subscribers processed with Excel files!")
        print(f"   📅 Coverage: December 22-31, 2025")
        print(f"   📂 Files located in: outputs/BOOK3_*_2025-12-22_to_2025-12-31/")
        print(f"   📈 Ready for delivery!")
    else:
        print(f"\\n⚠️  Some subscribers may need attention:")
        for json_file, code in subscriber_codes.items():
            if code not in existing_outputs:
                print(f"   ❌ Missing: {json_file}")

if __name__ == "__main__":
    main()