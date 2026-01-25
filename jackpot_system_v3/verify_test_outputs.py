#!/usr/bin/env python3
"""
Verify test subscriber outputs are properly organized
"""

from pathlib import Path
import json

def verify_kit(kit_name):
    """Verify outputs for a specific KIT"""
    print(f"\n{'='*60}")
    print(f"Verifying {kit_name}")
    print(f"{'='*60}")
    
    # Paths
    subscriber_dir = Path(f'C:/MyBestOdds/jackpot_system_v3/data/subscribers/{kit_name}_TEST')
    outputs_dir = Path('C:/MyBestOdds/jackpot_system_v3/outputs')
    
    if not subscriber_dir.exists():
        print(f"❌ Subscriber directory not found: {subscriber_dir}")
        return
    
    # Count subscriber files
    subscriber_files = list(subscriber_dir.glob('*.json'))
    print(f"\n📁 Subscriber files: {len(subscriber_files)}")
    print(f"   Location: {subscriber_dir}")
    
    # Count output directories
    if outputs_dir.exists():
        output_dirs = [d for d in outputs_dir.iterdir() 
                      if d.is_dir() and f'{kit_name}_TEST' in d.name]
        print(f"\n📊 Output directories: {len(output_dirs)}")
        print(f"   Location: {outputs_dir}")
        
        # Count forecast.csv files
        forecast_count = sum(1 for d in output_dirs if (d / 'forecast.csv').exists())
        print(f"\n✅ Forecast.csv files: {forecast_count}/{len(output_dirs)}")
        
        # Check for missing forecasts
        missing = len(output_dirs) - forecast_count
        if missing > 0:
            print(f"⚠️  Missing {missing} forecast.csv files")
            return False
        else:
            print(f"✅ All outputs have forecast.csv files!")
            return True
    else:
        print(f"❌ Outputs directory not found: {outputs_dir}")
        return False

def main():
    """Verify all KITs"""
    print("\n" + "="*60)
    print("TEST SUBSCRIBER OUTPUT VERIFICATION")
    print("="*60)
    
    results = {}
    for kit in ['BOOK3', 'BOOK', 'BOSK']:
        results[kit] = verify_kit(kit)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for kit, success in results.items():
        status = "✅ COMPLETE" if success else "⚠️  NEEDS ATTENTION"
        print(f"{kit}: {status}")
    
    print("\n" + "="*60)
    print("CURRENT STRUCTURE (CORRECT):")
    print("="*60)
    print("INPUT:  data/subscribers/{KIT}_TEST/*.json")
    print("OUTPUT: outputs/{KIT}_{KIT}_TEST####_dates/")
    print("        ├── forecast.csv")
    print("        ├── summary.json")
    print("        └── YYYY-MM-DD.json (daily predictions)")
    print("="*60)

if __name__ == "__main__":
    main()
