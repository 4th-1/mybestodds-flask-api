#!/usr/bin/env python3

import pandas as pd
import re
from datetime import datetime
import os

def parse_cash4_text_file(filepath):
    """Parse the text format Cash4 file"""
    data = []
    
    # Try different encodings
    encodings = ['utf-16', 'utf-8', 'cp1252', 'iso-8859-1', 'utf-16-le', 'utf-16-be']
    lines = []
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                lines = f.readlines()
            print(f"Successfully read file with encoding: {encoding}")
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if not lines:
        raise ValueError("Could not decode file with any encoding")
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('Date'):
            continue
            
        # Parse format like: "8/31/2025	NIGHT	6 5 8 8	206"
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3:
                date_str = parts[0].strip()
                session = parts[1].strip()
                numbers_str = parts[2].strip()
                
                # Extract date
                try:
                    date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                except:
                    continue
                
                # Normalize session names
                session_map = {
                    'NIGHT': 'NIGHT',
                    'EVENING': 'EVENING',
                    'MIDDAY': 'MIDDAY'
                }
                session = session_map.get(session, session.upper())
                
                # Extract numbers - handle different formats
                # Format: "6 5 8 8" or "6\xa05\xa08\xa08" (with non-breaking spaces)
                digits = ""
                
                # Replace non-breaking spaces and other special chars
                numbers_str = re.sub(r'[\xa0\u00A0]', ' ', numbers_str)  # Non-breaking space
                
                if ' ' in numbers_str:
                    # Handle space format
                    numbers = numbers_str.split()
                    numbers = [n.strip() for n in numbers if n.strip().isdigit()]
                    if len(numbers) == 4:
                        digits = ''.join(numbers)
                
                if len(digits) == 4 and digits.isdigit():
                    data.append({
                        'draw_date': formatted_date,
                        'session': session,
                        'digits': digits,
                        'game': 'Cash4',
                        'row_id': len(data) + 1
                    })
    
    return pd.DataFrame(data)

def main():
    # File paths
    csv_file = r'c:\MyBestOdds\jackpot_system_v3\data\results\ga_results\cash4_results.csv'
    text_file = r'c:\MyBestOdds\jackpot_system_v3\data\results\ga_results\Cash4 Jan_Aug2025 - Copy.txt'
    output_file = r'c:\MyBestOdds\jackpot_system_v3\Cash4_Combined_2025.csv'
    
    # Load CSV data (Sept-Oct 2025)
    print("Loading CSV data (Sept-Oct 2025)...")
    df_csv = pd.read_csv(csv_file)
    df_csv['draw_date'] = pd.to_datetime(df_csv['draw_date']).dt.strftime('%Y-%m-%d')
    
    # Parse text data (Jan-Aug 2025)
    print("Parsing text data (Jan-Aug 2025)...")
    df_text = parse_cash4_text_file(text_file)
    
    # Combine both datasets
    print("Combining datasets...")
    combined_df = pd.concat([df_text, df_csv], ignore_index=True)
    
    # Sort by date and session
    combined_df['draw_date'] = pd.to_datetime(combined_df['draw_date'])
    combined_df = combined_df.sort_values(['draw_date', 'session'])
    combined_df['draw_date'] = combined_df['draw_date'].dt.strftime('%Y-%m-%d')
    
    # Reset row_id
    combined_df['row_id'] = range(1, len(combined_df) + 1)
    
    # Remove duplicates if any (by date and session)
    combined_df = combined_df.drop_duplicates(subset=['draw_date', 'session'], keep='last')
    
    # Save to CSV
    combined_df.to_csv(output_file, index=False)
    
    print(f"\n✅ Combined Cash4 data saved to: {output_file}")
    print(f"📊 Total records: {len(combined_df)}")
    print(f"📅 Date range: {combined_df['draw_date'].min()} to {combined_df['draw_date'].max()}")
    
    # Show session distribution
    print(f"\n🔍 Session distribution:")
    print(combined_df['session'].value_counts().sort_index())
    
    # Show first few and last few records
    print(f"\n🔍 First 5 records:")
    print(combined_df.head())
    print(f"\n🔍 Last 5 records:")
    print(combined_df.tail())

if __name__ == "__main__":
    main()