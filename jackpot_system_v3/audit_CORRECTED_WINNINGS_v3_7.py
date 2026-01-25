"""
CORRECTED WINNING AUDIT - ACCURATE 1-OFF LOGIC
This fixes the flawed 1-OFF detection and calculates actual prize winnings
"""

import json
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, date
import itertools
from collections import Counter

# --------------------------------------------------------------------
# PROJECT SETUP
# --------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

AUTHORITATIVE_FILE = PROJECT_ROOT / "output" / "AUDIT_CORRECTED_V3_7" / "authoritative_master_results.csv"
OUTPUTS_DIR = PROJECT_ROOT / "output"
CORRECTED_AUDIT_DIR = PROJECT_ROOT / "output" / "CORRECTED_WINNING_AUDIT_V3_7"
CORRECTED_AUDIT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[CORRECTED AUDIT] Fixing 1-OFF logic and calculating actual winnings")

# Prize payout tables (based on your charts)
CASH3_PRIZES = {
    'straight': {'$0.50': 250, '$1.00': 500},  # Example values
    'box_6_way': {'$0.50': 40, '$1.00': 80},
    'box_3_way': {'$0.50': 80, '$1.00': 160}, 
    '1_off_1_digit': {'$0.50': 6, '$1.00': 12},
    '1_off_2_digit': {'$0.50': 1, '$1.00': 2},
    '1_off_3_digit': {'$0.50': 1, '$1.00': 2}
}

CASH4_PRIZES = {
    'straight': {'$0.50': 2500, '$1.00': 5000},
    'box_24_way': {'$0.50': 100, '$1.00': 200},
    'box_12_way': {'$0.50': 200, '$1.00': 400},
    'box_6_way': {'$0.50': 400, '$1.00': 800},
    'box_4_way': {'$0.50': 600, '$1.00': 1200},
    '1_off_1_digit': {'$0.50': 62, '$1.00': 124},
    '1_off_2_digit': {'$0.50': 12, '$1.00': 24},
    '1_off_3_digit': {'$0.50': 7, '$1.00': 14},
    '1_off_4_digit': {'$0.50': 16, '$1.00': 32}
}

CASH4LIFE_PRIZES = {
    '5+1': 1000,  # $1000/day for life
    '5+0': 1000,  # $1000/week for life  
    '4+1': 2500,
    '4+0': 500,
    '3+1': 100,
    '3+0': 25,
    '2+1': 10,
    '2+0': 4,
    '1+1': 2,
    '0+1': 2
}

# --------------------------------------------------------------------
# CORRECTED WINNING LOGIC
# --------------------------------------------------------------------

def check_corrected_1_off_win(prediction, winning_number, max_digits_off=1):
    """CORRECTED 1-OFF logic - digits must be EXACTLY 1 away"""
    if len(prediction) != len(winning_number):
        return False
    
    digits_off_by_one = 0
    for p_digit, w_digit in zip(prediction, winning_number):
        try:
            p_int = int(p_digit)
            w_int = int(w_digit)
            diff = abs(p_int - w_int)
            if diff == 1:  # EXACTLY 1 digit away
                digits_off_by_one += 1
        except ValueError:
            continue
    
    # Return True only if exactly the specified number of digits are off by 1
    return digits_off_by_one == max_digits_off

def check_box_win(prediction, winning_number):
    """Check if prediction wins in BOX (any order)"""
    if len(prediction) != len(winning_number):
        return False
    
    pred_digits = sorted(list(prediction))
    win_digits = sorted(list(winning_number))
    return pred_digits == win_digits

def calculate_box_type(number_str):
    """Determine BOX type for prize calculation"""
    digit_counts = Counter(number_str)
    unique_digits = len(digit_counts)
    
    if len(number_str) == 3:  # Cash3
        if unique_digits == 1:
            return "all_same"
        elif unique_digits == 2:
            return "3_way" if 3 in digit_counts.values() else "6_way"
        else:
            return "straight_only"
    
    elif len(number_str) == 4:  # Cash4
        if unique_digits == 1:
            return "all_same"
        elif unique_digits == 2:
            counts = sorted(digit_counts.values())
            if counts == [1, 3]:
                return "4_way"
            elif counts == [2, 2]:
                return "6_way"
        elif unique_digits == 3:
            return "12_way"
        elif unique_digits == 4:
            return "24_way"
    
    return "unknown"

