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
    """Load ALL prediction files from output/ folder"""
    predictions = []
    
    # Look in output/ folder for forecast.csv files in subscriber directories
    output_dir = r'c:\MyBestOdds\jackpot_system_v3\output'
    
    if os.path.exists(output_dir):
        count = 0
        loaded_folders = []
        
        # Get all directories and sort them to process systematically  
        try:
            all_items = os.listdir(output_dir)
            all_dirs = [item for item in all_items if os.path.isdir(os.path.join(output_dir, item))]
            all_dirs.sort()
            
            for item in all_dirs:
                # Skip test directories and audit directories
                if item.startswith(('Test_', 'AUDIT', 'COMPREHENSIVE')):
                    continue
                    
                # Load forecast.csv files
                forecast_file = os.path.join(output_dir, item, 'forecast.csv')
                
                if os.path.exists(forecast_file):
                    try:
                        df = pd.read_csv(forecast_file)
                        df['source_folder'] = item
                        predictions.append(df)
                        loaded_folders.append(item)
                        count += 1
                        
                        # Process ALL subscriber folders to find maximum hits
                        
                    except Exception as e:
                        print(f"❌ Error loading {forecast_file}: {e}")
            
            print(f"📊 Loaded {count} prediction folders")
            if loaded_folders:
                print(f"    First 5 folders: {', '.join(loaded_folders[:5])}")
                
        except Exception as e:
            print(f"❌ Error listing output directory: {e}")
    
    return pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()

def analyze_cash3_matches(predictions_df, results):
    """Analyze Cash3 predictions for exact and BOX matches with enhanced pattern checking"""
    matches = []
    
    if 'cash3' not in results:
        return matches
    
    cash3_results = results['cash3']['data']
    
    for _, pred in predictions_df.iterrows():
        # Look for Cash3 predictions with more flexible game name matching
        game = str(pred.get('game', '')).lower()
        if 'cash3' in game or 'cash 3' in game or 'cash-3' in game or game == 'c3':
            # Get predicted date with proper parsing
            pred_date_raw = pred.get('draw_date')
            if pd.isna(pred_date_raw):
                continue
                
            # Convert to datetime if it's a string
            if isinstance(pred_date_raw, str):
                try:
                    pred_date = pd.to_datetime(pred_date_raw)
                except:
                    continue
            else:
                pred_date = pred_date_raw
                
            # Get predicted number with multiple format handling
            pred_numbers = str(pred.get('number', '')).zfill(3)
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
                        'play_type': pred.get('play_type', 'Straight'),
                        'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                        'confidence_band': pred.get('confidence_band', ''),
                        'source_folder': pred.get('source_folder', ''),
                        'subscriber': pred.get('kit_name', ''),
                        'match_type': 'STRAIGHT'
                    })
                
                # Check BOX match (any arrangement)
                elif sorted(pred_numbers) == sorted(result_numbers):
                    matches.append({
                        'game': 'Cash3',
                        'date': pred_date,
                        'predicted_numbers': pred_numbers,
                        'winning_numbers': result_numbers,
                        'session': result.get('session', ''),
                        'play_type': pred.get('play_type', 'Box'),
                        'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                        'confidence_band': pred.get('confidence_band', ''),
                        'source_folder': pred.get('source_folder', ''),
                        'subscriber': pred.get('kit_name', ''),
                        'match_type': 'BOX'
                    })
                
    return matches

