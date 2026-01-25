"""
COMPREHENSIVE AUDIT TOOL v3.7 - APPLES TO APPLES COMPARISON
Uses ONLY the authoritative CSV files for true accuracy validation

This tool will:
1. Load predictions from system outputs  
2. Compare against AUTHORITATIVE historical data
3. Calculate true accuracy metrics for each kit level
4. Generate detailed performance reports

NO OTHER DATA SOURCES WILL BE USED - only the authoritative CSVs.
"""

import json
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, date
import glob

# --------------------------------------------------------------------
# PROJECT SETUP
# --------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Use the authoritative master file we just created
AUTHORITATIVE_FILE = PROJECT_ROOT / "output" / "AUDIT_CORRECTED_V3_7" / "authoritative_master_results.csv"
OUTPUTS_DIR = PROJECT_ROOT / "output"
AUDIT_OUTPUT_DIR = PROJECT_ROOT / "output" / "COMPREHENSIVE_AUDIT_V3_7"
AUDIT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[AUDIT] Using authoritative data: {AUTHORITATIVE_FILE}")
print(f"[AUDIT] Outputs directory: {OUTPUTS_DIR}")

# --------------------------------------------------------------------
# LOAD AUTHORITATIVE RESULTS
# --------------------------------------------------------------------

def load_authoritative_master():
    """Load the master authoritative results file"""
    if not AUTHORITATIVE_FILE.exists():
        print(f"[ERROR] Authoritative master file not found: {AUTHORITATIVE_FILE}")
        print("Run audit_CORRECTED_v3_7.py first to generate the authoritative dataset!")
        return None
    
    df = pd.read_csv(AUTHORITATIVE_FILE)
    df['date'] = pd.to_datetime(df['date']).dt.date
    print(f"[LOADED] {len(df)} authoritative results from {df['date'].min()} to {df['date'].max()}")
    return df

# --------------------------------------------------------------------
# PREDICTION LOADERS
# --------------------------------------------------------------------

def find_prediction_files():
    """Find all forecast.csv files in output directories"""
    prediction_files = []
    
    # Look for forecast.csv files in output directories
    for output_dir in OUTPUTS_DIR.glob("*"):
        if output_dir.is_dir() and not output_dir.name.startswith("AUDIT"):
            forecast_file = output_dir / "forecast.csv"
            if forecast_file.exists():
                prediction_files.append(forecast_file)
    
    print(f"[FOUND] {len(prediction_files)} prediction files:")
    for file in prediction_files:
        print(f"  - {file}")
    
    return prediction_files

def load_predictions(forecast_file):
    """Load predictions from a forecast.csv file"""
    try:
        df = pd.read_csv(forecast_file)
        
        # Ensure date column exists and is properly formatted
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
        elif 'forecast_date' in df.columns:
            df['date'] = pd.to_datetime(df['forecast_date']).dt.date
        else:
            print(f"[WARNING] No date column found in {forecast_file}")
            return None
        
        # Extract kit info from file path
        parent_dir = forecast_file.parent.name
        if "BOOK3" in parent_dir:
            df['kit_level'] = 'BOOK3'
        elif "BOOK" in parent_dir:
            df['kit_level'] = 'BOOK' 
        elif "BOSK" in parent_dir:
            df['kit_level'] = 'BOSK'
        else:
            df['kit_level'] = 'UNKNOWN'
        
        df['source_file'] = str(forecast_file)
        
        return df
    
    except Exception as e:
        print(f"[ERROR] Failed to load {forecast_file}: {e}")
        return None

# --------------------------------------------------------------------
# ACCURACY CALCULATION
# --------------------------------------------------------------------