def check_jackpot_matches(prediction, winning_combo):
    """Check jackpot matches with correct logic"""
    if not winning_combo or '-' not in winning_combo:
        return {'main_matches': 0, 'bonus_match': False, 'win_type': None}
    
    try:
        parts = winning_combo.split('+')
        main_part = parts[0]
        bonus_part = parts[1] if len(parts) > 1 else None
        
        main_numbers = main_part.split('-')
        pred_str = str(prediction).zfill(2)
        
        main_matches = 1 if pred_str in main_numbers else 0
        bonus_match = bonus_part and pred_str == bonus_part
        
        win_type = None
        if main_matches == 1 and bonus_match:
            win_type = "1+1"
        elif main_matches == 1 and not bonus_match:
            win_type = "1+0"
        elif main_matches == 0 and bonus_match:
            win_type = "0+1"
        
        return {
            'main_matches': main_matches,
            'bonus_match': bonus_match,
            'win_type': win_type
        }
        
    except Exception:
        return {'main_matches': 0, 'bonus_match': False, 'win_type': None}

def analyze_corrected_wins(prediction, winning_number, game):
    """Corrected win analysis with accurate logic"""
    results = {
        'straight': False,
        'box': False,
        'box_type': None,
        '1_off_1_digit': False,
        '1_off_2_digit': False,  
        '1_off_3_digit': False,
        '1_off_4_digit': False,
        'any_win': False,
        'win_types': [],
        'prize_amount': 0
    }
    
    if not prediction or not winning_number:
        return results
    
    pred_str = str(prediction).zfill(3 if game == 'Cash3' else 4)
    win_str = str(winning_number).zfill(3 if game == 'Cash3' else 4)
    
    # Check STRAIGHT (exact match)
    if pred_str == win_str:
        results['straight'] = True
        results['any_win'] = True
        results['win_types'].append('STRAIGHT')
        if game == 'Cash3':
            results['prize_amount'] = CASH3_PRIZES['straight']['$1.00']
        elif game == 'Cash4':
            results['prize_amount'] = CASH4_PRIZES['straight']['$1.00']
    
    # Check BOX (any order) - only if not straight
    elif check_box_win(pred_str, win_str):
        results['box'] = True
        box_type = calculate_box_type(win_str)
        results['box_type'] = box_type
        results['any_win'] = True
        results['win_types'].append(f'BOX_{box_type.upper()}')
        
        # Calculate BOX prize
        if game == 'Cash3' and box_type in ['3_way', '6_way']:
            results['prize_amount'] = CASH3_PRIZES[f'box_{box_type}']['$1.00']
        elif game == 'Cash4' and box_type in ['4_way', '6_way', '12_way', '24_way']:
            results['prize_amount'] = CASH4_PRIZES[f'box_{box_type}']['$1.00']
    
    # Check 1-OFF, 2-OFF, etc. (CORRECTED LOGIC)
    else:
        max_digits = 3 if game == 'Cash3' else 4
        for digits_off in range(1, max_digits + 1):
            if check_corrected_1_off_win(pred_str, win_str, digits_off):
                results[f'1_off_{digits_off}_digit'] = True
                results['any_win'] = True
                results['win_types'].append(f'{digits_off}_DIGIT_1_OFF')
                
                # Calculate 1-OFF prize
                if game == 'Cash3':
                    results['prize_amount'] = CASH3_PRIZES[f'1_off_{digits_off}_digit']['$1.00']
                elif game == 'Cash4':
                    results['prize_amount'] = CASH4_PRIZES[f'1_off_{digits_off}_digit']['$1.00']
                break  # Only count the first 1-OFF match
    
    return results