def analyze_cash4_matches(predictions_df, results):
    """Analyze Cash4 predictions for exact and BOX matches"""
    matches = []
    
    if 'cash4' not in results:
        return matches
    
    cash4_results = results['cash4']['data']
    
    for _, pred in predictions_df.iterrows():
        # Look for Cash4 predictions
        game = str(pred.get('game', '')).lower()
        if 'cash4' in game or 'cash 4' in game or 'cash-4' in game or game == 'c4':
            # Get predicted date with proper parsing
            pred_date_raw = pred.get('draw_date')
            if pd.isna(pred_date_raw):
                continue
                
            # Convert to datetime if it's a string
            if isinstance(pred_date_raw, str):
                try:
                    pred_date = pd.to_datetime(pred_date_raw)
                except:
                    continue
            else:
                pred_date = pred_date_raw
                
            # Get predicted number
            pred_numbers = str(pred.get('number', '')).zfill(4)
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
                        'play_type': pred.get('play_type', 'Straight'),
                        'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                        'confidence_band': pred.get('confidence_band', ''),
                        'source_folder': pred.get('source_folder', ''),
                        'subscriber': pred.get('kit_name', ''),
                        'match_type': 'STRAIGHT'
                    })
                
                # Check BOX match (any arrangement)
                elif sorted(pred_numbers) == sorted(result_numbers):
                    matches.append({
                        'game': 'Cash4',
                        'date': pred_date,
                        'predicted_numbers': pred_numbers,
                        'winning_numbers': result_numbers,
                        'session': result.get('session', ''),
                        'play_type': pred.get('play_type', 'Box'),
                        'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                        'confidence_band': pred.get('confidence_band', ''),
                        'source_folder': pred.get('source_folder', ''),
                        'subscriber': pred.get('kit_name', ''),
                        'match_type': 'BOX'
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
        'mega millions': 'megamillions',
        'mm': 'megamillions',
        'powerball': 'powerball',
        'pb': 'powerball'
    }
    
    for _, pred in predictions_df.iterrows():
        game = str(pred.get('game', '')).lower().replace(' ', '').replace('-', '')
        
        # Find which game this prediction is for
        result_game = None
        for key, mapped in game_mapping.items():
            if key in game:
                result_game = mapped
                break
        
        if result_game and result_game in results:
            # Get predicted date with proper parsing
            pred_date_raw = pred.get('draw_date')
            if pd.isna(pred_date_raw):
                continue
                
            # Convert to datetime if it's a string
            if isinstance(pred_date_raw, str):
                try:
                    pred_date = pd.to_datetime(pred_date_raw)
                except:
                    continue
            else:
                pred_date = pred_date_raw
            
            # Get the results for this game
            game_results = results[result_game]['data']
            date_col = results[result_game]['date_col']
            
            # Find matching results for that date
            matching_results = game_results[
                game_results[date_col].dt.date == pred_date.date()
            ]
            
            for _, result in matching_results.iterrows():
                pred_number = str(pred.get('number', '')).strip()
                
                # Skip invalid predictions (0, empty, etc.)
                if not pred_number or pred_number == '0' or not pred_number.isdigit():
                    continue
                
                # Cash4Life analysis
                if result_game == 'cash4life':
                    # Get main numbers and cash ball
                    main_nums = [int(x) for x in str(result.get('main_numbers', '')).split('-') if x.isdigit()]
                    cash_ball = result.get('cash_ball', 0)
                    
                    # Check if prediction matches any main number
                    if int(pred_number) in main_nums:
                        matches.append({
                            'game': 'Cash4Life',
                            'date': pred_date,
                            'predicted_numbers': pred_number,
                            'winning_numbers': f"{'-'.join(map(str, main_nums))} + {cash_ball}",
                            'session': result.get('session', 'Daily'),
                            'play_type': pred.get('play_type', ''),
                            'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                            'confidence_band': pred.get('confidence_band', ''),
                            'source_folder': pred.get('source_folder', ''),
                            'subscriber': pred.get('kit_name', ''),
                            'match_type': f'1 MAIN NUMBER ({pred_number})'
                        })
                
                # Mega Millions analysis
                elif result_game == 'megamillions':
                    main_nums = [int(x) for x in str(result.get('main_numbers', '')).split('-') if x.isdigit()]
                    mega_ball = result.get('mega_ball', 0)
                    
                    pred_int = int(pred_number)
                    if pred_int in main_nums:
                        matches.append({
                            'game': 'Mega Millions',
                            'date': pred_date,
                            'predicted_numbers': pred_number,
                            'winning_numbers': f"{'-'.join(map(str, main_nums))} + {mega_ball}",
                            'session': 'Weekly',
                            'play_type': pred.get('play_type', ''),
                            'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                            'confidence_band': pred.get('confidence_band', ''),
                            'source_folder': pred.get('source_folder', ''),
                            'subscriber': pred.get('kit_name', ''),
                            'match_type': f'1 MAIN NUMBER ({pred_number})'
                        })
                    elif pred_int == mega_ball and mega_ball != 0:  # Don't match 0 mega balls
                        matches.append({
                            'game': 'Mega Millions',
                            'date': pred_date,
                            'predicted_numbers': pred_number,
                            'winning_numbers': f"{'-'.join(map(str, main_nums))} + {mega_ball}",
                            'session': 'Weekly',
                            'play_type': pred.get('play_type', ''),
                            'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                            'confidence_band': pred.get('confidence_band', ''),
                            'source_folder': pred.get('source_folder', ''),
                            'subscriber': pred.get('kit_name', ''),
                            'match_type': f'MEGA BALL ({pred_number})'
                        })
                
                # Powerball analysis
                elif result_game == 'powerball':
                    main_nums = [int(x) for x in str(result.get('main_numbers', '')).split('-') if x.isdigit()]
                    power_ball = result.get('powerball', 0)
                    
                    pred_int = int(pred_number)
                    if pred_int in main_nums:
                        matches.append({
                            'game': 'Powerball',
                            'date': pred_date,
                            'predicted_numbers': pred_number,
                            'winning_numbers': f"{'-'.join(map(str, main_nums))} + {power_ball}",
                            'session': 'Weekly',
                            'play_type': pred.get('play_type', ''),
                            'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                            'confidence_band': pred.get('confidence_band', ''),
                            'source_folder': pred.get('source_folder', ''),
                            'subscriber': pred.get('kit_name', ''),
                            'match_type': f'1 MAIN NUMBER ({pred_number})'
                        })
                    elif pred_int == power_ball and power_ball != 0:  # Don't match 0 powerballs
                        matches.append({
                            'game': 'Powerball',
                            'date': pred_date,
                            'predicted_numbers': pred_number,
                            'winning_numbers': f"{'-'.join(map(str, main_nums))} + {power_ball}",
                            'session': 'Weekly',
                            'play_type': pred.get('play_type', ''),
                            'confidence': f"{pred.get('confidence_score', 0)*100:.1f}%" if pred.get('confidence_score') else str(pred.get('confidence_pct', '')),
                            'confidence_band': pred.get('confidence_band', ''),
                            'source_folder': pred.get('source_folder', ''),
                            'subscriber': pred.get('kit_name', ''),
                            'match_type': f'POWERBALL ({pred_number})'
                        })
    
    return matches

def main():
    print("🎯 ENHANCED WIN VALIDATION ANALYSIS")
    print("=" * 70)
    
    # Load lottery results
    print("\n📊 Loading lottery results...")
    results = load_all_lottery_results()
    
    # Load prediction files
    print("\n🔍 Loading ALL prediction files...")
    predictions_df = load_prediction_files()
    
    if predictions_df.empty:
        print("❌ No predictions loaded!")
        return
    
    # Analyze predictions against results
    print("\n🎲 Analyzing ALL predictions from forecast.csv...")
    
    cash3_matches = analyze_cash3_matches(predictions_df, results)
    cash4_matches = analyze_cash4_matches(predictions_df, results)
    jackpot_matches = analyze_jackpot_matches(predictions_df, results)
    
    # Combine and display results
    all_matches = cash3_matches + cash4_matches + jackpot_matches
    
    if all_matches:
        print(f"\n{'='*70}")
        print(f"🎯 WINNING PREDICTIONS FOUND: {len(all_matches)}")
        print(f"{'='*70}")
        
        # Remove duplicates (same prediction across multiple kits)
        unique_matches = []
        seen_combinations = set()
        
        for match in all_matches:
            key = (match['game'], match['date'].strftime('%Y-%m-%d'), match['predicted_numbers'], match['winning_numbers'], match['match_type'])
            if key not in seen_combinations:
                unique_matches.append(match)
                seen_combinations.add(key)
        
        # Sort by confidence and date
        unique_matches.sort(key=lambda x: (
            float(x['confidence'].replace('%', '')) if x['confidence'] and '%' in x['confidence'] else 0,
            x['date']
        ), reverse=True)
        
        # Show top 10 results
        display_matches = unique_matches[:10] if len(unique_matches) >= 10 else unique_matches
        
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
                if 'MEGA BALL' in match['match_type']:
                    winnings = "$2 (Mega Ball only)"
                else:
                    winnings = "$2+ (1+ numbers)"
            elif 'Power' in match['game']:
                if 'POWERBALL' in match['match_type']:
                    winnings = "$4 (Powerball only)"
                else:
                    winnings = "$4+ (1+ numbers)"
            else:
                winnings = "Varies by game"
            
            print(f"   💰 Potential Winnings: {winnings}")
            print(f"   📈 Odds Beat: {match.get('odds', 'Unknown')}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total unique wins: {len(unique_matches)}")
        print(f"   Showing top {len(display_matches)} results")
        
        if len(unique_matches) > 10:
            print(f"   ({len(unique_matches) - 10} additional wins not shown)")
    else:
        print("\n❌ No exact matches found between predictions and winning numbers.")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()