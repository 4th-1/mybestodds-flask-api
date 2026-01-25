"""
Comprehensive results analyzer for 1000 test subscriber validation.
Analyzes predictions against actual winning numbers and system performance.
"""
import os
import sys
import json
import pandas as pd
import glob
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def load_actual_results():
    """Load actual winning numbers for validation period: Jan 1, 2025 - Nov 10, 2025."""
    results = {}
    validation_start = datetime(2025, 1, 1)
    validation_end = datetime(2025, 11, 10)
    
    # Target games for validation
    target_games = ["Cash3", "Cash4", "Powerball", "Cash4Life", "MegaMillions"]
    
    # Load Georgia Cash3 and Cash4 results
    ga_files = {
        "Cash3": "data/results/ga_results/cash3_results.csv",
        "Cash4": "data/results/ga_results/cash4_results.csv"
    }
    
    for game, file_path in ga_files.items():
        try:
            df = pd.read_csv(file_path)
            for _, row in df.iterrows():
                date_str = row.get('draw_date', '')
                if not date_str:
                    continue
                    
                # Parse date (format: M/D/YYYY)
                try:
                    date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                    
                    # Filter to validation period only
                    if not (validation_start <= date_obj <= validation_end):
                        continue
                    
                    date_key = date_obj.strftime('%Y-%m-%d')
                    
                    # Get winning number from 'digits' column
                    winning_number = str(row.get('digits', '')).strip()
                    
                    if winning_number:
                        if date_key not in results:
                            results[date_key] = {}
                        
                        # Create session-specific key for Cash3/Cash4 (MIDDAY/NIGHT)
                        session = row.get('session', 'MIDDAY').upper()
                        game_key = f"{game}_{session}" if session in ['MIDDAY', 'NIGHT'] else game
                        results[date_key][game_key] = winning_number
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Warning: Could not load {file_path}: {e}")
    
    # Load Jackpot game results
    jackpot_files = {
        "MegaMillions": "data/results/jackpot_results/MegaMillions.csv",
        "Powerball": "data/results/jackpot_results/Powerball.csv", 
        "Cash4Life": "data/results/jackpot_results/Cash4Life.csv"
    }
    
    for game, file_path in jackpot_files.items():
        try:
            df = pd.read_csv(file_path)
            for _, row in df.iterrows():
                date_str = row.get('date', '')
                if not date_str:
                    continue
                    
                # Parse date (format: YYYY-MM-DD)
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Filter to validation period only
                    if not (validation_start <= date_obj <= validation_end):
                        continue
                    
                    date_key = date_obj.strftime('%Y-%m-%d')
                    
                    # Construct winning number from columns
                    if game == "MegaMillions":
                        winning_number = f"{row['n1']}-{row['n2']}-{row['n3']}-{row['n4']}-{row['n5']} MB:{row['bonus']}"
                    elif game == "Powerball":
                        winning_number = f"{row['n1']}-{row['n2']}-{row['n3']}-{row['n4']}-{row['n5']} PB:{row['bonus']}"
                    elif game == "Cash4Life":
                        winning_number = f"{row['n1']}-{row['n2']}-{row['n3']}-{row['n4']}-{row['n5']} CB:{row['bonus']}"
                    
                    if winning_number:
                        if date_key not in results:
                            results[date_key] = {}
                        results[date_key][game] = winning_number
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Warning: Could not load {file_path}: {e}")
    
    print(f"📅 Loaded results for {len(results)} dates from {validation_start.strftime('%Y-%m-%d')} to {validation_end.strftime('%Y-%m-%d')}")
    
    # Print game coverage summary
    game_counts = defaultdict(int)
    for date_data in results.values():
        for game_key in date_data.keys():
            base_game = game_key.split('_')[0]  # Remove session suffix
            game_counts[base_game] += 1
    
    print("🎮 Game coverage in validation period:")
    for game in target_games:
        count = game_counts.get(game, 0)
        print(f"   {game}: {count} draws")
        
        # Show sessions for Cash games
        if game in ["Cash3", "Cash4"]:
            midday_count = sum(1 for d in results.values() if f"{game}_MIDDAY" in d)
            night_count = sum(1 for d in results.values() if f"{game}_NIGHT" in d)
            print(f"     - MIDDAY: {midday_count} draws")
            print(f"     - NIGHT: {night_count} draws")
    
    return results

