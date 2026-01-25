#!/usr/bin/env python3
"""
Generate forecast.csv files from existing JSON outputs
for BOOK_TEST subscriber predictions
"""

import os
import json
import csv
from pathlib import Path
from datetime import datetime

def process_subscriber_directory(sub_dir):
    """Process a single subscriber output directory and create forecast.csv"""
    # Find all daily JSON files (exclude summary.json)
    json_files = sorted([f for f in sub_dir.glob('*.json') if f.name != 'summary.json'])
    
    if not json_files:
        return False
    
    # Collect all predictions from daily JSONs
    all_rows = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Extract date from filename
            date_str = json_file.stem  # e.g., "2025-01-01"
            
            # Get overall score and determine band
            score = data.get('score', 0)
            if score >= 70:
                band = 'GREEN'
            elif score >= 50:
                band = 'YELLOW'
            else:
                band = 'RED'
            
            # Process picks for each game
            if 'picks' in data:
                for game, picks_data in data['picks'].items():
                    # Get lane_system picks
                    lane_system = picks_data.get('lane_system', [])
                    
                    for pick in lane_system:
                        row = {
                            'date': date_str,
                            'game': game,
                            'prediction': pick,
                            'confidence': round(score, 2),
                            'odds': '',
                            'band': band,
                            'play_type': 'STRAIGHT',
                        }
                        all_rows.append(row)
        except Exception as e:
            print(f"  Error processing {json_file.name}: {e}")
            continue
    
    if not all_rows:
        return False
    
    # Write forecast.csv
    forecast_path = sub_dir / 'forecast.csv'
    
    try:
        with open(forecast_path, 'w', newline='') as f:
            fieldnames = ['date', 'game', 'prediction', 'confidence', 'odds', 'band', 'play_type']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        
        return True
    except Exception as e:
        print(f"  Error writing forecast.csv: {e}")
        return False

def main():
    """Process all test subscriber directories"""
    outputs_dir = Path('C:/MyBestOdds/jackpot_system_v3/outputs')
    
    if not outputs_dir.exists():
        print(f"Error: {outputs_dir} does not exist")
        return
    
    # Find all BOOK3_TEST and BOOK_TEST directories
    test_dirs = sorted([d for d in outputs_dir.iterdir() 
                       if d.is_dir() and ('BOOK3_TEST' in d.name or 'BOOK_TEST' in d.name)])
    
    print(f"Found {len(test_dirs)} test directories")
    print(f"Generating forecast.csv files...\n")
    
    success_count = 0
    fail_count = 0
    
    for i, sub_dir in enumerate(test_dirs, 1):
        # Show progress every 10 directories
        if i % 10 == 0 or i == 1:
            print(f"Progress: {i}/{len(test_dirs)} ({success_count} successful)", flush=True)
        
        success = process_subscriber_directory(sub_dir)
        
        if success:
            success_count += 1
        else:
            fail_count += 1
            print(f"Failed: {sub_dir.name}")
    
    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}")
    print(f"Successfully generated: {success_count} forecast.csv files")
    print(f"Failed: {fail_count}")
    print(f"Total processed: {len(test_dirs)}")

if __name__ == "__main__":
    main()
