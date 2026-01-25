#!/usr/bin/env python3

import pandas as pd
import os
import json
from datetime import datetime
import glob

def load_all_lottery_results():
    """Load all combined lottery result files"""
    results = {}
    
    files = {
        'Cash3_Combined_2025.csv': ('cash3', 'draw_date'),
        'Cash4_Combined_2025.csv': ('cash4', 'draw_date'), 
        'Cash4Life_Combined_2025.csv': ('cash4life', 'date'),
        'MegaMillions_Combined_2025.csv': ('megamillions', 'date'),
        'Powerball_Combined_2025.csv': ('powerball', 'date')
    }
    
    base_dir = r'c:\MyBestOdds\jackpot_system_v3'
    
    for filename, (game_key, date_col) in files.items():
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df[date_col] = pd.to_datetime(df[date_col])
            results[game_key] = {
                'data': df,
                'date_col': date_col
            }
            print(f"✅ Loaded {game_key}: {len(df)} records")
        else:
            print(f"❌ Missing {filename}")
    
    return results

def load_prediction_files():
    """Load all prediction files from output/ folder"""
    predictions = []
    
    # Look in output/ folder for forecast.csv files in subscriber directories
    output_dir = r'c:\MyBestOdds\jackpot_system_v3\output'
    
    if os.path.exists(output_dir):
        # Look for all subscriber directories (exclude Test directories)
        for item in os.listdir(output_dir):
            if os.path.isdir(os.path.join(output_dir, item)) and not item.startswith(('Test_', 'AUDIT', 'COMPREHENSIVE')):
                forecast_file = os.path.join(output_dir, item, 'forecast.csv')
                
                if os.path.exists(forecast_file):
                    try:
                        df = pd.read_csv(forecast_file)
                        
                        # Add source info
                        df['source_folder'] = item
                        df['source_file'] = 'forecast.csv'
                        
                        # Convert date columns
                        if 'draw_date' in df.columns:
                            df['draw_date'] = pd.to_datetime(df['draw_date'], format='mixed', errors='coerce')
                        if 'forecast_date' in df.columns:
                            df['forecast_date'] = pd.to_datetime(df['forecast_date'], format='mixed', errors='coerce')
                        
                        predictions.append(df)
                        print(f"✅ Loaded predictions: {item} ({len(df)} records)")
                        
                        # Load more files for comprehensive analysis
                        if len(predictions) >= 50:
                            break
                            
                    except Exception as e:
                        print(f"❌ Error loading {forecast_file}: {e}")
    
    return predictions

def analyze_cash3_matches(predictions_df, results):
    """Analyze Cash3 predictions against results"""
    matches = []
    
    if 'cash3' not in results:
        return matches
    
    cash3_results = results['cash3']['data']
    
    for _, pred in predictions_df.iterrows():
        # Look for Cash3 predictions
        game = str(pred.get('game', '')).lower()
        if 'cash3' in game or game == 'cash 3' or game == 'cash-3':
            pred_date = pred.get('draw_date')
            if pd.isna(pred_date):
                continue
                
            # Get predicted number
            pred_numbers = str(pred.get('number', '')).zfill(3)  # Pad with zeros
            if len(pred_numbers) != 3 or not pred_numbers.isdigit():
                continue
                
            # Find matching results for that date
            matching_results = cash3_results[
                cash3_results['draw_date'].dt.date == pred_date.date()
            ]
            
            for _, result in matching_results.iterrows():
                result_numbers = str(result.get('digits', '')).zfill(3)
                
                # Check exact match (STRAIGHT)
                if pred_numbers == result_numbers:
                    matches.append({
                        'game': 'Cash3',
                        'date': pred_date,
                        'predicted_numbers': pred_numbers,
                        'winning_numbers': result_numbers,
                        'session': result.get('session', ''),
                        'play_type': pred.get('play_type', ''),
                        'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else pred.get('confidence_pct', ''),
                        'confidence_band': pred.get('confidence_band', ''),
                        'source_folder': pred.get('source_folder', ''),
                        'subscriber': pred.get('kit_name', ''),
                        'match_type': 'STRAIGHT'
                    })
                
                # Also check BOX matches (different arrangements)
                elif len(pred_numbers) == 3 and len(result_numbers) == 3:
                    pred_sorted = ''.join(sorted(pred_numbers))
                    result_sorted = ''.join(sorted(result_numbers))
                    
                    if pred_sorted == result_sorted:
                        matches.append({
                            'game': 'Cash3',
                            'date': pred_date,
                            'predicted_numbers': pred_numbers,
                            'winning_numbers': result_numbers,
                            'session': result.get('session', ''),
                            'play_type': pred.get('play_type', ''),
                            'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else pred.get('confidence_pct', ''),
                            'confidence_band': pred.get('confidence_band', ''),
                            'source_folder': pred.get('source_folder', ''),
                            'subscriber': pred.get('kit_name', ''),
                            'match_type': 'BOX'
                        })
    
    return matches

