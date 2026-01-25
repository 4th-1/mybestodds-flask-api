#!/usr/bin/env python3
"""
TEST RESULTS COMPREHENSIVE AUDIT v3.7
========================================

Audits all test subscriber outputs (BOOK3_TEST, BOOK_TEST, BOSK_TEST)
and generates detailed performance reports.

CRITICAL KIT-SPECIFIC RULES:
- BOOK3: Cash3, Cash4, MegaMillions, Powerball, Cash4Life
- BOOK: Cash3, Cash4, MegaMillions, Powerball, Cash4Life  
- BOSK: Cash3, Cash4 ONLY (jackpot games excluded from audit)

Usage:
    python audit_TEST_RESULTS_v3_7.py
"""

import json
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, date
from collections import defaultdict

# Project setup
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
AUDIT_DIR = PROJECT_ROOT / "outputs" / "TEST_AUDIT_V3_7"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

# KIT-specific game configurations
KIT_GAMES = {
    "BOOK3": ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"],
    "BOOK": ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"],
    "BOSK": ["Cash3", "Cash4"]  # NO JACKPOT GAMES
}

def load_ga_results():
    """Load actual Georgia Lottery results"""
    results_dir = PROJECT_ROOT / "data" / "ga_results"
    all_results = []
    
    for game_file in results_dir.glob("*.json"):
        try:
            with open(game_file, 'r') as f:
                data = json.load(f)
                
                # Handle both list format and dict with "draws" key
                if isinstance(data, list):
                    draws = data
                elif isinstance(data, dict) and "draws" in data:
                    draws = data["draws"]
                else:
                    print(f"⚠️  Skipping {game_file.name}: Invalid format")
                    continue
                
                # Determine game from filename
                game_name = None
                fname_lower = game_file.name.lower()
                if "cash3" in fname_lower:
                    game_name = "Cash3"
                elif "cash4" in fname_lower:
                    game_name = "Cash4"
                elif "mega" in fname_lower:
                    game_name = "MegaMillions"
                elif "powerball" in fname_lower:
                    game_name = "Powerball"
                elif "cash4life" in fname_lower:
                    game_name = "Cash4Life"
                
                for draw in draws:
                    all_results.append({
                        "date": draw.get("date"),
                        "game": draw.get("game", game_name),  # Use from draw or infer from filename
                        "session": draw.get("session", ""),
                        "winning_number": draw.get("winning_number")
                    })
        except Exception as e:
            print(f"⚠️  Error loading {game_file.name}: {e}")
    
    df = pd.DataFrame(all_results)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
    return df

def find_test_outputs():
    """Find all test subscriber output directories"""
    test_outputs = defaultdict(list)
    
    for kit in ["BOOK3", "BOOK", "BOSK"]:
        # Pattern to match test output folders like BOOK3_BOOK3_TEST0001_...
        pattern = f"{kit}_{kit}_TEST*"
        for output_dir in OUTPUTS_DIR.glob(pattern):
            if output_dir.is_dir():
                # Check for either forecast.csv or daily JSON files
                forecast_file = output_dir / "forecast.csv"
                has_jsons = any(output_dir.glob("*.json"))
                
                if forecast_file.exists() or has_jsons:
                    test_outputs[kit].append(output_dir)
        
        print(f"Found {len(test_outputs[kit])} test outputs for {kit}")
    
    return test_outputs