def calculate_accuracy_for_predictions(predictions_df, authoritative_df):
    """Calculate accuracy by comparing predictions to authoritative results"""
    
    results = []
    
    for _, pred_row in predictions_df.iterrows():
        pred_date = pred_row['date']
        pred_game = pred_row.get('game', 'Unknown')
        pred_session = pred_row.get('draw_time', pred_row.get('session', None))
        pred_number = str(pred_row.get('number', pred_row.get('candidate', pred_row.get('winning_number', ''))))
        kit_level = pred_row.get('kit_level', 'Unknown')
        
        # Skip invalid predictions (0 or empty)
        if not pred_number or pred_number == '0' or pred_number == 'nan':
            continue
        
        # Find matching authoritative results
        auth_matches = authoritative_df[
            (authoritative_df['date'] == pred_date) &
            (authoritative_df['game'] == pred_game)
        ]
        
        # Session matching logic - only for games that have sessions
        if pred_session and pred_game in ['Cash3', 'Cash4']:
            pred_session_norm = normalize_session_name(pred_session)
            if pred_session_norm:
                auth_matches = auth_matches[auth_matches['session'] == pred_session_norm]
        # For jackpot games, ignore session since they don't have sessions in authoritative data
        
        # Check for match based on game type
        hit = False
        winning_numbers = []
        
        if not auth_matches.empty:
            winning_numbers = auth_matches['winning_number'].tolist()
            
            if pred_game in ['Cash3', 'Cash4']:
                # Direct number comparison for Cash3/Cash4
                if pred_number in winning_numbers:
                    hit = True
            else:
                # For jackpot games, check if prediction number appears in any winning combination
                for winning_combo in winning_numbers:
                    if check_jackpot_hit(pred_number, winning_combo):
                        hit = True
                        break
        
        results.append({
            'date': pred_date,
            'game': pred_game,
            'session': pred_session,
            'kit_level': kit_level,
            'prediction': pred_number,
            'actual_winners': ', '.join([str(x) for x in winning_numbers]),
            'hit': hit,
            'source_file': pred_row['source_file']
        })
    
    return pd.DataFrame(results)


def normalize_session_name(session):
    """Normalize session names for comparison"""
    if not session:
        return None
    
    session_str = str(session).strip().lower()
    if session_str in ['midday', 'mid', 'day']:
        return 'Midday'
    elif session_str in ['evening', 'eve', 'pm']:
        return 'Evening'
    elif session_str in ['night', 'late', 'n']:
        return 'Night'
    else:
        return session_str.capitalize()


def check_jackpot_hit(prediction, winning_combo):
    """Check if a single number prediction hits any part of a jackpot winning combination"""
    # Extract all numbers from the winning combination (format: "01-04-35-45-55+03")
    import re
    all_numbers = re.findall(r'\d+', winning_combo)
    
    # Convert prediction to int for comparison
    try:
        pred_int = int(prediction)
        return str(pred_int).zfill(2) in all_numbers or str(pred_int) in all_numbers
    except ValueError:
        return False

# --------------------------------------------------------------------
# COMPREHENSIVE AUDIT EXECUTION
# --------------------------------------------------------------------

