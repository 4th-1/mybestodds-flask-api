"""
Comprehensive Audit System v3.7 for My Best Odds
Validates 3,202 test subscriber predictions against actual Georgia Lottery results
Generates app-ready JSON outputs for Base44 frontend integration
"""

import os
import sys
import json
import pandas as pd
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import PyPDF2

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# ============================================================================
# PDF PARSER - Extract winning numbers from Georgia Lottery PDF files
# ============================================================================

def parse_ga_lottery_pdf(pdf_path):
    """Extract winning numbers from Georgia Lottery PDF"""
    print(f"Parsing PDF: {pdf_path}")
    results = []
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                
                # Look for date patterns: MM/DD/YYYY
                date_pattern = r'(\d{2}/\d{2}/\d{4})'
                # Look for time patterns: Midday, Evening, Night
                time_pattern = r'(Midday|Evening|Night)'
                # Look for number patterns: 3 or 4 digits
                number_pattern = r'\b(\d{3,4})\b'
                
                lines = text.split('\n')
                current_date = None
                
                for i, line in enumerate(lines):
                    # Check for date
                    date_match = re.search(date_pattern, line)
                    if date_match:
                        date_str = date_match.group(1)
                        current_date = datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
                    
                    # Check for session and numbers
                    time_match = re.search(time_pattern, line, re.IGNORECASE)
                    if time_match and current_date:
                        session = time_match.group(1).upper()
                        
                        # Extract numbers from this line and nearby lines
                        numbers = re.findall(number_pattern, line)
                        
                        # Check next few lines for numbers if not found
                        if not numbers and i + 1 < len(lines):
                            numbers = re.findall(number_pattern, lines[i + 1])
                        
                        if numbers:
                            # Filter for valid Cash3 (3 digits) or Cash4 (4 digits)
                            for num in numbers:
                                if len(num) in [3, 4]:
                                    game = 'Cash3' if len(num) == 3 else 'Cash4'
                                    results.append({
                                        'date': current_date,
                                        'game': game,
                                        'session': session,
                                        'winning_number': num
                                    })
                                    break  # Take first valid number per session
        
        print(f"  Extracted {len(results)} draws from PDF")
        return results
        
    except Exception as e:
        print(f"  ERROR parsing PDF: {e}")
        return []


# ============================================================================
# HISTORICAL DATA CONSOLIDATION
# ============================================================================

