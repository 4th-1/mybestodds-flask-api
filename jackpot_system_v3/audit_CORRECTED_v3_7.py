"""
CORRECTED AUDIT SYSTEM v3.7
Uses AUTHORITATIVE CSV files as provided by user for proper apples-to-apples comparison

Authoritative Data Sources:
- cash3_results.csv 
- cash4_results.csv
- Cash4Life.csv
- MegaMillions.csv  
- Powerball.csv

These are the ONLY sources that should be used for verification across all games.
"""

import json
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, date

# --------------------------------------------------------------------
# PROJECT SETUP
# --------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Data paths - Using AUTHORITATIVE locations
GA_RESULTS_DIR = PROJECT_ROOT / "data" / "results" / "ga_results"
JACKPOT_RESULTS_DIR = PROJECT_ROOT / "data" / "results" / "jackpot_results"
OUTPUTS_DIR = PROJECT_ROOT / "output"
AUDIT_DIR = OUTPUTS_DIR / "AUDIT_CORRECTED_V3_7"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

# Date range for validation
START_DATE = "2025-09-01"
END_DATE = "2025-11-10"

print(f"[CORRECTED AUDIT] Using authoritative data sources:")
print(f"  - GA Results: {GA_RESULTS_DIR}")
print(f"  - Jackpot Results: {JACKPOT_RESULTS_DIR}")
print(f"  - Date Range: {START_DATE} to {END_DATE}")

# --------------------------------------------------------------------
# AUTHORITATIVE DATA LOADERS
# --------------------------------------------------------------------

