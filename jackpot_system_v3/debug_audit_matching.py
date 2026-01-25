"""
DEBUG AUDIT - Check specific examples to understand matching issues
"""

import pandas as pd
from pathlib import Path

# Load authoritative data
auth_file = Path("C:/MyBestOdds/jackpot_system_v3/output/AUDIT_CORRECTED_V3_7/authoritative_master_results.csv")
auth_df = pd.read_csv(auth_file)
auth_df['date'] = pd.to_datetime(auth_df['date']).dt.date

# Test specific case: Cash4Life on 2025-09-01
test_date = pd.to_datetime('2025-09-01').date()
test_game = 'Cash4Life'

print("DEBUG: Testing Cash4Life matching")
print(f"Looking for: date={test_date}, game={test_game}")

# Find matches
matches = auth_df[
    (auth_df['date'] == test_date) & 
    (auth_df['game'] == test_game)
]

print(f"Found {len(matches)} matches:")
print(matches)

if not matches.empty:
    winning_combo = matches.iloc[0]['winning_number']
    print(f"\nWinning combination: {winning_combo}")
    
    # Test prediction 9
    prediction = "9"
    print(f"Testing prediction: {prediction}")
    
    # Extract all numbers from winning combo
    import re
    all_numbers = re.findall(r'\d+', winning_combo)
    print(f"All numbers in combo: {all_numbers}")
    
    # Check if prediction matches any number
    pred_int = int(prediction)
    padded = str(pred_int).zfill(2)
    
    print(f"Prediction as int: {pred_int}")
    print(f"Prediction padded: {padded}")
    print(f"Match found: {padded in all_numbers or str(pred_int) in all_numbers}")

# Check Cash3/Cash4 matching too
print("\n" + "="*50)
print("DEBUG: Testing Cash3 matching")

test_date_c3 = pd.to_datetime('2025-09-01').date()
test_game_c3 = 'Cash3'

matches_c3 = auth_df[
    (auth_df['date'] == test_date_c3) & 
    (auth_df['game'] == test_game_c3)
]

print(f"Cash3 matches on {test_date_c3}:")
print(matches_c3)