def analyze_prediction_file(file_path):
    """Analyze a single prediction file."""
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            predictions = data.get('predictions', [])
            subscriber_id = data.get('subscriber_id', 'unknown')
            
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            predictions = df.to_dict('records')
            subscriber_id = os.path.basename(file_path).split('_')[0]
            
        else:
            return None
            
        analysis = {
            'subscriber_id': subscriber_id,
            'total_predictions': len(predictions),
            'games': defaultdict(int),
            'confidence_scores': [],
            'silence_periods': 0,
            'play_periods': 0,
            'predictions_by_date': defaultdict(list)
        }
        
        for pred in predictions:
            # Count by game
            game = pred.get('game', '')
            analysis['games'][game] += 1
            
            # Track confidence scores
            confidence = pred.get('confidence_score', pred.get('confidence', 0))
            if confidence:
                analysis['confidence_scores'].append(float(confidence))
            
            # Track silence vs play
            verdict = pred.get('final_verdict', pred.get('verdict', ''))
            if verdict == 'SILENCE':
                analysis['silence_periods'] += 1
            else:
                analysis['play_periods'] += 1
            
            # Group by date
            date = pred.get('draw_date', pred.get('date', ''))
            if date:
                analysis['predictions_by_date'][date].append(pred)
        
        return analysis
        
    except Exception as e:
        return {'error': str(e), 'file': file_path}

def check_winning_matches(predictions, actual_results):
    """Check predictions against actual winning numbers."""
    matches = {
        'exact_matches': [],
        'partial_matches': [],
        'no_matches': [],
        'total_checked': 0
    }
    
    for date, preds in predictions.items():
        if date not in actual_results:
            continue
            
        for pred in preds:
            matches['total_checked'] += 1
            game = pred.get('game', '')
            predicted_number = pred.get('winning_number', pred.get('number', ''))
            
            # Handle session-specific games (Cash3_MIDDAY, Cash3_NIGHT, etc.)
            actual_game_keys = []
            if game == 'Cash3':
                actual_game_keys = ['Cash3_MIDDAY', 'Cash3_NIGHT']
            elif game == 'Cash4':
                actual_game_keys = ['Cash4_MIDDAY', 'Cash4_NIGHT']  
            else:
                actual_game_keys = [game]
            
            match_found = False
            for actual_game_key in actual_game_keys:
                if actual_game_key in actual_results[date]:
                    actual_number = actual_results[date][actual_game_key]
                    
                    if game in ['Cash3', 'Cash4']:
                        # Cash3/Cash4 exact match
                        pred_clean = str(predicted_number).strip().replace(',', '')
                        actual_clean = str(actual_number).strip().replace(',', '')
                        
                        if pred_clean == actual_clean:
                            matches['exact_matches'].append({
                                'date': date,
                                'game': game,
                                'session': actual_game_key.split('_')[1] if '_' in actual_game_key else 'UNKNOWN',
                                'predicted': predicted_number,
                                'actual': actual_number,
                                'confidence': pred.get('confidence_score', 0),
                                'match_type': 'STRAIGHT'
                            })
                            match_found = True
                            break
                            
                        elif game == 'Cash3':
                            # Check for BOX matches in Cash3
                            pred_digits = sorted(pred_clean)
                            actual_digits = sorted(actual_clean)
                            if pred_digits == actual_digits and len(pred_digits) == 3:
                                matches['partial_matches'].append({
                                    'date': date,
                                    'game': game,
                                    'session': actual_game_key.split('_')[1] if '_' in actual_game_key else 'UNKNOWN',
                                    'match_type': 'BOX',
                                    'predicted': predicted_number,
                                    'actual': actual_number,
                                    'confidence': pred.get('confidence_score', 0)
                                })
                                match_found = True
                                break
                                
                    elif game in ['MegaMillions', 'Powerball', 'Cash4Life']:
                        # Jackpot games - exact match only (very rare)
                        if str(predicted_number).strip() == str(actual_number).strip():
                            matches['exact_matches'].append({
                                'date': date,
                                'game': game,
                                'predicted': predicted_number,
                                'actual': actual_number,
                                'confidence': pred.get('confidence_score', 0),
                                'match_type': 'JACKPOT'
                            })
                            match_found = True
                            break
            
            # If no match found in any session, record as no match
            if not match_found:
                # Find any actual number for this game to show what was drawn
                actual_sample = None
                for actual_game_key in actual_game_keys:
                    if actual_game_key in actual_results[date]:
                        actual_sample = actual_results[date][actual_game_key]
                        break
                
                matches['no_matches'].append({
                    'date': date,
                    'game': game,
                    'predicted': predicted_number,
                    'actual': actual_sample or 'Not drawn'
                })
    
    return matches

