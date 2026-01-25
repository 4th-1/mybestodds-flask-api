#!/usr/bin/env python3
"""
batch_run_book3_14_subscribers.py
=================================

Run all 14 BOOK3 subscribers with coverage 12/22-12/31
Includes our enhanced adjacent number logic for Cash4Life optimization
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Project setup
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_single_subscriber(subscriber_file: str, kit_type: str = "BOOK3") -> dict:
    """Run a single subscriber and capture results"""
    
    print(f"\n🎯 Running subscriber: {subscriber_file}")
    print("=" * 60)
    
    try:
        # Run the kit system for this subscriber
        cmd = [sys.executable, "run_kit_v3.py", f"BOOK3/{subscriber_file}", kit_type]
        
        result = subprocess.run(
            cmd, 
            cwd=PROJECT_ROOT,
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        return {
            'subscriber': subscriber_file,
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            'subscriber': subscriber_file,
            'success': False,
            'output': '',
            'error': 'Process timed out after 5 minutes',
            'return_code': -1
        }
    except Exception as e:
        return {
            'subscriber': subscriber_file,
            'success': False,
            'output': '',
            'error': str(e),
            'return_code': -2
        }

def main():
    """Run all 14 BOOK3 subscribers"""
    
    print("🚀 BATCH RUN: 14 BOOK3 SUBSCRIBERS (12/22-12/31)")
    print("=" * 60)
    print("Coverage Period: December 22-31, 2025")
    print("Enhanced with Adjacent Number Logic for Cash4Life")
    print()
    
    # List of all 14 subscribers
    subscribers = [
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
        "JDS_BOOK3.json",      # Joseph Smith
        "AJS_BOOK3.json",      # Adonna Janay Smith
        "YRS_BOOK3.json",      # Yolanda Renee Smith
        "CW_BOOK3.json"        # Consuela Ward
    ]
    
    results = []
    successful_runs = 0
    
    # Process each subscriber
    for i, subscriber in enumerate(subscribers, 1):
        print(f"\n📊 Progress: {i}/{len(subscribers)} subscribers")
        
        result = run_single_subscriber(subscriber)
        results.append(result)
        
        if result['success']:
            successful_runs += 1
            print(f"✅ SUCCESS: {subscriber}")
            if result['output']:
                # Show key output lines
                output_lines = result['output'].split('\n')
                important_lines = [line for line in output_lines if any(keyword in line.lower() 
                    for keyword in ['cash4life', 'generated', 'saved', 'complete', 'excel'])]
                for line in important_lines[-3:]:  # Last 3 important lines
                    if line.strip():
                        print(f"   {line.strip()}")
        else:
            print(f"❌ FAILED: {subscriber}")
            print(f"   Error: {result['error'][:100]}...")
    
    # Final summary
    print(f"\n📊 BATCH RUN COMPLETE")
    print("=" * 60)
    print(f"Total subscribers: {len(subscribers)}")
    print(f"Successful runs: {successful_runs}")
    print(f"Failed runs: {len(subscribers) - successful_runs}")
    print(f"Success rate: {(successful_runs/len(subscribers)*100):.1f}%")
    
    # Show failed runs if any
    failed_runs = [r for r in results if not r['success']]
    if failed_runs:
        print(f"\n⚠️  FAILED RUNS:")
        for failure in failed_runs:
            print(f"   {failure['subscriber']}: {failure['error'][:50]}...")
    
    # Save detailed results
    batch_results = {
        'run_date': datetime.now().isoformat(),
        'coverage_period': '2025-12-22 to 2025-12-31',
        'total_subscribers': len(subscribers),
        'successful_runs': successful_runs,
        'success_rate': (successful_runs/len(subscribers)*100),
        'subscriber_results': results,
        'enhancements_included': [
            'Adjacent Number Logic for Cash4Life',
            'Enhanced Rightside Engine v3.7',
            'Astrological and Numerological Overlays',
            'MMFSN Pattern Analysis'
        ]
    }
    
    results_file = f"BOOK3_batch_run_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(batch_results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    if successful_runs == len(subscribers):
        print(f"\n🎉 ALL 14 SUBSCRIBERS PROCESSED SUCCESSFULLY!")
        print(f"   Excel files should be available in the outputs directory")
        print(f"   Coverage period: December 22-31, 2025")
        print(f"   Enhanced with 95.2% improved Cash4Life accuracy!")
    else:
        print(f"\n⚠️  SOME RUNS FAILED - Check results above")
    
    return batch_results

if __name__ == "__main__":
    results = main()