def load_all_historical_data():
    """Load and consolidate all historical data sources"""
    print("\n" + "="*80)
    print("LOADING HISTORICAL DATA")
    print("="*80)
    
    all_results = []
    
    # 1. Load Cash3 Jan-Aug TXT file
    cash3_jan_aug = os.path.join(PROJECT_ROOT, 'data', 'results', 'ga_results', 'Cash3_2025 Jan-Aug 2025.txt')
    if os.path.exists(cash3_jan_aug):
        print(f"\n1. Loading Cash3 Jan-Aug from: {cash3_jan_aug}")
        try:
            # Try multiple encodings
            for encoding in ['utf-16', 'latin-1', 'cp1252', 'utf-8']:
                try:
                    with open(cash3_jan_aug, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # Has data
                            for line in lines[1:]:  # Skip header
                                parts = line.strip().split('\t')
                                if len(parts) >= 4:
                                    date_str = parts[1].strip()
                                    session = parts[2].strip().upper()
                                    number = parts[3].strip()
                                    
                                    # Parse date
                                    try:
                                        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                                        date_iso = date_obj.strftime('%Y-%m-%d')
                                        
                                        all_results.append({
                                            'date': date_iso,
                                            'game': 'Cash3',
                                            'session': session,
                                            'winning_number': number
                                        })
                                    except:
                                        continue
                            print(f"  Loaded {len([r for r in all_results if r['game'] == 'Cash3'])} Cash3 draws (encoding: {encoding})")
                            break
                except:
                    continue
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # 2. Load Cash4 Jan-Aug TXT file
    cash4_jan_aug = os.path.join(PROJECT_ROOT, 'data', 'results', 'ga_results', 'Cash4 Jan_Aug2025.txt')
    if os.path.exists(cash4_jan_aug):
        print(f"\n2. Loading Cash4 Jan-Aug from: {cash4_jan_aug}")
        try:
            # Try multiple encodings
            for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
                try:
                    with open(cash4_jan_aug, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # Has data
                            for line in lines[1:]:  # Skip header
                                parts = line.strip().split('\t')
                                if len(parts) >= 4:
                                    date_str = parts[1].strip()
                                    session = parts[2].strip().upper()
                                    number = parts[3].strip()
                                    
                                    # Parse date
                                    try:
                                        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                                        date_iso = date_obj.strftime('%Y-%m-%d')
                                        
                                        all_results.append({
                                            'date': date_iso,
                                            'game': 'Cash4',
                                            'session': session,
                                            'winning_number': number
                                        })
                                    except:
                                        continue
                            print(f"  Loaded {len([r for r in all_results if r['game'] == 'Cash4'])} Cash4 draws (encoding: {encoding})")
                            break
                except:
                    continue
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # 3. Load Cash3 Sep-Nov CSV
    cash3_csv = os.path.join(PROJECT_ROOT, 'data', 'results', 'ga_results', 'cash3_results.csv')
    if os.path.exists(cash3_csv):
        print(f"\n3. Loading Cash3 Sep-Nov from: {cash3_csv}")
        try:
            df = pd.read_csv(cash3_csv)
            # Handle different column name formats
            date_col = 'draw_date' if 'draw_date' in df.columns else 'Draw Date'
            time_col = 'session' if 'session' in df.columns else 'Time'
            num_col = 'digits' if 'digits' in df.columns else 'Winning Numbers'
            
            for _, row in df.iterrows():
                date_obj = pd.to_datetime(row[date_col])
                all_results.append({
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'game': 'Cash3',
                    'session': str(row[time_col]).upper(),
                    'winning_number': str(row[num_col])
                })
            print(f"  Loaded {len(df)} Cash3 draws")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # 4. Load Cash4 Sep-Nov CSV
    cash4_csv = os.path.join(PROJECT_ROOT, 'data', 'results', 'ga_results', 'cash4_results.csv')
    if os.path.exists(cash4_csv):
        print(f"\n4. Loading Cash4 Sep-Nov from: {cash4_csv}")
        try:
            df = pd.read_csv(cash4_csv)
            # Handle different column name formats
            date_col = 'draw_date' if 'draw_date' in df.columns else 'Draw Date'
            time_col = 'session' if 'session' in df.columns else 'Time'
            num_col = 'digits' if 'digits' in df.columns else 'Winning Numbers'
            
            for _, row in df.iterrows():
                date_obj = pd.to_datetime(row[date_col])
                all_results.append({
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'game': 'Cash4',
                    'session': str(row[time_col]).upper(),
                    'winning_number': str(row[num_col])
                })
            print(f"  Loaded {len(df)} Cash4 draws")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # 5. Load PDF files for Nov 11 - Dec 1
    pdf_files = [
        ('GA_Lottery_WinningNumbers (54).PDF', 'Cash4'),
        ('GA_Lottery_WinningNumbers (55).PDF', 'Cash3'),
        ('GA_Lottery_WinningNumbers (58).PDF', 'Cash4'),
        ('GA_Lottery_WinningNumbers (59).PDF', 'Cash4')
    ]
    
    pdf_base_path = r'C:\Users\suppo\Downloads'
    print(f"\n5. Loading PDF files from: {pdf_base_path}")
    
    for pdf_file, expected_game in pdf_files:
        pdf_path = os.path.join(pdf_base_path, pdf_file)
        if os.path.exists(pdf_path):
            pdf_results = parse_ga_lottery_pdf(pdf_path)
            all_results.extend(pdf_results)
    
    # Convert to DataFrame and deduplicate
    df_all = pd.DataFrame(all_results)
    
    if len(df_all) == 0:
        print("\nERROR: No historical data loaded!")
        return pd.DataFrame()
    
    # Deduplicate based on date + game + session
    original_count = len(df_all)
    df_all = df_all.drop_duplicates(subset=['date', 'game', 'session'], keep='first')
    
    print(f"\n" + "="*80)
    print(f"CONSOLIDATION COMPLETE")
    print(f"  Original records: {original_count}")
    print(f"  After deduplication: {len(df_all)}")
    print(f"  Date range: {df_all['date'].min()} to {df_all['date'].max()}")
    print(f"  Cash3 draws: {len(df_all[df_all['game'] == 'Cash3'])}")
    print(f"  Cash4 draws: {len(df_all[df_all['game'] == 'Cash4'])}")
    print("="*80)
    
    return df_all


# ============================================================================
# PREDICTION LOADING
# ============================================================================
def load_subscriber_predictions(kit, subscriber_id):
    """Load all predictions for a subscriber from generated output JSON files."""
    predictions = []

    outputs_dir = os.path.join(PROJECT_ROOT, 'outputs')

    # Normalize kit names so *_TEST subscribers match production-style output folders
    kit_name = kit.replace('_TEST', '')
    pattern = f'{kit_name}_{subscriber_id}_*'

    matching_dirs = sorted(Path(outputs_dir).glob(pattern))

    # Fastest-path fallback: if BOSK per-subscriber folders are empty/missing,
    # consume the shared BOSK_TS payload so audits can run without regeneration.
    if kit_name == 'BOSK':
        matching_dirs = [d for d in matching_dirs if any(d.glob('*.json'))]
        if not matching_dirs:
            bosk_ts_dir = Path(outputs_dir) / 'BOSK_TS_1900-01-01_to_2100-12-31'
            if bosk_ts_dir.exists():
                matching_dirs = [bosk_ts_dir]

    if not matching_dirs:
        return predictions

    # Prefer the most recently modified directory if multiple exist
    output_dir = max(matching_dirs, key=lambda p: p.stat().st_mtime)

    # Load all JSON files in the date directory
    for json_file in sorted(output_dir.glob('*.json')):
        if json_file.name == 'summary.json':
            continue

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
        except Exception:
            continue

        date_str = json_file.stem  # e.g., 2025-01-01

        # -----------------------------
        # Handle "picks" style payloads
        # -----------------------------
        picks = data.get('picks')
        if isinstance(picks, dict):
            for game, game_payload in picks.items():
                if not isinstance(game_payload, dict):
                    continue

                for pick_list in game_payload.values():
                    if not isinstance(pick_list, list):
                        continue

                    for entry in pick_list:
                        number = entry.get('number') if isinstance(entry, dict) else entry
                        if number is None:
                            continue

                        sessions = ['MIDDAY', 'EVENING', 'NIGHT'] if game in ['Cash3', 'Cash4'] else ['N/A']
                        for session in sessions:
                            predictions.append({
                                'subscriber_id': subscriber_id,
                                'kit': kit,
                                'date': date_str,
                                'game': game,
                                'session': session,
                                'predicted_number': str(number),
                                'confidence': entry.get('confidence', data.get('score', 0)) if isinstance(entry, dict) else data.get('score', 0),
                                'odds': entry.get('odds', 0) if isinstance(entry, dict) else 0,
                                'band': entry.get('band', data.get('band', 'UNKNOWN')) if isinstance(entry, dict) else data.get('band', 'UNKNOWN'),
                                'play_type': entry.get('play_type', 'STRAIGHT') if isinstance(entry, dict) else 'STRAIGHT'
                            })

        # -------------------------------
        # Handle flat "predictions" list
        # -------------------------------
        flat_predictions = data.get('predictions')
        if isinstance(flat_predictions, list):
            for prediction in flat_predictions:
                if not isinstance(prediction, dict):
                    continue

                game = prediction.get('game')
                if not game:
                    continue

                session = prediction.get('session')
                if not session and game in ['Cash3', 'Cash4']:
                    session = 'EVENING'

                number = prediction.get('number') or prediction.get('digits')
                if not number:
                    continue

                predictions.append({
                    'subscriber_id': subscriber_id,
                    'kit': kit,
                    'date': date_str,
                    'game': game,
                    'session': session if session else 'N/A',
                    'predicted_number': str(number),
                    'confidence': prediction.get('confidence', data.get('score', 0)),
                    'odds': prediction.get('odds', 0),
                    'band': prediction.get('band', data.get('band', 'UNKNOWN')),
                    'play_type': prediction.get('play_type', 'STRAIGHT')
                })

    return predictions


# ============================================================================
# MISSING OUTPUT CHECKER
# ============================================================================
def report_missing_outputs(kits):
    """Report subscribers that lack generated output folders."""
    outputs_dir = Path(PROJECT_ROOT) / 'outputs'
    missing = defaultdict(list)

    for kit in kits:
        kit_name = kit.replace('_TEST', '')
        subscriber_dir = Path(PROJECT_ROOT) / 'data' / 'subscribers' / kit
        if not subscriber_dir.exists():
            print(f"WARNING: subscriber directory not found for {kit}")
            continue

        for sub_file in subscriber_dir.glob('*.json'):
            subscriber_id = sub_file.stem
            pattern = f"{kit_name}_{subscriber_id}_*"
            matches = list(outputs_dir.glob(pattern))
            # Also treat empty folders as missing so audits flag subscribers with no payloads
            has_payload = any(True for m in matches for _ in m.glob('*.json'))
            if not matches or not has_payload:
                missing[kit_name].append(subscriber_id)

    total_missing = sum(len(v) for v in missing.values())
    if total_missing == 0:
        print("All subscribers have output folders present.")
        return

    print("Missing outputs detected:")
    for kit_name, subs in missing.items():
        print(f"  {kit_name}: {len(subs)} missing")
    # Optionally list a few samples to guide regeneration
    for kit_name, subs in missing.items():
        sample = ', '.join(subs[:5])
        if sample:
            print(f"    Sample {kit_name} missing IDs: {sample}{' ...' if len(subs) > 5 else ''}")


# ============================================================================
# LOTTERY WINNING LOGIC
# ============================================================================

def check_cash3_win(predicted, actual, play_type='STRAIGHT'):
    """Check if Cash3 prediction is a winner based on play type"""
    pred_digits = [d for d in str(predicted)]
    actual_digits = [d for d in str(actual)]
    
    if len(pred_digits) != 3 or len(actual_digits) != 3:
        return None, 0
    
    wins = []
    
    # STRAIGHT - exact order
    if predicted == actual:
        wins.append('STRAIGHT')
    
    # BOX - any order
    if sorted(pred_digits) == sorted(actual_digits):
        wins.append('BOX')
    
    # PAIRS
    if pred_digits[0] == actual_digits[0] and pred_digits[1] == actual_digits[1]:
        wins.append('FRONT_PAIR')
    if pred_digits[1] == actual_digits[1] and pred_digits[2] == actual_digits[2]:
        wins.append('BACK_PAIR')
    
    # 1-OFF - one digit off in each position
    one_off = all(
        abs(int(pred_digits[i]) - int(actual_digits[i])) <= 1
        for i in range(3)
    )
    if one_off and predicted != actual:
        wins.append('1-OFF')
    
    # Determine payout multiplier (example values)
    payout = 0
    if 'STRAIGHT' in wins:
        payout = 500  # $0.50 bet = $250, $1 bet = $500
    elif 'BOX' in wins:
        # 3-way box or 6-way box
        unique = len(set(pred_digits))
        payout = 160 if unique == 2 else 80
    elif 'FRONT_PAIR' in wins or 'BACK_PAIR' in wins:
        payout = 50
    elif '1-OFF' in wins:
        payout = 9
    
    return wins, payout


def check_cash4_win(predicted, actual, play_type='STRAIGHT'):
    """Check if Cash4 prediction is a winner based on play type"""
    pred_digits = [d for d in str(predicted)]
    actual_digits = [d for d in str(actual)]
    
    if len(pred_digits) != 4 or len(actual_digits) != 4:
        return None, 0
    
    wins = []
    
    # STRAIGHT - exact order
    if predicted == actual:
        wins.append('STRAIGHT')
    
    # BOX - any order
    if sorted(pred_digits) == sorted(actual_digits):
        wins.append('BOX')
    
    # 1-OFF - one digit off in each position
    one_off = all(
        abs(int(pred_digits[i]) - int(actual_digits[i])) <= 1
        for i in range(4)
    )
    if one_off and predicted != actual:
        wins.append('1-OFF')
    
    # Determine payout multiplier
    payout = 0
    if 'STRAIGHT' in wins:
        payout = 5000  # $0.50 bet = $2,500, $1 bet = $5,000
    elif 'BOX' in wins:
        # 24-way, 12-way, 6-way, or 4-way
        unique = len(set(pred_digits))
        if unique == 4:
            payout = 200  # 24-way box
        elif unique == 3:
            payout = 400  # 12-way box
        elif unique == 2:
            payout = 800  # 6-way box
        else:
            payout = 1200  # 4-way box
    elif '1-OFF' in wins:
        payout = 18
    
    return wins, payout


def check_jackpot_win(predicted, actual, game):
    """Check jackpot game wins (MegaMillions, Powerball, Cash4Life)"""
    # Parse predicted numbers
    pred_parts = predicted.split('+')
    if len(pred_parts) != 2:
        return None, 0
    
    pred_main = set(pred_parts[0].strip().split())
    pred_bonus = pred_parts[1].strip()
    
    # Parse actual numbers
    actual_parts = actual.split('+')
    if len(actual_parts) != 2:
        return None, 0
    
    actual_main = set(actual_parts[0].strip().split())
    actual_bonus = actual_parts[1].strip()
    
    # Count matches
    main_matches = len(pred_main & actual_main)
    bonus_match = (pred_bonus == actual_bonus)
    
    # Determine prize tier (example payouts)
    wins = []
    payout = 0
    
    if game in ['MegaMillions', 'Powerball']:
        if main_matches == 5 and bonus_match:
            wins.append('JACKPOT')
            payout = 1000000  # Placeholder for jackpot
        elif main_matches == 5:
            wins.append('SECOND_PRIZE')
            payout = 1000000
        elif main_matches == 4 and bonus_match:
            wins.append('THIRD_PRIZE')
            payout = 10000
        elif main_matches == 4:
            wins.append('FOURTH_PRIZE')
            payout = 500
        elif main_matches == 3 and bonus_match:
            wins.append('FIFTH_PRIZE')
            payout = 200
        elif main_matches == 3:
            wins.append('SIXTH_PRIZE')
            payout = 10
        elif main_matches == 2 and bonus_match:
            wins.append('SEVENTH_PRIZE')
            payout = 10
        elif main_matches == 1 and bonus_match:
            wins.append('EIGHTH_PRIZE')
            payout = 4
        elif bonus_match:
            wins.append('BONUS_ONLY')
            payout = 2
    
    elif game == 'Cash4Life':
        if main_matches == 5 and bonus_match:
            wins.append('TOP_PRIZE')
            payout = 1000  # $1000/day for life
        elif main_matches == 5:
            wins.append('SECOND_PRIZE')
            payout = 1000  # $1000/week for life
        elif main_matches == 4 and bonus_match:
            wins.append('THIRD_PRIZE')
            payout = 2500
        elif main_matches == 4:
            wins.append('FOURTH_PRIZE')
            payout = 500
        elif main_matches == 3 and bonus_match:
            wins.append('FIFTH_PRIZE')
            payout = 100
        elif main_matches == 3:
            wins.append('SIXTH_PRIZE')
            payout = 25
        elif main_matches == 2 and bonus_match:
            wins.append('SEVENTH_PRIZE')
            payout = 10
        elif main_matches == 2:
            wins.append('EIGHTH_PRIZE')
            payout = 4
        elif main_matches == 1 and bonus_match:
            wins.append('NINTH_PRIZE')
            payout = 2
    
    return wins, payout


# ============================================================================
# AUDIT ENGINE
# ============================================================================

def audit_subscriber(subscriber_id, kit, historical_df):
    """Audit a single subscriber's predictions with proper lottery winning logic"""
    
    # Load predictions
    predictions = load_subscriber_predictions(kit, subscriber_id)
    
    if not predictions:
        return None
    
    # Filter BOSK to only Cash3/Cash4
    if kit == 'BOSK':
        predictions = [p for p in predictions if p['game'] in ['Cash3', 'Cash4']]
    
    results = {
        'subscriber_id': subscriber_id,
        'kit': kit,
        'total_predictions': len(predictions),
        'by_game': {},
        'by_confidence_band': {},
        'by_play_type': {},
        'wins': 0,
        'win_breakdown': {},
        'total_payout': 0,
        'misses': 0,
        'win_rate': 0.0,
        'avg_confidence': 0.0,
        'roi': 0.0,
        'daily_performance': []
    }
    
    # Match predictions to actual results
    for pred in predictions:
        game = pred['game']
        date = pred['date']
        session = pred.get('session', 'EVENING')
        predicted_num = str(pred['predicted_number'])
        play_type = pred.get('play_type', 'STRAIGHT')
        
        # Find actual result
        if game in ['Cash3', 'Cash4']:
            match = historical_df[
                (historical_df['date'] == date) &
                (historical_df['game'] == game) &
                (historical_df['session'] == session)
            ]
        else:
            # Jackpot games don't have sessions
            match = historical_df[
                (historical_df['date'] == date) &
                (historical_df['game'] == game)
            ]
        
        if len(match) > 0:
            actual_num = str(match.iloc[0]['winning_number'])
            
            # Check for wins based on game type
            if game == 'Cash3':
                wins, payout = check_cash3_win(predicted_num, actual_num, play_type)
            elif game == 'Cash4':
                wins, payout = check_cash4_win(predicted_num, actual_num, play_type)
            elif game in ['MegaMillions', 'Powerball', 'Cash4Life']:
                wins, payout = check_jackpot_win(predicted_num, actual_num, game)
            else:
                wins, payout = None, 0
            
            # Record results
            if wins and len(wins) > 0:
                pred['result'] = 'WIN'
                pred['win_types'] = wins
                pred['payout'] = payout
                results['wins'] += 1
                results['total_payout'] += payout
                
                # Track win breakdown
                for win_type in wins:
                    if win_type not in results['win_breakdown']:
                        results['win_breakdown'][win_type] = 0
                    results['win_breakdown'][win_type] += 1
            else:
                pred['result'] = 'MISS'
                pred['win_types'] = []
                pred['payout'] = 0
                results['misses'] += 1
            
            pred['actual_number'] = actual_num
        else:
            pred['result'] = 'NO_DRAW'
            pred['actual_number'] = None
            pred['win_types'] = []
            pred['payout'] = 0
    
    # Calculate statistics
    total_with_result = results['wins'] + results['misses']
    if total_with_result > 0:
        results['win_rate'] = (results['wins'] / total_with_result) * 100
    
    # Calculate ROI (assuming $1 per bet)
    total_spent = len([p for p in predictions if p.get('result') != 'NO_DRAW'])
    results['roi'] = ((results['total_payout'] - total_spent) / total_spent * 100) if total_spent > 0 else 0
    
    # Group by game
    for pred in predictions:
        game = pred['game']
        if game not in results['by_game']:
            results['by_game'][game] = {
                'total': 0,
                'wins': 0,
                'misses': 0,
                'total_payout': 0,
                'win_rate': 0.0,
                'roi': 0.0
            }
        
        results['by_game'][game]['total'] += 1
        if pred.get('result') == 'WIN':
            results['by_game'][game]['wins'] += 1
            results['by_game'][game]['total_payout'] += pred.get('payout', 0)
        elif pred.get('result') == 'MISS':
            results['by_game'][game]['misses'] += 1
    
    # Calculate win rates and ROI by game
    for game_stats in results['by_game'].values():
        total = game_stats['wins'] + game_stats['misses']
        if total > 0:
            game_stats['win_rate'] = (game_stats['wins'] / total) * 100
            game_stats['roi'] = ((game_stats['total_payout'] - total) / total * 100)
    
    # Group by confidence band
    for pred in predictions:
        band = pred.get('band', 'UNKNOWN')
        if band not in results['by_confidence_band']:
            results['by_confidence_band'][band] = {
                'total': 0,
                'wins': 0,
                'total_payout': 0,
                'win_rate': 0.0
            }
        
        results['by_confidence_band'][band]['total'] += 1
        if pred.get('result') == 'WIN':
            results['by_confidence_band'][band]['wins'] += 1
            results['by_confidence_band'][band]['total_payout'] += pred.get('payout', 0)
    
    # Calculate win rates by band
    for band_stats in results['by_confidence_band'].values():
        if band_stats['total'] > 0:
            band_stats['win_rate'] = (band_stats['wins'] / band_stats['total']) * 100
    
    # Average confidence
    confidences = [p['confidence'] for p in predictions if p.get('confidence')]
    if confidences:
        results['avg_confidence'] = sum(confidences) / len(confidences)
    
    return results


def run_full_audit(kits=None):
    """Run comprehensive audit across the provided test subscribers"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE AUDIT v3.7 - My Best Odds")
    print("="*80)

    # Pre-flight: report any missing forecast outputs
    kits = kits or ['BOOK3_TEST', 'BOOK_TEST', 'BOSK_TEST']
    print("\nChecking for missing outputs before audit...")
    report_missing_outputs(kits)
    
    # Load historical data
    historical_df = load_all_historical_data()
    
    if len(historical_df) == 0:
        print("ERROR: No historical data available for audit")
        return
    
    # Get all test subscribers
    all_audit_results = []
    
    for kit in kits:
        kit_name = kit.replace('_TEST', '')
        subscriber_dir = os.path.join(PROJECT_ROOT, 'data', 'subscribers', kit)
        
        if not os.path.exists(subscriber_dir):
            print(f"\nWARNING: No subscriber directory found for {kit}")
            continue
        
        print(f"\n{'='*80}")
        print(f"AUDITING {kit_name} SUBSCRIBERS")
        print(f"{'='*80}")
        
        subscriber_files = list(Path(subscriber_dir).glob('*.json'))
        total_subscribers = len(subscriber_files)
        
        print(f"Found {total_subscribers} subscribers to audit")
        
        for idx, sub_file in enumerate(subscriber_files, 1):
            subscriber_id = sub_file.stem
            
            if idx % 100 == 0:
                print(f"  Progress: {idx}/{total_subscribers} subscribers audited")
            
            audit_result = audit_subscriber(subscriber_id, kit_name, historical_df)
            
            if audit_result:
                all_audit_results.append(audit_result)
    
    # Save individual subscriber audit results
    output_dir = os.path.join(PROJECT_ROOT, 'audit_results')
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*80}")
    print("SAVING AUDIT RESULTS")
    print(f"{'='*80}")
    
    # 1. Individual subscriber results
    for result in all_audit_results:
        kit = result['kit']
        sub_id = result['subscriber_id']
        
        kit_dir = os.path.join(output_dir, 'by_subscriber', kit)
        os.makedirs(kit_dir, exist_ok=True)
        
        output_file = os.path.join(kit_dir, f'{sub_id}_audit.json')
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    print(f"  Saved {len(all_audit_results)} subscriber audit files")
    
    # 2. KIT-level aggregates
    kit_aggregates = {}
    for kit_name in ['BOOK3', 'BOOK', 'BOSK']:
        kit_results = [r for r in all_audit_results if r['kit'] == kit_name]
        
        if not kit_results:
            continue
        
        kit_aggregates[kit_name] = {
            'total_subscribers': len(kit_results),
            'total_predictions': sum(r['total_predictions'] for r in kit_results),
            'total_wins': sum(r['wins'] for r in kit_results),
            'total_misses': sum(r['misses'] for r in kit_results),
            'total_payout': sum(r['total_payout'] for r in kit_results),
            'avg_win_rate': sum(r['win_rate'] for r in kit_results) / len(kit_results) if kit_results else 0,
            'avg_confidence': sum(r['avg_confidence'] for r in kit_results) / len(kit_results) if kit_results else 0,
            'avg_roi': sum(r['roi'] for r in kit_results) / len(kit_results) if kit_results else 0,
            'by_game': {},
            'by_confidence_band': {},
            'win_breakdown': {}
        }
        
        # Aggregate by game
        all_games = set()
        for r in kit_results:
            all_games.update(r['by_game'].keys())
        
        for game in all_games:
            game_data = [r['by_game'].get(game, {}) for r in kit_results if game in r['by_game']]
            if game_data:
                kit_aggregates[kit_name]['by_game'][game] = {
                    'total_predictions': sum(g.get('total', 0) for g in game_data),
                    'wins': sum(g.get('wins', 0) for g in game_data),
                    'misses': sum(g.get('misses', 0) for g in game_data),
                    'total_payout': sum(g.get('total_payout', 0) for g in game_data),
                    'avg_win_rate': sum(g.get('win_rate', 0) for g in game_data) / len(game_data),
                    'avg_roi': sum(g.get('roi', 0) for g in game_data) / len(game_data)
                }
    
    # Save KIT aggregates
    kit_output_file = os.path.join(output_dir, 'kit_aggregates.json')
    with open(kit_output_file, 'w') as f:
        json.dump(kit_aggregates, f, indent=2)
    
    print(f"  Saved KIT aggregate statistics")
    
    # 3. Overall summary
    summary = {
        'audit_date': datetime.now().isoformat(),
        'test_period': {
            'start': '2025-01-01',
            'end': '2025-12-01'
        },
        'total_subscribers': len(all_audit_results),
        'total_predictions': sum(r['total_predictions'] for r in all_audit_results),
        'total_wins': sum(r['wins'] for r in all_audit_results),
        'total_misses': sum(r['misses'] for r in all_audit_results),
        'total_payout': sum(r['total_payout'] for r in all_audit_results),
        'overall_win_rate': 0.0,
        'overall_roi': 0.0,
        'by_kit': kit_aggregates
    }
    
    total_with_result = summary['total_wins'] + summary['total_misses']
    if total_with_result > 0:
        summary['overall_win_rate'] = (summary['total_wins'] / total_with_result) * 100
        summary['overall_roi'] = ((summary['total_payout'] - total_with_result) / total_with_result * 100)
    
    summary_file = os.path.join(output_dir, 'audit_summary.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"  Saved overall audit summary")
    
    # Print summary to console
    print(f"\n{'='*80}")
    print("AUDIT SUMMARY - LOTTERY WINNING ANALYSIS")
    print(f"{'='*80}")
    print(f"Total Subscribers: {summary['total_subscribers']}")
    print(f"Total Predictions: {summary['total_predictions']:,}")
    print(f"Total Wins (all types): {summary['total_wins']:,}")
    print(f"Total Misses: {summary['total_misses']:,}")
    print(f"Total Payout: ${summary['total_payout']:,.2f}")
    print(f"Overall Win Rate: {summary['overall_win_rate']:.2f}%")
    print(f"Overall ROI: {summary['overall_roi']:.2f}%")
    print(f"\nBy KIT:")
    for kit_name, kit_data in kit_aggregates.items():
        print(f"  {kit_name}:")
        print(f"    Subscribers: {kit_data['total_subscribers']}")
        print(f"    Predictions: {kit_data['total_predictions']:,}")
        print(f"    Wins: {kit_data['total_wins']:,}")
        print(f"    Total Payout: ${kit_data['total_payout']:,.2f}")
        print(f"    Avg Win Rate: {kit_data['avg_win_rate']:.2f}%")
        print(f"    Avg ROI: {kit_data['avg_roi']:.2f}%")
    
    print(f"\n{'='*80}")
    print(f"AUDIT COMPLETE - Results saved to: {output_dir}")
    print(f"{'='*80}")


if __name__ == '__main__':
    run_full_audit()
