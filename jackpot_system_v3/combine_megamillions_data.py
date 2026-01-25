#!/usr/bin/env python3

import pandas as pd
import re
from datetime import datetime
import os

def parse_megamillions_text_file(filepath):
    """Parse the text format MegaMillions file"""
    data = []
    
    # Try different encodings
    encodings = ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']
    lines = []
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                lines = f.readlines()
            print(f"Successfully read file with encoding: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if not lines:
        raise ValueError("Could not decode file with any encoding")
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('Date'):
            continue
            
        # Parse format like: "8/29/2025	13 31 32 44 45 Mega Ball: 21	"
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                date_str = parts[0].strip()
                numbers_str = parts[1].strip()
                
                # Extract date
                try:
                    date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                except:
                    continue
                
                # Extract numbers and mega ball
                # Format: "13 31 32 44 45 Mega Ball: 21" or variations
                # Remove any extra text like "Megaplier2X"
                numbers_str = re.sub(r'Megaplier\d+X', '', numbers_str).strip()
                
                match = re.match(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+Mega Ball:\s*(\d+)', numbers_str)
                if match:
                    n1, n2, n3, n4, n5, bonus = match.groups()
                    
                    data.append({
                        'game': 'Mega Millions',
                        'date': formatted_date,
                        'n1': int(n1),
                        'n2': int(n2),
                        'n3': int(n3),
                        'n4': int(n4),
                        'n5': int(n5),
                        'bonus': int(bonus)
                    })
    
    return pd.DataFrame(data)

def main():
    # File paths
    csv_file = r'c:\MyBestOdds\jackpot_system_v3\data\results\jackpot_results\MegaMillions.csv'
    text_file = r'c:\MyBestOdds\jackpot_system_v3\data\results\jackpot_results\MegaMillions_Jan_Aug2025.txt'
    output_file = r'c:\MyBestOdds\jackpot_system_v3\MegaMillions_Combined_2025.csv'
    
    # Load CSV data (Sept-Nov 2025)
    print("Loading CSV data (Sept-Nov 2025)...")
    df_csv = pd.read_csv(csv_file)
    df_csv['date'] = pd.to_datetime(df_csv['date']).dt.strftime('%Y-%m-%d')
    
    # Parse text data (Jan-Aug 2025)
    print("Parsing text data (Jan-Aug 2025)...")
    df_text = parse_megamillions_text_file(text_file)
    
    # Combine both datasets
    print("Combining datasets...")
    combined_df = pd.concat([df_text, df_csv], ignore_index=True)
    
    # Sort by date
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    combined_df = combined_df.sort_values('date')
    combined_df['date'] = combined_df['date'].dt.strftime('%Y-%m-%d')
    
    # Remove duplicates if any
    combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
    
    # Save to CSV
    combined_df.to_csv(output_file, index=False)
    
    print(f"\n✅ Combined MegaMillions data saved to: {output_file}")
    print(f"📊 Total records: {len(combined_df)}")
    print(f"📅 Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    
    # Show first few and last few records
    print(f"\n🔍 First 5 records:")
    print(combined_df.head())
    print(f"\n🔍 Last 5 records:")
    print(combined_df.tail())

if __name__ == "__main__":
    main()