def load_authoritative_cash3():
    """Load Cash3 from authoritative cash3_results.csv"""
    csv_path = GA_RESULTS_DIR / "cash3_results.csv"
    if not csv_path.exists():
        print(f"[ERROR] Authoritative Cash3 file not found: {csv_path}")
        return pd.DataFrame()
    
    print(f"[LOAD] Cash3 from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Expected columns: draw_date,session,digits,game,row_id
    df['date'] = pd.to_datetime(df['draw_date']).dt.date
    df['game'] = 'Cash3'
    df['session'] = df['session'].str.capitalize()  # MIDDAY -> Midday
    df['winning_number'] = df['digits'].astype(str).str.zfill(3)
    
    # Filter date range
    start_dt = pd.to_datetime(START_DATE).date()
    end_dt = pd.to_datetime(END_DATE).date()
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
    
    return df[['date', 'game', 'session', 'winning_number']]


def load_authoritative_cash4():
    """Load Cash4 from authoritative cash4_results.csv"""
    csv_path = GA_RESULTS_DIR / "cash4_results.csv"
    if not csv_path.exists():
        print(f"[ERROR] Authoritative Cash4 file not found: {csv_path}")
        return pd.DataFrame()
    
    print(f"[LOAD] Cash4 from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Expected columns: draw_date,session,digits,game,row_id
    df['date'] = pd.to_datetime(df['draw_date']).dt.date
    df['game'] = 'Cash4'
    df['session'] = df['session'].str.capitalize()  # EVENING -> Evening
    df['winning_number'] = df['digits'].astype(str).str.zfill(4)
    
    # Filter date range
    start_dt = pd.to_datetime(START_DATE).date()
    end_dt = pd.to_datetime(END_DATE).date()
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
    
    return df[['date', 'game', 'session', 'winning_number']]


def load_authoritative_cash4life():
    """Load Cash4Life from authoritative Cash4Life.csv"""
    csv_path = JACKPOT_RESULTS_DIR / "Cash4Life.csv"
    if not csv_path.exists():
        print(f"[ERROR] Authoritative Cash4Life file not found: {csv_path}")
        return pd.DataFrame()
    
    print(f"[LOAD] Cash4Life from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Expected columns: game,date,n1,n2,n3,n4,n5,bonus
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['game'] = 'Cash4Life'
    df['session'] = None  # Jackpot games don't have sessions
    
    # Create winning number as "n1-n2-n3-n4-n5+bonus"
    df['winning_number'] = df.apply(lambda row: 
        f"{row['n1']:02d}-{row['n2']:02d}-{row['n3']:02d}-{row['n4']:02d}-{row['n5']:02d}+{row['bonus']:02d}", 
        axis=1)
    
    # Filter date range
    start_dt = pd.to_datetime(START_DATE).date()
    end_dt = pd.to_datetime(END_DATE).date()
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
    
    return df[['date', 'game', 'session', 'winning_number']]


def load_authoritative_megamillions():
    """Load MegaMillions from authoritative MegaMillions.csv"""
    csv_path = JACKPOT_RESULTS_DIR / "MegaMillions.csv"
    if not csv_path.exists():
        print(f"[ERROR] Authoritative MegaMillions file not found: {csv_path}")
        return pd.DataFrame()
    
    print(f"[LOAD] MegaMillions from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Expected columns: game,date,n1,n2,n3,n4,n5,bonus
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['game'] = 'MegaMillions'
    df['session'] = None  # Jackpot games don't have sessions
    
    # Create winning number as "n1-n2-n3-n4-n5+bonus"
    df['winning_number'] = df.apply(lambda row: 
        f"{row['n1']:02d}-{row['n2']:02d}-{row['n3']:02d}-{row['n4']:02d}-{row['n5']:02d}+{row['bonus']:02d}", 
        axis=1)
    
    # Filter date range
    start_dt = pd.to_datetime(START_DATE).date()
    end_dt = pd.to_datetime(END_DATE).date()
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
    
    return df[['date', 'game', 'session', 'winning_number']]


def load_authoritative_powerball():
    """Load Powerball from authoritative Powerball.csv"""
    csv_path = JACKPOT_RESULTS_DIR / "Powerball.csv"
    if not csv_path.exists():
        print(f"[ERROR] Authoritative Powerball file not found: {csv_path}")
        return pd.DataFrame()
    
    print(f"[LOAD] Powerball from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Expected columns: game,date,n1,n2,n3,n4,n5,bonus
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['game'] = 'Powerball'
    df['session'] = None  # Jackpot games don't have sessions
    
    # Create winning number as "n1-n2-n3-n4-n5+bonus"
    df['winning_number'] = df.apply(lambda row: 
        f"{row['n1']:02d}-{row['n2']:02d}-{row['n3']:02d}-{row['n4']:02d}-{row['n5']:02d}+{row['bonus']:02d}", 
        axis=1)
    
    # Filter date range
    start_dt = pd.to_datetime(START_DATE).date()
    end_dt = pd.to_datetime(END_DATE).date()
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
    
    return df[['date', 'game', 'session', 'winning_number']]


def load_all_authoritative_results():
    """Load ALL authoritative historical results for proper comparison"""
    print("\n" + "="*60)
    print("LOADING AUTHORITATIVE HISTORICAL RESULTS")
    print("="*60)
    
    frames = []
    
    # Load each game from authoritative sources
    cash3_df = load_authoritative_cash3()
    if not cash3_df.empty:
        frames.append(cash3_df)
        print(f"[✓] Cash3: {len(cash3_df)} records loaded")
    
    cash4_df = load_authoritative_cash4()
    if not cash4_df.empty:
        frames.append(cash4_df)
        print(f"[✓] Cash4: {len(cash4_df)} records loaded")
    
    c4l_df = load_authoritative_cash4life()
    if not c4l_df.empty:
        frames.append(c4l_df)
        print(f"[✓] Cash4Life: {len(c4l_df)} records loaded")
    
    mm_df = load_authoritative_megamillions()
    if not mm_df.empty:
        frames.append(mm_df)
        print(f"[✓] MegaMillions: {len(mm_df)} records loaded")
    
    pb_df = load_authoritative_powerball()
    if not pb_df.empty:
        frames.append(pb_df)
        print(f"[✓] Powerball: {len(pb_df)} records loaded")
    
    if not frames:
        print("[ERROR] No authoritative data could be loaded!")
        return pd.DataFrame()
    
    # Combine all results
    all_results = pd.concat(frames, ignore_index=True)
    
    print(f"\n[MASTER] Total authoritative records: {len(all_results)}")
    print("Game breakdown:")
    for game in all_results['game'].unique():
        game_count = len(all_results[all_results['game'] == game])
        print(f"  - {game}: {game_count} records")
    
    # Save master authoritative file
    master_file = AUDIT_DIR / "authoritative_master_results.csv"
    all_results.to_csv(master_file, index=False)
    print(f"\n[SAVED] Master file: {master_file}")
    
    return all_results


# --------------------------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------------------------

if __name__ == "__main__":
    print("CORRECTED AUDIT SYSTEM v3.7")
    print("Using ONLY authoritative CSV files for apples-to-apples comparison")
    print("="*60)
    
    # Load all authoritative results
    master_results = load_all_authoritative_results()
    
    if master_results.empty:
        print("[CRITICAL] No authoritative data available - cannot proceed with audit")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("AUTHORITATIVE DATA SUMMARY")
    print("="*60)
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Total Records: {len(master_results)}")
    print(f"Date Coverage: {master_results['date'].min()} to {master_results['date'].max()}")
    
    print("\nSample records:")
    print(master_results.head(10).to_string(index=False))
    
    print(f"\n[SUCCESS] Authoritative historical data prepared for audit comparisons")
    print(f"[NEXT] Use this master file for all accuracy testing: {AUDIT_DIR / 'authoritative_master_results.csv'}")