def main():
    """Analyze results from 1000 test subscribers."""
    print("🔍 Analyzing results from 1000 test subscribers...")
    
    # Find output files
    output_files = glob.glob("outputs/*TEST*.json") + glob.glob("outputs/*TEST*.csv")
    
    if not output_files:
        print("❌ No test output files found. Run batch_run_1000_test.py first.")
        return
    
    print(f"📂 Found {len(output_files)} output files to analyze")
    
    # Load actual winning numbers
    print("🎯 Loading actual winning numbers...")
    actual_results = load_actual_results()
    print(f"📅 Loaded results for {len(actual_results)} dates")
    
    # Analyze each file
    print("📊 Analyzing prediction files...")
    analyses = []
    total_matches = {
        'exact_matches': [],
        'partial_matches': [],
        'no_matches': [],
        'total_checked': 0
    }
    
    for i, file_path in enumerate(output_files, 1):
        if i % 100 == 0:
            print(f"   Processed {i}/{len(output_files)} files...")
        
        analysis = analyze_prediction_file(file_path)
        if analysis and 'error' not in analysis:
            analyses.append(analysis)
            
            # Check for winning matches
            matches = check_winning_matches(analysis['predictions_by_date'], actual_results)
            
            # Aggregate matches
            total_matches['exact_matches'].extend(matches['exact_matches'])
            total_matches['partial_matches'].extend(matches['partial_matches']) 
            total_matches['no_matches'].extend(matches['no_matches'])
            total_matches['total_checked'] += matches['total_checked']
    
    print(f"✅ Successfully analyzed {len(analyses)} files")
    
    # Compile statistics
    stats = {
        'analysis_timestamp': datetime.now().isoformat(),
        'files_analyzed': len(analyses),
        'total_predictions': sum(a['total_predictions'] for a in analyses),
        'games_breakdown': defaultdict(int),
        'confidence_stats': {},
        'silence_rate': 0,
        'winning_analysis': {}
    }
    
    # Aggregate game counts
    for analysis in analyses:
        for game, count in analysis['games'].items():
            stats['games_breakdown'][game] += count
    
    # Confidence score statistics
    all_confidence_scores = []
    for analysis in analyses:
        all_confidence_scores.extend(analysis['confidence_scores'])
    
    if all_confidence_scores:
        stats['confidence_stats'] = {
            'count': len(all_confidence_scores),
            'mean': float(np.mean(all_confidence_scores)),
            'std': float(np.std(all_confidence_scores)),
            'min': float(np.min(all_confidence_scores)),
            'max': float(np.max(all_confidence_scores)),
            'median': float(np.median(all_confidence_scores))
        }
    
    # Silence rate
    total_silence = sum(a['silence_periods'] for a in analyses)
    total_play = sum(a['play_periods'] for a in analyses) 
    if total_silence + total_play > 0:
        stats['silence_rate'] = total_silence / (total_silence + total_play) * 100
    
    # Winning analysis
    stats['winning_analysis'] = {
        'total_predictions_checked': total_matches['total_checked'],
        'exact_matches': len(total_matches['exact_matches']),
        'partial_matches': len(total_matches['partial_matches']),
        'no_matches': len(total_matches['no_matches']),
        'exact_match_rate': len(total_matches['exact_matches']) / total_matches['total_checked'] * 100 if total_matches['total_checked'] > 0 else 0,
        'any_match_rate': (len(total_matches['exact_matches']) + len(total_matches['partial_matches'])) / total_matches['total_checked'] * 100 if total_matches['total_checked'] > 0 else 0
    }
    
    # Save comprehensive results
    results_file = f"VALIDATION_ANALYSIS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    full_results = {
        'summary': stats,
        'exact_matches': total_matches['exact_matches'],
        'partial_matches': total_matches['partial_matches'],
        'individual_analyses': [
            {
                'subscriber_id': a['subscriber_id'],
                'total_predictions': a['total_predictions'],
                'games': dict(a['games']),
                'avg_confidence': np.mean(a['confidence_scores']) if a['confidence_scores'] else 0,
                'silence_rate': a['silence_periods'] / (a['silence_periods'] + a['play_periods']) * 100 if (a['silence_periods'] + a['play_periods']) > 0 else 0
            } for a in analyses
        ]
    }
    
    with open(results_file, 'w') as f:
        json.dump(full_results, f, indent=2)
    
    # Print comprehensive report
    print(f"\n🎯 VALIDATION ANALYSIS COMPLETE")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📊 FILES ANALYZED: {stats['files_analyzed']}")
    print(f"🎲 TOTAL PREDICTIONS: {stats['total_predictions']}")
    print(f"🎯 PREDICTIONS CHECKED: {stats['winning_analysis']['total_predictions_checked']}")
    print()
    
    print(f"🎮 GAME BREAKDOWN:")
    for game, count in stats['games_breakdown'].items():
        print(f"   {game}: {count:,} predictions")
    print()
    
    print(f"📈 CONFIDENCE SCORES:")
    if stats['confidence_stats']:
        cs = stats['confidence_stats']
        print(f"   Mean: {cs['mean']:.1f}%")
        print(f"   Range: {cs['min']:.1f}% - {cs['max']:.1f}%")
        print(f"   Std Dev: {cs['std']:.1f}%")
        print(f"   Median: {cs['median']:.1f}%")
    print()
    
    print(f"🔇 SILENCE RATE: {stats['silence_rate']:.1f}%")
    print()
    
    print(f"🏆 WINNING RESULTS:")
    wa = stats['winning_analysis']
    print(f"   Exact Matches: {wa['exact_matches']} ({wa['exact_match_rate']:.3f}%)")
    print(f"   Partial Matches: {wa['partial_matches']}")
    print(f"   Any Match Rate: {wa['any_match_rate']:.3f}%")
    print(f"   No Matches: {wa['no_matches']}")
    print()
    
    if total_matches['exact_matches']:
        print(f"✨ EXACT MATCHES DETAILS:")
        for match in total_matches['exact_matches'][:10]:  # Show first 10
            print(f"   {match['date']} - {match['game']}: {match['predicted']} (confidence: {match['confidence']:.1f}%)")
        if len(total_matches['exact_matches']) > 10:
            print(f"   ... and {len(total_matches['exact_matches']) - 10} more")
        print()
    
    print(f"💾 Full results saved to: {results_file}")
    print(f"🔄 Analysis complete!")

if __name__ == "__main__":
    main()