def load_predictions_from_dir(output_dir, kit):
    """Load predictions from output directory (forecast.csv or daily JSONs)"""
    allowed_games = KIT_GAMES[kit]
    all_predictions = []
    
    # First, try forecast.csv
    forecast_file = output_dir / "forecast.csv"
    if forecast_file.exists():
        try:
            df = pd.read_csv(forecast_file)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
            elif 'forecast_date' in df.columns:
                df['date'] = pd.to_datetime(df['forecast_date']).dt.date
            
            # Filter to allowed games
            if 'game' in df.columns:
                df = df[df['game'].isin(allowed_games)].copy()
            
            df['kit'] = kit
            df['source'] = output_dir.name
            return df
        except Exception as e:
            print(f"⚠️  Error loading forecast.csv from {output_dir.name}: {e}")
    
    # Otherwise, load from daily JSONs
    for json_file in sorted(output_dir.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Extract date from data or filename
            forecast_date = data.get("date", json_file.stem)
            
            # Extract predictions from the "picks" structure
            if "picks" in data:
                for game, picks_data in data["picks"].items():
                    if game not in allowed_games:  # Filter by KIT games
                        continue
                    
                    # Get predictions from different lanes
                    predictions_list = []
                    if isinstance(picks_data, dict):
                        # Collect from all lanes (lane_system, lane_mmfsn, etc.)
                        for lane_key, lane_values in picks_data.items():
                            if isinstance(lane_values, list):
                                predictions_list.extend(lane_values)
                    
                    # Create entry for each prediction
                    for i, prediction in enumerate(predictions_list):
                        # For Cash3/Cash4: extract number only
                        # For jackpot games: full string with Mega/Power ball
                        if game in ["Cash3", "Cash4"]:
                            number = prediction.strip()
                        else:
                            number = prediction.strip()
                        
                        all_predictions.append({
                            'date': forecast_date,
                            'game': game,
                            'prediction': number,
                            'score': data.get('score', 0),
                            'rank': i + 1,
                            'kit': kit,
                            'source': output_dir.name
                        })
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
            continue
    
    if all_predictions:
        df = pd.DataFrame(all_predictions)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    else:
        return None

def audit_kit(kit, output_dirs, ga_results):
    """Audit all forecasts for a specific KIT"""
    print(f"\n{'='*70}")
    print(f"AUDITING {kit} KIT")
    print(f"{'='*70}")
    print(f"Allowed games: {', '.join(KIT_GAMES[kit])}")
    print(f"Output directories: {len(output_dirs)}")
    
    all_predictions = []
    for output_dir in output_dirs[:5]:  # Limit to first 5 for testing
        df = load_predictions_from_dir(output_dir, kit)
        if df is not None:
            all_predictions.append(df)
    
    if not all_predictions:
        print(f"❌ No valid predictions found for {kit}")
        return None
    
    predictions = pd.concat(all_predictions, ignore_index=True)
    print(f"Total predictions: {len(predictions)}")
    
    # Game breakdown
    if 'game' in predictions.columns:
        print("\nPredictions by game:")
        for game, count in predictions['game'].value_counts().items():
            print(f"  {game}: {count}")
    
    # Match against actual results
    matches = []
    for _, pred in predictions.iterrows():
        pred_date = pred['date']
        pred_game = pred.get('game', '')
        pred_number = pred.get('prediction', pred.get('candidate', ''))
        
        # Find matching actual result
        actual = ga_results[
            (ga_results['date'] == pred_date) &
            (ga_results['game'] == pred_game)
        ]
        
        if not actual.empty:
            winning_number = actual.iloc[0]['winning_number']
            is_match = str(pred_number) == str(winning_number)
            matches.append({
                'kit': kit,
                'date': pred_date,
                'game': pred_game,
                'prediction': pred_number,
                'actual': winning_number,
                'match': is_match,
                'source': pred.get('source', '')
            })
    
    if matches:
        match_df = pd.DataFrame(matches)
        accuracy = (match_df['match'].sum() / len(match_df)) * 100
        print(f"\n✅ Accuracy: {accuracy:.2f}% ({match_df['match'].sum()}/{len(match_df)} matches)")
        
        # Save detailed results
        output_file = AUDIT_DIR / f"{kit}_audit_results.csv"
        match_df.to_csv(output_file, index=False)
        print(f"📊 Detailed results: {output_file}")
        
        return {
            'kit': kit,
            'total_predictions': len(predictions),
            'matched_predictions': len(match_df),
            'hits': match_df['match'].sum(),
            'accuracy': accuracy,
            'games_audited': KIT_GAMES[kit]
        }
    else:
        print("⚠️  No matches found (predictions may be outside result date range)")
        return None

def main():
    print("="*70)
    print("TEST RESULTS COMPREHENSIVE AUDIT v3.7")
    print("="*70)
    print("\nKIT-SPECIFIC GAME CONFIGURATIONS:")
    for kit, games in KIT_GAMES.items():
        print(f"  {kit}: {', '.join(games)}")
    
    # Load actual results
    print(f"\n{'='*70}")
    print("LOADING ACTUAL GA RESULTS")
    print(f"{'='*70}")
    ga_results = load_ga_results()
    print(f"Loaded {len(ga_results)} actual results")
    if not ga_results.empty:
        print(f"Date range: {ga_results['date'].min()} to {ga_results['date'].max()}")
    
    # Find test outputs
    print(f"\n{'='*70}")
    print("FINDING TEST OUTPUTS")
    print(f"{'='*70}")
    test_outputs = find_test_outputs()
    for kit, files in test_outputs.items():
        print(f"{kit}: {len(files)} output directories")
    
    # Audit each KIT
    results = []
    for kit in ["BOOK3", "BOOK", "BOSK"]:
        if kit in test_outputs:
            result = audit_kit(kit, test_outputs[kit], ga_results)
            if result:
                results.append(result)
    
    # Generate summary report
    print(f"\n{'='*70}")
    print("AUDIT SUMMARY")
    print(f"{'='*70}")
    
    summary_df = pd.DataFrame(results)
    if not summary_df.empty:
        print(summary_df.to_string(index=False))
        
        # Save summary
        summary_file = AUDIT_DIR / "audit_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"\n📊 Summary saved: {summary_file}")
        
        # Save JSON summary with games list
        summary_json = AUDIT_DIR / "audit_summary.json"
        with open(summary_json, 'w') as f:
            json.dump({
                'audit_date': datetime.now().isoformat(),
                'kit_configurations': KIT_GAMES,
                'results': results
            }, f, indent=2, default=str)
        print(f"📊 JSON summary: {summary_json}")
    else:
        print("❌ No results to summarize")
    
    print(f"\n{'='*70}")
    print("AUDIT COMPLETE")
    print(f"{'='*70}")
    print(f"Output directory: {AUDIT_DIR}")

if __name__ == "__main__":
    main()