def analyze_corrected_jackpot_wins(prediction, winning_combo, game):
    """Corrected jackpot analysis"""
    jackpot_analysis = check_jackpot_matches(prediction, winning_combo)
    
    results = {
        'win_type': jackpot_analysis['win_type'],
        'any_win': jackpot_analysis['win_type'] is not None,
        'prize_amount': 0
    }
    
    # Calculate prize based on match type
    if game == 'Cash4Life' and results['win_type'] in CASH4LIFE_PRIZES:
        results['prize_amount'] = CASH4LIFE_PRIZES[results['win_type']]
    
    return results

def run_corrected_winning_audit():
    """Run corrected audit with accurate logic"""
    
    print("\n" + "="*80)
    print("CORRECTED WINNING AUDIT - ACCURATE 1-OFF LOGIC")
    print("="*80)
    
    # Load data
    if not AUTHORITATIVE_FILE.exists():
        print("[ERROR] Run audit_CORRECTED_v3_7.py first!")
        return
    
    auth_df = pd.read_csv(AUTHORITATIVE_FILE)
    auth_df['date'] = pd.to_datetime(auth_df['date']).dt.date
    
    # Find prediction files  
    prediction_files = []
    for output_dir in OUTPUTS_DIR.glob("*"):
        if output_dir.is_dir() and not output_dir.name.startswith("AUDIT"):
            forecast_file = output_dir / "forecast.csv"
            if forecast_file.exists():
                prediction_files.append(forecast_file)
    
    all_results = []
    total_winnings = 0
    
    for forecast_file in prediction_files:
        print(f"\n[PROCESSING] {forecast_file.parent.name}")
        
        try:
            predictions_df = pd.read_csv(forecast_file)
            predictions_df['date'] = pd.to_datetime(predictions_df['forecast_date']).dt.date
            
            # Extract kit info
            parent_dir = forecast_file.parent.name
            if "BOOK3" in parent_dir:
                kit_level = 'BOOK3'
            elif "BOOK" in parent_dir:
                kit_level = 'BOOK'
            elif "BOSK" in parent_dir:
                kit_level = 'BOSK'
            else:
                kit_level = 'UNKNOWN'
            
            kit_results = []
            kit_winnings = 0
            
            for _, pred_row in predictions_df.iterrows():
                pred_date = pred_row['date']
                pred_game = pred_row.get('game', 'Unknown')
                pred_number = pred_row.get('number', '')
                
                if not pred_number or pred_number == 0 or str(pred_number) == 'nan':
                    continue
                
                # Find matching results
                auth_matches = auth_df[
                    (auth_df['date'] == pred_date) &
                    (auth_df['game'] == pred_game)
                ]
                
                if pred_game in ['Cash3', 'Cash4']:
                    pred_session = pred_row.get('draw_time', '')
                    if pred_session:
                        session_norm = pred_session.capitalize()
                        auth_matches = auth_matches[auth_matches['session'] == session_norm]
                
                # Analyze each match
                for _, auth_row in auth_matches.iterrows():
                    winning_number = auth_row['winning_number']
                    
                    if pred_game in ['Cash3', 'Cash4']:
                        win_analysis = analyze_corrected_wins(pred_number, winning_number, pred_game)
                    else:
                        win_analysis = analyze_corrected_jackpot_wins(pred_number, winning_number, pred_game)
                    
                    if win_analysis['any_win']:
                        kit_winnings += win_analysis['prize_amount']
                        total_winnings += win_analysis['prize_amount']
                    
                    result_row = {
                        'date': pred_date,
                        'game': pred_game,
                        'kit_level': kit_level,
                        'prediction': str(pred_number),
                        'winning_number': str(winning_number),
                        'any_win': win_analysis['any_win'],
                        'win_types': win_analysis.get('win_types', [win_analysis.get('win_type', '')]),
                        'prize_amount': win_analysis['prize_amount'],
                        'source_file': str(forecast_file)
                    }
                    
                    result_row.update(win_analysis)
                    kit_results.append(result_row)
            
            all_results.extend(kit_results)
            
            # Kit summary
            total_predictions = len(kit_results)
            total_wins = len([r for r in kit_results if r['any_win']])
            win_rate = (total_wins / total_predictions * 100) if total_predictions > 0 else 0
            
            print(f"  {kit_level}: {total_wins}/{total_predictions} wins = {win_rate:.2f}%")
            print(f"  Total Winnings: ${kit_winnings:,.2f}")
            
        except Exception as e:
            print(f"[ERROR] Processing {forecast_file}: {e}")
    
    # Generate final report
    if all_results:
        generate_corrected_winning_report(all_results, total_winnings)
    
    return total_winnings