def analyze_cash4_matches(predictions_df, results):
    """Analyze Cash4 predictions against results"""
    matches = []
    
    if 'cash4' not in results:
        return matches
    
    cash4_results = results['cash4']['data']
    
    for _, pred in predictions_df.iterrows():
        # Look for Cash4 predictions
        game = str(pred.get('game', '')).lower()
        if 'cash4' in game or game == 'cash 4' or game == 'cash-4':
            pred_date = pred.get('draw_date')
            if pd.isna(pred_date):
                continue
                
            # Get predicted number
            pred_numbers = str(pred.get('number', '')).zfill(4)  # Pad with zeros
            if len(pred_numbers) != 4 or not pred_numbers.isdigit():
                continue
                
            # Find matching results for that date
            matching_results = cash4_results[
                cash4_results['draw_date'].dt.date == pred_date.date()
            ]
            
            for _, result in matching_results.iterrows():
                result_numbers = str(result.get('digits', '')).zfill(4)
                
                # Check exact match (STRAIGHT)
                if pred_numbers == result_numbers:
                    matches.append({
                        'game': 'Cash4',
                        'date': pred_date,
                        'predicted_numbers': pred_numbers,
                        'winning_numbers': result_numbers,
                        'session': result.get('session', ''),
                        'play_type': pred.get('play_type', ''),
                        'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else pred.get('confidence_pct', ''),
                        'confidence_band': pred.get('confidence_band', ''),
                        'source_folder': pred.get('source_folder', ''),
                        'subscriber': pred.get('kit_name', ''),
                        'match_type': 'STRAIGHT'
                    })
    
    return matches

def analyze_jackpot_matches(predictions_df, results):
    """Analyze jackpot game predictions (Cash4Life, Mega Millions, Powerball)"""
    matches = []
    
    # Map game names
    game_mapping = {
        'cash4life': 'cash4life',
        'c4l': 'cash4life',
        'megamillions': 'megamillions', 
        'mm': 'megamillions',
        'powerball': 'powerball',
        'pb': 'powerball'
    }
    
    for _, pred in predictions_df.iterrows():
        game = str(pred.get('game', '')).lower().replace(' ', '')
        game_code = str(pred.get('game_code', '')).lower()
        
        # Find the actual game type
        actual_game = None
        for key, value in game_mapping.items():
            if key in game or key in game_code:
                actual_game = value
                break
        
        if actual_game and actual_game in results:
            pred_date = pred.get('draw_date')
            if pd.isna(pred_date):
                continue
                
            game_results = results[actual_game]['data']
            date_col = results[actual_game]['date_col']
            
            # Find matching results for that date
            matching_results = game_results[
                game_results[date_col].dt.date == pred_date.date()
            ]
            
            for _, result in matching_results.iterrows():
                # For Cash4Life, check if predicted number matches any result number
                if actual_game == 'cash4life':
                    pred_number = pred.get('number', 0)
                    if isinstance(pred_number, (int, float)) and not pd.isna(pred_number):
                        pred_number = int(pred_number)
                        
                        # Check if predicted number matches any of the 5 main numbers
                        result_numbers = []
                        for i in range(1, 6):
                            val = result.get(f'n{i}')
                            if val is not None:
                                result_numbers.append(int(val))
                        
                        if pred_number in result_numbers:
                            matches.append({
                                'game': 'Cash4Life',
                                'date': pred_date,
                                'predicted_numbers': str(pred_number),
                                'winning_numbers': f"{result_numbers} + {result.get('bonus', 'N/A')}",
                                'session': 'Daily',
                                'play_type': pred.get('play_type', ''),
                                'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else pred.get('confidence_pct', ''),
                                'confidence_band': pred.get('confidence_band', ''),
                                'source_folder': pred.get('source_folder', ''),
                                'subscriber': pred.get('kit_name', ''),
                                'match_type': f'1 MAIN NUMBER ({pred_number})'
                            })
                
                # For MegaMillions and Powerball - look for number matches
                elif actual_game in ['megamillions', 'powerball']:
                    pred_number = pred.get('number', 0)
                    if isinstance(pred_number, (int, float)) and not pd.isna(pred_number):
                        pred_number = int(pred_number)
                        
                        # Check main numbers
                        result_numbers = []
                        for i in range(1, 6):
                            val = result.get(f'n{i}')
                            if val is not None:
                                result_numbers.append(int(val))
                        
                        bonus_number = result.get('bonus')
                        
                        # Check if predicted number matches any main number or bonus
                        if pred_number in result_numbers:
                            matches.append({
                                'game': actual_game.title().replace('mega', 'Mega ').replace('power', 'Power'),
                                'date': pred_date,
                                'predicted_numbers': str(pred_number),
                                'winning_numbers': f"{result_numbers} + {bonus_number}",
                                'session': 'Drawing',
                                'play_type': pred.get('play_type', ''),
                                'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else pred.get('confidence_pct', ''),
                                'confidence_band': pred.get('confidence_band', ''),
                                'source_folder': pred.get('source_folder', ''),
                                'subscriber': pred.get('kit_name', ''),
                                'match_type': f'1 MAIN NUMBER ({pred_number})'
                            })
                        elif pred_number == bonus_number:
                            matches.append({
                                'game': actual_game.title().replace('mega', 'Mega ').replace('power', 'Power'),
                                'date': pred_date,
                                'predicted_numbers': str(pred_number),
                                'winning_numbers': f"{result_numbers} + {bonus_number}",
                                'session': 'Drawing',
                                'play_type': pred.get('play_type', ''),
                                'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else pred.get('confidence_pct', ''),
                                'confidence_band': pred.get('confidence_band', ''),
                                'source_folder': pred.get('source_folder', ''),
                                'subscriber': pred.get('kit_name', ''),
                                'match_type': f'BONUS NUMBER ({pred_number})'
                            })
    
    return matches

