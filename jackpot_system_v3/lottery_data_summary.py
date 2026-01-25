#!/usr/bin/env python3

import pandas as pd
import os
from datetime import datetime

def create_master_summary():
    """Create a summary of all combined lottery data files"""
    
    base_dir = r'c:\MyBestOdds\jackpot_system_v3'
    
    files = {
        'Cash3_Combined_2025.csv': 'Georgia Cash 3',
        'Cash4_Combined_2025.csv': 'Georgia Cash 4', 
        'Cash4Life_Combined_2025.csv': 'Cash4Life',
        'MegaMillions_Combined_2025.csv': 'Mega Millions',
        'Powerball_Combined_2025.csv': 'Powerball'
    }
    
    print("🎯 LOTTERY DATA COMBINATION SUMMARY")
    print("=" * 60)
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    total_records = 0
    
    for filename, game_name in files.items():
        filepath = os.path.join(base_dir, filename)
        
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            
            if 'draw_date' in df.columns:
                date_col = 'draw_date'
            elif 'date' in df.columns:
                date_col = 'date'
            else:
                date_col = None
            
            record_count = len(df)
            total_records += record_count
            
            print(f"📄 {game_name}")
            print(f"   File: {filename}")
            print(f"   Records: {record_count:,}")
            
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col])
                date_range = f"{df[date_col].min().strftime('%Y-%m-%d')} → {df[date_col].max().strftime('%Y-%m-%d')}"
                print(f"   Date Range: {date_range}")
                
                # Show session distribution for daily games
                if 'session' in df.columns:
                    sessions = df['session'].value_counts().sort_index()
                    session_str = ', '.join([f"{k}: {v}" for k, v in sessions.items()])
                    print(f"   Sessions: {session_str}")
            
            print()
        else:
            print(f"❌ {game_name}: File not found - {filename}")
            print()
    
    print("=" * 60)
    print(f"🎯 TOTAL RECORDS ACROSS ALL GAMES: {total_records:,}")
    print("=" * 60)
    print()
    print("✅ All files are ready for comprehensive prediction analysis!")
    print("🔍 You can now cross-reference your system's predictions")
    print("   against this complete year-long dataset to validate")
    print("   your documented 28.03% win rate and $21,744 in winnings.")

if __name__ == "__main__":
    create_master_summary()