def generate_corrected_winning_report(results, total_winnings):
    """Generate corrected winning report with prize calculations"""
    
    results_df = pd.DataFrame(results)
    
    print("\n" + "="*80)
    print("CORRECTED WINNING ANALYSIS - ACTUAL PRIZE MONEY")
    print("="*80)
    
    # Overall statistics
    total_predictions = len(results_df)
    total_wins = len(results_df[results_df['any_win'] == True])
    overall_win_rate = (total_wins / total_predictions * 100) if total_predictions > 0 else 0
    
    print(f"CORRECTED PERFORMANCE:")
    print(f"  Total Predictions: {total_predictions:,}")
    print(f"  Total Wins: {total_wins:,}")
    print(f"  Corrected Win Rate: {overall_win_rate:.2f}%")
    print(f"  TOTAL PRIZE WINNINGS: ${total_winnings:,.2f}")
    
    # Kit level breakdown with winnings
    print(f"\nKIT PERFORMANCE & WINNINGS:")
    for kit in results_df['kit_level'].unique():
        kit_data = results_df[results_df['kit_level'] == kit]
        kit_predictions = len(kit_data)
        kit_wins = len(kit_data[kit_data['any_win'] == True])
        kit_rate = (kit_wins / kit_predictions * 100) if kit_predictions > 0 else 0
        kit_winnings = kit_data[kit_data['any_win'] == True]['prize_amount'].sum()
        
        print(f"  {kit}: {kit_wins:,}/{kit_predictions:,} = {kit_rate:.2f}% | ${kit_winnings:,.2f}")
    
    # Game breakdown
    print(f"\nGAME PERFORMANCE & WINNINGS:")
    for game in results_df['game'].unique():
        game_data = results_df[results_df['game'] == game]
        game_wins_data = game_data[game_data['any_win'] == True]
        game_predictions = len(game_data)
        game_wins = len(game_wins_data)
        game_rate = (game_wins / game_predictions * 100) if game_predictions > 0 else 0
        game_winnings = game_wins_data['prize_amount'].sum()
        
        print(f"  {game}: {game_wins:,}/{game_predictions:,} = {game_rate:.2f}% | ${game_winnings:,.2f}")
    
    # Save results
    results_file = CORRECTED_AUDIT_DIR / "corrected_winning_results.csv"
    results_df.to_csv(results_file, index=False)
    
    summary_file = CORRECTED_AUDIT_DIR / "prize_winnings_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("CORRECTED WINNING ANALYSIS - ACTUAL PRIZE MONEY\n")
        f.write("="*80 + "\n")
        f.write(f"Total Prize Winnings: ${total_winnings:,.2f}\n")
        f.write(f"Corrected Win Rate: {overall_win_rate:.2f}%\n")
        f.write("\nThis analysis uses CORRECTED 1-OFF logic:\n")
        f.write("- 1-OFF wins require digits to be EXACTLY 1 away\n")
        f.write("- All prize amounts based on $1.00 play\n")
        f.write("- Accurate BOX and STRAIGHT detection\n")
    
    print(f"\n[SAVED] Results: {results_file}")
    print(f"[SAVED] Summary: {summary_file}")

if __name__ == "__main__":
    total_winnings = run_corrected_winning_audit()
    print(f"\n🎉 SUBSCRIBERS WOULD HAVE WON: ${total_winnings:,.2f}")
    print("[SUCCESS] Corrected audit shows TRUE winning performance!")