def run_comprehensive_audit():
    """Run complete audit comparing all predictions to authoritative data"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE AUDIT v3.7 - APPLES TO APPLES COMPARISON")
    print("="*80)
    
    # Load authoritative results
    auth_df = load_authoritative_master()
    if auth_df is None:
        return
    
    # Find all prediction files
    prediction_files = find_prediction_files()
    if not prediction_files:
        print("[ERROR] No prediction files found!")
        return
    
    # Process each prediction file
    all_results = []
    
    for forecast_file in prediction_files:
        print(f"\n[PROCESSING] {forecast_file}")
        
        predictions_df = load_predictions(forecast_file)
        if predictions_df is None:
            continue
        
        accuracy_results = calculate_accuracy_for_predictions(predictions_df, auth_df)
        all_results.append(accuracy_results)
        
        # Calculate summary for this file
        total_predictions = len(accuracy_results)
        hits = len(accuracy_results[accuracy_results['hit'] == True])
        accuracy_rate = (hits / total_predictions * 100) if total_predictions > 0 else 0
        
        kit_level = accuracy_results['kit_level'].iloc[0] if not accuracy_results.empty else 'Unknown'
        
        print(f"  Kit Level: {kit_level}")
        print(f"  Predictions: {total_predictions}")
        print(f"  Hits: {hits}")
        print(f"  Accuracy: {accuracy_rate:.2f}%")
    
    if not all_results:
        print("[ERROR] No results to analyze!")
        return
    
    # Combine all results
    master_results = pd.concat(all_results, ignore_index=True)
    
    # Generate comprehensive report
    generate_comprehensive_report(master_results, auth_df)

def generate_comprehensive_report(results_df, auth_df):
    """Generate detailed accuracy report"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE ACCURACY REPORT")
    print("="*80)
    
    # Overall statistics
    total_predictions = len(results_df)
    total_hits = len(results_df[results_df['hit'] == True])
    overall_accuracy = (total_hits / total_predictions * 100) if total_predictions > 0 else 0
    
    print(f"Overall Performance:")
    print(f"  Total Predictions: {total_predictions:,}")
    print(f"  Total Hits: {total_hits:,}")
    print(f"  Overall Accuracy: {overall_accuracy:.2f}%")
    
    # Kit level breakdown
    print(f"\nKit Level Performance:")
    for kit in results_df['kit_level'].unique():
        kit_results = results_df[results_df['kit_level'] == kit]
        kit_predictions = len(kit_results)
        kit_hits = len(kit_results[kit_results['hit'] == True])
        kit_accuracy = (kit_hits / kit_predictions * 100) if kit_predictions > 0 else 0
        
        print(f"  {kit}:")
        print(f"    Predictions: {kit_predictions:,}")
        print(f"    Hits: {kit_hits:,}")
        print(f"    Accuracy: {kit_accuracy:.2f}%")
    
    # Game breakdown
    print(f"\nGame Performance:")
    for game in results_df['game'].unique():
        game_results = results_df[results_df['game'] == game]
        game_predictions = len(game_results)
        game_hits = len(game_results[game_results['hit'] == True])
        game_accuracy = (game_hits / game_predictions * 100) if game_predictions > 0 else 0
        
        print(f"  {game}:")
        print(f"    Predictions: {game_predictions:,}")
        print(f"    Hits: {game_hits:,}")
        print(f"    Accuracy: {game_accuracy:.2f}%")
    
    # Save detailed results
    results_file = AUDIT_OUTPUT_DIR / "comprehensive_audit_results.csv"
    results_df.to_csv(results_file, index=False)
    print(f"\n[SAVED] Detailed results: {results_file}")
    
    # Save summary report
    summary_file = AUDIT_OUTPUT_DIR / "accuracy_summary_report.txt"
    with open(summary_file, 'w') as f:
        f.write("COMPREHENSIVE ACCURACY REPORT - APPLES TO APPLES COMPARISON\n")
        f.write("="*80 + "\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Authoritative Data Source: {AUTHORITATIVE_FILE}\n\n")
        
        f.write(f"Overall Performance:\n")
        f.write(f"  Total Predictions: {total_predictions:,}\n")
        f.write(f"  Total Hits: {total_hits:,}\n")
        f.write(f"  Overall Accuracy: {overall_accuracy:.2f}%\n\n")
        
        f.write(f"Kit Level Performance:\n")
        for kit in results_df['kit_level'].unique():
            kit_results = results_df[results_df['kit_level'] == kit]
            kit_predictions = len(kit_results)
            kit_hits = len(kit_results[kit_results['hit'] == True])
            kit_accuracy = (kit_hits / kit_predictions * 100) if kit_predictions > 0 else 0
            
            f.write(f"  {kit}:\n")
            f.write(f"    Predictions: {kit_predictions:,}\n")
            f.write(f"    Hits: {kit_hits:,}\n")
            f.write(f"    Accuracy: {kit_accuracy:.2f}%\n")
        
        f.write(f"\nGame Performance:\n")
        for game in results_df['game'].unique():
            game_results = results_df[results_df['game'] == game]
            game_predictions = len(game_results)
            game_hits = len(game_results[game_results['hit'] == True])
            game_accuracy = (game_hits / game_predictions * 100) if game_predictions > 0 else 0
            
            f.write(f"  {game}:\n")
            f.write(f"    Predictions: {game_predictions:,}\n")
            f.write(f"    Hits: {game_hits:,}\n")
            f.write(f"    Accuracy: {game_accuracy:.2f}%\n")
    
    print(f"[SAVED] Summary report: {summary_file}")
    
    print(f"\n[SUCCESS] Comprehensive audit complete using ONLY authoritative data sources")
    print(f"[RESULT] This is true apples-to-apples comparison for amazing tasting applesauce!")

# --------------------------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------------------------

if __name__ == "__main__":
    run_comprehensive_audit()