def main():
    print("🎯 COMPREHENSIVE WIN VALIDATION ANALYSIS")
    print("=" * 70)
    
    # Load lottery results
    print("\n📊 Loading lottery results...")
    results = load_all_lottery_results()
    
    # Load prediction files
    print("\n🔍 Loading prediction files...")
    prediction_files = load_prediction_files()
    
    if not prediction_files:
        print("❌ No prediction files found in output/ folder")
        return
    
    all_matches = []
    
    # Analyze each prediction file
    for df in prediction_files:
        print(f"\n🎲 Analyzing predictions from {df['source_file'].iloc[0]}...")
        
        # Analyze Cash3 matches
        cash3_matches = analyze_cash3_matches(df, results)
        all_matches.extend(cash3_matches)
        
        # Analyze Cash4 matches
        cash4_matches = analyze_cash4_matches(df, results)
        all_matches.extend(cash4_matches)
        
        # Analyze jackpot matches
        jackpot_matches = analyze_jackpot_matches(df, results)
        all_matches.extend(jackpot_matches)
    
    # Display results
    print("\n" + "=" * 70)
    print(f"🎯 WINNING PREDICTIONS FOUND: {len(all_matches)}")
    print("=" * 70)
    
    if all_matches:
        # Sort by date to show chronologically
        all_matches.sort(key=lambda x: x['date'])
        
        # Remove duplicates (same prediction across multiple kits)
        unique_matches = []
        seen_combinations = set()
        
        for match in all_matches:
            key = (match['game'], match['date'].strftime('%Y-%m-%d'), match['predicted_numbers'], match['winning_numbers'], match['match_type'])
            if key not in seen_combinations:
                unique_matches.append(match)
                seen_combinations.add(key)
        
        # Show first 5 unique matches
        display_matches = unique_matches[:5] if len(unique_matches) >= 5 else unique_matches
        
        for i, match in enumerate(display_matches, 1):
            print(f"\n🏆 HIT #{i}:")
            print(f"   🎲 Game: {match['game']}")
            print(f"   📅 Date: {match['date'].strftime('%m/%d/%Y')}")
            print(f"   🎯 Predicted: {match['predicted_numbers']} ({match['play_type']})")
            print(f"   🏆 Winner: {match['winning_numbers']} ({match['session']})")
            print(f"   📊 Confidence: {match['confidence']} ({match['confidence_band']})")
            print(f"   👤 Subscriber: {match['subscriber']}")
            print(f"   🎮 Match Type: {match['match_type']}")
            print(f"   📁 Source: {match['source_folder']}")
            
            # Calculate potential winnings
            if match['game'] == 'Cash3':
                if match['match_type'] == 'STRAIGHT':
                    winnings = "$500 (50¢ straight)"
                else:
                    winnings = "$80 (50¢ box)"
            elif match['game'] == 'Cash4':
                if match['match_type'] == 'STRAIGHT':
                    winnings = "$5,000 (50¢ straight)"
                else:
                    winnings = "$200 (50¢ box)"
            elif 'Cash4Life' in match['game']:
                winnings = "$1,000/day for life (top prize) or $25-$2,500"
            elif 'Mega' in match['game']:
                if 'BONUS' in match['match_type']:
                    winnings = "$4 (Mega Ball only)"
                else:
                    winnings = "$4+ (1+ numbers + Mega Ball)"
            elif 'Power' in match['game']:
                if 'BONUS' in match['match_type']:
                    winnings = "$7 (Powerball only)"
                else:
                    winnings = "$7+ (1+ numbers + Powerball)"
            else:
                winnings = "Varies by game"
            
            print(f"   💰 Potential Winnings: {winnings}")
            print(f"   📈 Odds Beat: {match.get('odds', 'Unknown')}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total unique wins: {len(unique_matches)}")
        print(f"   Showing top {len(display_matches)} results")
        
        if len(unique_matches) > 5:
            print(f"   ({len(unique_matches) - 5} additional wins not shown)")
    else:
        print("\n❌ No exact matches found between predictions and winning numbers.")
        print("\n🔍 This suggests either:")
        print("   1. Prediction files are in a different format")
        print("   2. Predictions are stored elsewhere")
        print("   3. The documented wins need different validation approach")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()