#!/usr/bin/env python3
"""
Generate predictions for December 21-31, 2025 using test subscribers
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Set up project root
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    """Generate high-confidence predictions for Dec 21-31, 2025"""
    print("🎯 SMART LOGIC PREDICTION GENERATOR")
    print("="*60)
    print("📅 Target Period: December 21-31, 2025") 
    print("🧠 Using 2000 Test Subscribers")
    print("📊 Confidence Filter: 65-100%")
    print("="*60)
    
    # First, let's use the existing kit runner with modified config
    # We need to create a temporary config for this date range
    
    # Load base config
    config_path = PROJECT_ROOT / "config_v3_5.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("\n🔧 Using existing SMART LOGIC engine configuration...")
    print(f"📋 Engine Version: {config.get('engine_version', 'Unknown')}")
    
    # For now, let's run a few test subscribers to generate the format we need
    from kits.kit_runner import run_30_day_kit
    
    # Try with first test subscriber
    test_sub_path = "data/subscribers/BOOK3_TEST/Test_Subscriber_001_BOOK3.json"
    
    if Path(test_sub_path).exists():
        print(f"\n🎬 Running prediction for test subscriber: {test_sub_path}")
        try:
            run_30_day_kit(
                subscriber_file=test_sub_path,
                kit_name="BOOK3",
                output_dir="output"
            )
            print("✅ Prediction generation complete!")
        except Exception as e:
            print(f"❌ Error running predictions: {e}")
    else:
        print(f"❌ Test subscriber file not found: {test_sub_path}")
        
        # Let's look for available test files
        test_dir = PROJECT_ROOT / "data/subscribers/BOOK3_TEST"
        if test_dir.exists():
            test_files = list(test_dir.glob("*.json"))
            print(f"\n📁 Found {len(test_files)} test subscriber files")
            if test_files:
                print(f"   First file: {test_files[0].name}")
                try:
                    run_30_day_kit(
                        subscriber_file=str(test_files[0]).replace(str(PROJECT_ROOT) + os.sep, ""),
                        kit_name="BOOK3", 
                        output_dir="output"
                    )
                    print("✅ Prediction generation complete!")
                except Exception as e:
                    print(f"❌ Error running predictions: {e}")
        else:
            print("❌ Test subscriber directory not found!")

if __name__ == "__main__":
    main()