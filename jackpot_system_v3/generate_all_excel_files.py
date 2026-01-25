#!/usr/bin/env python3
"""
generate_all_excel_files.py

Generate Excel files for all BOOK3 December 2025 outputs
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

def main():
    print("Generating Excel files for all December 2025 BOOK3 outputs...")
    
    # Find all December 2025 directories
    december_dirs = []
    if OUTPUTS_DIR.exists():
        for d in OUTPUTS_DIR.iterdir():
            if (d.is_dir() and 
                d.name.startswith("BOOK3_") and 
                "2025-12-22_to_2025-12-31" in d.name):
                december_dirs.append(d)
    
    print(f"Found {len(december_dirs)} December directories:")
    for d in december_dirs:
        print(f"  {d.name}")
    
    # Generate Excel for each directory
    successes = 0
    failures = 0
    
    for i, output_dir in enumerate(december_dirs, 1):
        print(f"\n[{i}/{len(december_dirs)}] Processing {output_dir.name}...")
        
        cmd = ["python", "create_excel_from_daily_jsons.py", str(output_dir)]
        
        try:
            result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"  SUCCESS!")
                successes += 1
            else:
                print(f"  FAILED: {result.stderr[:100] if result.stderr else 'Unknown error'}")
                failures += 1
                
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            failures += 1
    
    print(f"\n" + "="*50)
    print(f"SUMMARY:")
    print(f"  Total directories: {len(december_dirs)}")
    print(f"  Excel files created: {successes}")
    print(f"  Failures: {failures}")
    
    if failures == 0:
        print(f"\\nAll Excel files generated successfully!")
        print(f"Files are located in each output directory as [DirectoryName].xlsx")
    else:
        print(f"\\nSome failures occurred. Check individual directories.")

if __name__ == "__main__":
    main()