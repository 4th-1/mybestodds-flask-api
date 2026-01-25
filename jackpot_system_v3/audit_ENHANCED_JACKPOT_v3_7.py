"""
audit_ENHANCED_JACKPOT_v3_7.py
Enhanced jackpot game audit with complete number combination analysis

NOW TESTS:
- Complete 5+1 number combinations (not single digits)
- ALL prize tiers for each jackpot game
- Real prize payouts for each tier
- Enhanced Right Engine predictions

FIXES:
- Cash4Life "1+0" non-paying tier issue → Full combination coverage
- Missing Powerball/MegaMillions analysis → Complete coverage
- Single digit limitations → Multi-number analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys
from datetime import datetime, date
import os
import re

# Project setup
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Enhanced Right Engine import
try:
    from engines.rightside_v3_7.rightside_engine_v3_7_ENHANCED import EnhancedJackpotEngine
    ENHANCED_ENGINE_AVAILABLE = True
    print("✅ Enhanced Jackpot Engine loaded successfully")
except ImportError as e:
    ENHANCED_ENGINE_AVAILABLE = False
    print(f"⚠️ Enhanced engine not available: {e}")

# Prize structures for accurate payout calculation
JACKPOT_PRIZE_STRUCTURES = {
    'Cash4Life': {
        '5+1': 365000,  # $1000/day * 365 = lifetime value approximation
        '5+0': 52000,   # $1000/week * 52 = lifetime value approximation  
        '4+1': 2500,
        '4+0': 500,
        '3+1': 100,
        '3+0': 25,
        '2+1': 10,
        '1+1': 2,
        '1+0': 0,       # Non-paying tier (our old problem!)
        '0+1': 0,       # Non-paying tier
        '0+0': 0        # Non-paying tier
    },
    'Powerball': {
        '5+1': 40000000,  # Average jackpot (varies)
        '5+0': 1000000,
        '4+1': 50000,
        '4+0': 100,
        '3+1': 100, 
        '3+0': 7,
        '2+1': 7,
        '1+1': 4,
        '0+1': 4,       # Powerball-only win!
        '0+0': 0
    },
    'MegaMillions': {
        '5+1': 20000000,  # Average jackpot (varies)
        '5+0': 1000000,
        '4+1': 10000,
        '4+0': 500,
        '3+1': 200,
        '3+0': 10,
        '2+1': 10,
        '1+1': 4,
        '0+1': 2,       # Mega Ball-only win!
        '0+0': 0
    }
}

def load_authoritative_data():
    """Load authoritative CSV data for jackpot games"""
    
    data_files = {
        'Cash4Life': PROJECT_ROOT / 'data' / 'results' / 'jackpot_results' / 'Cash4Life.csv',
        'Powerball': PROJECT_ROOT / 'data' / 'results' / 'jackpot_results' / 'Powerball.csv', 
        'MegaMillions': PROJECT_ROOT / 'data' / 'results' / 'jackpot_results' / 'MegaMillions.csv'
    }
    
    jackpot_data = {}
    
    for game, file_path in data_files.items():
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                print(f"✅ Loaded {game}: {len(df)} draws")
                
                # Standardize column names
                df.columns = df.columns.str.lower().str.strip()
                
                # Convert date column
                date_cols = [col for col in df.columns if 'date' in col]
                if date_cols:
                    df['date'] = pd.to_datetime(df[date_cols[0]]).dt.date
                
                jackpot_data[game] = df
                
            except Exception as e:
                print(f"❌ Error loading {game}: {e}")
                jackpot_data[game] = pd.DataFrame()
        else:
            print(f"⚠️ Missing file: {file_path}")
            jackpot_data[game] = pd.DataFrame()
    
    return jackpot_data

def parse_prediction_combination(combination_str):
    """Parse prediction combination string into main numbers and bonus"""
    
    if pd.isna(combination_str) or combination_str == 'N/A':
        return [], None
        
    try:
        # Handle format like "3-6-15-30-51+3"
        if '+' in combination_str:
            main_part, bonus_part = combination_str.split('+')
            main_numbers = [int(x.strip()) for x in main_part.split('-')]
            bonus_number = int(bonus_part.strip())
            return main_numbers, bonus_number
        else:
            # Fallback for other formats
            numbers = [int(x.strip()) for x in combination_str.replace('-', ' ').split()]
            if len(numbers) >= 6:
                return numbers[:-1], numbers[-1]
            else:
                return numbers, None
                
    except (ValueError, AttributeError) as e:
        print(f"⚠️ Could not parse combination: {combination_str} - {e}")
        return [], None

def extract_winning_numbers(row, game):
    """Extract winning numbers from authoritative CSV data"""
    
    try:
        # CSV format: game,date,n1,n2,n3,n4,n5,bonus
        main_numbers = [int(row['n1']), int(row['n2']), int(row['n3']), int(row['n4']), int(row['n5'])]
        bonus_number = int(row['bonus'])
        
        return main_numbers, bonus_number
        
    except Exception as e:
        print(f"⚠️ Error extracting winning numbers from {game}: {e}")
        return [], None

def calculate_jackpot_matches(pred_main, pred_bonus, win_main, win_bonus):
    """Calculate number of matches for jackpot game"""
    
    if not pred_main or not win_main:
        return 0, 0
        
    # Count main number matches
    main_matches = len(set(pred_main) & set(win_main))
    
    # Check bonus match
    bonus_match = 1 if (pred_bonus is not None and win_bonus is not None and pred_bonus == win_bonus) else 0
    
    return main_matches, bonus_match

def determine_prize_tier(main_matches, bonus_match, game):
    """Determine prize tier and payout for jackpot game"""
    
    tier_key = f"{main_matches}+{bonus_match}"
    
    if game in JACKPOT_PRIZE_STRUCTURES and tier_key in JACKPOT_PRIZE_STRUCTURES[game]:
        prize = JACKPOT_PRIZE_STRUCTURES[game][tier_key] 
        return tier_key, prize
    else:
        return f"{main_matches}+{bonus_match}", 0

def analyze_enhanced_predictions():
    """Analyze enhanced jackpot predictions with complete combination support"""
    
    print("=" * 80)
    print("🎰 ENHANCED JACKPOT PREDICTION AUDIT v3.7")
    print("=" * 80)
    print("📊 Testing complete number combinations vs single digits")
    print("🎯 Checking ALL prize tiers for maximum winning potential")
    print()
    
    # Load authoritative winning data
    jackpot_data = load_authoritative_data()
    
    # Find prediction files
    prediction_files = []
    
    # Look for actual prediction files in output directories
    for kit in ['BOOK3', 'BOOK', 'BOSK']:
        output_dirs = list(PROJECT_ROOT.glob(f"output/*{kit}*"))
        for output_dir in output_dirs:
            forecast_file = output_dir / 'forecast.csv'
            if forecast_file.exists():
                prediction_files.append((kit, forecast_file))
                print(f"📁 Found {kit} predictions: {forecast_file.name}")
    
    if not prediction_files:
        print("❌ No prediction files found with jackpot games")
        return
    
    # Initialize results tracking
    total_wins = 0
    total_winnings = 0
    total_predictions = 0
    
    game_results = {
        'Cash4Life': {'predictions': 0, 'wins': 0, 'winnings': 0, 'win_details': []},
        'Powerball': {'predictions': 0, 'wins': 0, 'winnings': 0, 'win_details': []},
        'MegaMillions': {'predictions': 0, 'wins': 0, 'winnings': 0, 'win_details': []}
    }
    
    # Process each prediction file
    for kit, file_path in prediction_files:
        print(f"\n🔍 Analyzing {kit}: {file_path.name}")
        
        try:
            pred_df = pd.read_csv(file_path)
            
            # Look for jackpot game rows
            for idx, row in pred_df.iterrows():
                # Determine game type
                game = None
                if any(x in str(row).lower() for x in ['cash4life', 'cash_4_life']):
                    game = 'Cash4Life'
                elif any(x in str(row).lower() for x in ['powerball', 'power_ball']):
                    game = 'Powerball' 
                elif any(x in str(row).lower() for x in ['megamillions', 'mega_millions']):
                    game = 'MegaMillions'
                
                if not game or game not in jackpot_data or jackpot_data[game].empty:
                    continue
                
                # Get prediction date
                pred_date = None
                for col in ['date', 'draw_date', 'prediction_date']:
                    if col in row.index and not pd.isna(row[col]):
                        try:
                            pred_date = pd.to_datetime(row[col]).date()
                            break
                        except:
                            continue
                
                if pred_date is None:
                    continue
                
                # Analyze current single digit prediction
                current_number = None
                if 'number' in row.index and not pd.isna(row['number']):
                    current_number = row['number']
                
                print(f"  📋 Current single digit: {current_number} (why it fails jackpot games!)")
                
                # Generate enhanced prediction for this row
                prediction_combo = None
                
                if ENHANCED_ENGINE_AVAILABLE:
                    # Use enhanced engine to generate full combination
                    enhanced_engine = EnhancedJackpotEngine()
                    
                    # Mock subscriber data for testing
                    test_subscriber = {
                        'identity': {
                            'first_name': 'Test',
                            'last_name': 'Subscriber',
                            'date_of_birth': '1985-03-15'
                        }
                    }
                    
                    # Create mock row data
                    mock_row = pd.Series({
                        'n1': getattr(row, 'n1', 5),
                        'n2': getattr(row, 'n2', 12), 
                        'n3': getattr(row, 'n3', 23),
                        'n4': getattr(row, 'n4', 35),
                        'n5': getattr(row, 'n5', 48),
                        'bonus': getattr(row, 'bonus', 3),
                        'draw_date': pred_date
                    })
                    
                    try:
                        enhanced_result = enhanced_engine.generate_full_jackpot_combination(
                            game, test_subscriber, mock_row
                        )
                        prediction_combo = enhanced_result.get('full_combination')
                        print(f"  🎯 Enhanced prediction: {prediction_combo}")
                    except Exception as e:
                        print(f"  ⚠️ Enhanced generation failed: {e}")
                
                # Parse prediction combination
                if prediction_combo:
                    pred_main, pred_bonus = parse_prediction_combination(prediction_combo)
                else:
                    # Fallback to extracting from existing prediction data
                    pred_main, pred_bonus = [], None
                    
                if not pred_main:
                    continue
                
                total_predictions += 1
                game_results[game]['predictions'] += 1
                
                # Find matching winning draw
                winning_draws = jackpot_data[game][jackpot_data[game]['date'] == pred_date]
                
                if winning_draws.empty:
                    print(f"  📅 No winning data for {pred_date}")
                    continue
                
                winning_row = winning_draws.iloc[0]
                win_main, win_bonus = extract_winning_numbers(winning_row, game)
                
                if not win_main:
                    continue
                
                print(f"  📋 Prediction: {pred_main} + {pred_bonus}")
                print(f"  🎰 Winning:    {win_main} + {win_bonus}")
                
                # Calculate matches
                main_matches, bonus_match = calculate_jackpot_matches(
                    pred_main, pred_bonus, win_main, win_bonus
                )
                
                # Determine prize tier
                tier, prize = determine_prize_tier(main_matches, bonus_match, game)
                
                if prize > 0:
                    total_wins += 1
                    total_winnings += prize
                    game_results[game]['wins'] += 1
                    game_results[game]['winnings'] += prize
                    
                    win_detail = {
                        'date': pred_date,
                        'tier': tier,
                        'prize': prize,
                        'prediction': f"{pred_main}+{pred_bonus}",
                        'winning': f"{win_main}+{win_bonus}"
                    }
                    game_results[game]['win_details'].append(win_detail)
                    
                    print(f"  🎉 WIN! Tier {tier} = ${prize:,}")
                else:
                    print(f"  ❌ No win (Tier {tier})")
                    
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            continue
    
    # Generate final results report
    print("\n" + "=" * 80)
    print("📊 ENHANCED JACKPOT AUDIT RESULTS")
    print("=" * 80)
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Total Predictions: {total_predictions:,}")
    print(f"   Total Wins: {total_wins:,}")
    print(f"   Win Rate: {(total_wins/total_predictions*100) if total_predictions > 0 else 0:.2f}%")
    print(f"   Total Winnings: ${total_winnings:,}")
    
    print(f"\n🎰 GAME-BY-GAME BREAKDOWN:")
    for game, results in game_results.items():
        if results['predictions'] > 0:
            win_rate = (results['wins'] / results['predictions'] * 100)
            print(f"\n   {game}:")
            print(f"     Predictions: {results['predictions']:,}")
            print(f"     Wins: {results['wins']:,}")
            print(f"     Win Rate: {win_rate:.2f}%")
            print(f"     Winnings: ${results['winnings']:,}")
            
            if results['win_details']:
                print(f"     Win Details:")
                for detail in results['win_details']:
                    print(f"       {detail['date']}: {detail['tier']} = ${detail['prize']:,}")
    
    print(f"\n🚀 ENHANCEMENT IMPACT:")
    print(f"   Previous Cash4Life: 3 predictions, 0 wins, $0")
    print(f"   Enhanced Cash4Life: {game_results['Cash4Life']['predictions']} predictions, {game_results['Cash4Life']['wins']} wins, ${game_results['Cash4Life']['winnings']:,}")
    print(f"   Previous Other Games: Not analyzed")
    print(f"   Enhanced Coverage: All games with complete combination analysis")
    
    print("\n" + "=" * 80)
    print("✅ ENHANCED JACKPOT AUDIT COMPLETE")
    print("🎰 Complete number combinations provide access to ALL prize tiers!")
    print("=" * 80)
    
    return {
        'total_predictions': total_predictions,
        'total_wins': total_wins, 
        'total_winnings': total_winnings,
        'game_results': game_results
    }

if __name__ == "__main__":
    results = analyze_enhanced_predictions()