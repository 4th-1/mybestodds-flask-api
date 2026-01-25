"""
LOTTERY WINNING AUDIT v3.7 - My Best Odds
Validates predictions with PROPER lottery winning logic:
- Cash3: STRAIGHT, BOX, PAIRS, 1-OFF
- Cash4: STRAIGHT, BOX, 1-OFF  
- Jackpots: All prize tiers
"""

import os
import sys
import json
import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Lottery Winning Logic
def check_cash3_win(predicted, actual):
    pred_str, actual_str = str(predicted).zfill(3), str(actual).zfill(3)
    wins, payout = [], 0
    
    if pred_str == actual_str:
        wins.append('STRAIGHT'); payout = 500
    elif sorted(pred_str) == sorted(actual_str):
        wins.append('BOX'); payout = 160 if len(set(pred_str)) == 2 else 80
    
    if pred_str[:2] == actual_str[:2]: wins.append('FRONT_PAIR'); payout = max(payout, 50)
    if pred_str[1:] == actual_str[1:]: wins.append('BACK_PAIR'); payout = max(payout, 50)
    
    if all(abs(int(pred_str[i]) - int(actual_str[i])) <= 1 for i in range(3)) and pred_str != actual_str:
        wins.append('1-OFF'); payout = max(payout, 9)
    
    return wins, payout

def check_cash4_win(predicted, actual):
    pred_str, actual_str = str(predicted).zfill(4), str(actual).zfill(4)
    wins, payout = [], 0
    
    if pred_str == actual_str:
        wins.append('STRAIGHT'); payout = 5000
    elif sorted(pred_str) == sorted(actual_str):
        wins.append('BOX')
        unique = len(set(pred_str))
        payout = {4: 200, 3: 400, 2: 800, 1: 1200}.get(unique, 200)
    
    if all(abs(int(pred_str[i]) - int(actual_str[i])) <= 1 for i in range(4)) and pred_str != actual_str:
        wins.append('1-OFF'); payout = max(payout, 18)
    
    return wins, payout

# Load historical data
def load_historical_data():
    print("="*80)
    print("LOADING HISTORICAL DATA")
    print("="*80)
    
    all_results = []
    
    # Cash3 Jan-Aug
    cash3_file = os.path.join(PROJECT_ROOT, 'data', 'results', 'ga_results', 'Cash3_2025 Jan-Aug 2025.txt')
    if os.path.exists(cash3_file):
        print(f"Loading: {cash3_file}")
        try:
            with open(cash3_file, 'r', encoding='latin-1') as f:
                for line in f.readlines()[1:]:
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        try:
                            date_obj = datetime.strptime(parts[1].strip(), '%m/%d/%Y')
                            all_results.append({
                                'date': date_obj.strftime('%Y-%m-%d'),
                                'game': 'Cash3',
                                'session': parts[2].strip().upper(),
                                'winning_number': parts[3].strip()
                            })
                        except: pass
            print(f"  Loaded {len([r for r in all_results if r['game']=='Cash3'])} Cash3 draws")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Cash4 Jan-Aug
    cash4_file = os.path.join(PROJECT_ROOT, 'data', 'results', 'ga_results', 'Cash4 Jan_Aug2025.txt')
    if os.path.exists(cash4_file):
        print(f"Loading: {cash4_file}")
        try:
            with open(cash4_file, 'r', encoding='latin-1') as f:
                for line in f.readlines()[1:]:
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        try:
                            date_obj = datetime.strptime(parts[1].strip(), '%m/%d/%Y')
                            all_results.append({
                                'date': date_obj.strftime('%Y-%m-%d'),
                                'game': 'Cash4',
                                'session': parts[2].strip().upper(),
                                'winning_number': parts[3].strip()
                            })
                        except: pass
            print(f"  Loaded {len([r for r in all_results if r['game']=='Cash4'])} Cash4 draws")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # CSV files  
    for csv_file, game in [('cash3_results.csv', 'Cash3'), ('cash4_results.csv', 'Cash4')]:
        path = os.path.join(PROJECT_ROOT, 'data', 'results', 'ga_results', csv_file)
        if os.path.exists(path):
            print(f"Loading: {path}")
            try:
                df = pd.read_csv(path)
                for _, row in df.iterrows():
                    date_obj = pd.to_datetime(row['draw_date'])
                    all_results.append({
                        'date': date_obj.strftime('%Y-%m-%d'),
                        'game': game,
                        'session': row['session'].upper(),
                        'winning_number': str(row['digits'])
                    })
                print(f"  Loaded {len(df)} {game} draws")
            except Exception as e:
                print(f"  ERROR: {e}")
    
    df = pd.DataFrame(all_results).drop_duplicates(subset=['date', 'game', 'session'])
    print(f"\n{'='*80}")
    print(f"TOTAL: {len(df)} draws | {df['date'].min()} to {df['date'].max()}")
    print(f"Cash3: {len(df[df['game']=='Cash3'])} | Cash4: {len(df[df['game']=='Cash4'])}")
    print("="*80)
    return df

# Audit single subscriber
def audit_subscriber(kit, sub_id, historical_df):
    # Find output directory
    output_pattern = f'{kit}_{sub_id}_*'
    matches = list(Path(os.path.join(PROJECT_ROOT, 'outputs')).glob(output_pattern))
    if not matches: return None
    
    output_dir = matches[0]
    wins, misses, total_payout = 0, 0, 0
    win_types_count = defaultdict(int)
    games_tested = defaultdict(lambda: {'wins': 0, 'total': 0, 'payout': 0})
    
    # Process each day
    for json_file in output_dir.glob('2025-*.json'):
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            date = data.get('date')
            picks = data.get('picks', {})
            
            # Cash3
            if 'Cash3' in picks:
                for pred in picks['Cash3'].get('lane_system', []):
                    for session in ['MIDDAY', 'EVENING', 'NIGHT']:
                        match = historical_df[
                            (historical_df['date'] == date) &
                            (historical_df['game'] == 'Cash3') &
                            (historical_df['session'] == session)
                        ]
                        if len(match) > 0:
                            actual = match.iloc[0]['winning_number']
                            win_list, payout = check_cash3_win(pred, actual)
                            games_tested['Cash3']['total'] += 1
                            if win_list:
                                wins += 1
                                total_payout += payout
                                games_tested['Cash3']['wins'] += 1
                                games_tested['Cash3']['payout'] += payout
                                for w in win_list: win_types_count[w] += 1
                            else:
                                misses += 1
            
            # Cash4
            if 'Cash4' in picks:
                for pred in picks['Cash4'].get('lane_system', []):
                    for session in ['MIDDAY', 'EVENING', 'NIGHT']:
                        match = historical_df[
                            (historical_df['date'] == date) &
                            (historical_df['game'] == 'Cash4') &
                            (historical_df['session'] == session)
                        ]
                        if len(match) > 0:
                            actual = match.iloc[0]['winning_number']
                            win_list, payout = check_cash4_win(pred, actual)
                            games_tested['Cash4']['total'] += 1
                            if win_list:
                                wins += 1
                                total_payout += payout
                                games_tested['Cash4']['wins'] += 1
                                games_tested['Cash4']['payout'] += payout
                                for w in win_list: win_types_count[w] += 1
                            else:
                                misses += 1
        except: pass
    
    total_plays = wins + misses
    if total_plays == 0: return None
    
    return {
        'subscriber_id': sub_id,
        'kit': kit,
        'total_plays': total_plays,
        'wins': wins,
        'misses': misses,
        'win_rate': (wins / total_plays * 100),
        'total_payout': total_payout,
        'total_spent': total_plays,
        'roi': ((total_payout - total_plays) / total_plays * 100),
        'win_breakdown': dict(win_types_count),
        'by_game': dict(games_tested)
    }

# Main audit
def run_audit():
    print("\n" + "="*80)
    print("LOTTERY WINNING AUDIT v3.7")
    print("="*80)
    
    historical_df = load_historical_data()
    if len(historical_df) == 0:
        print("ERROR: No historical data!")
        return
    
    all_results = []
    
    for kit in ['BOOK3', 'BOOK', 'BOSK']:
        kit_dir = os.path.join(PROJECT_ROOT, 'data', 'subscribers', f'{kit}_TEST')
        if not os.path.exists(kit_dir): continue
        
        print(f"\n{'='*80}")
        print(f"AUDITING {kit}")
        print(f"{'='*80}")
        
        subscribers = list(Path(kit_dir).glob('*.json'))
        print(f"Found {len(subscribers)} subscribers")
        
        for idx, sub_file in enumerate(subscribers, 1):
            if idx % 100 == 0:
                print(f"  Progress: {idx}/{len(subscribers)}")
            
            sub_id = sub_file.stem
            result = audit_subscriber(kit, sub_id, historical_df)
            if result:
                all_results.append(result)
                
                # Save individual result
                output_dir = os.path.join(PROJECT_ROOT, 'audit_results', 'by_subscriber', kit)
                os.makedirs(output_dir, exist_ok=True)
                with open(os.path.join(output_dir, f'{sub_id}_audit.json'), 'w') as f:
                    json.dump(result, f, indent=2)
    
    # Generate summary
    if not all_results:
        print("\nNO RESULTS TO AUDIT!")
        return
    
    print(f"\n{'='*80}")
    print("AUDIT COMPLETE - SUMMARY")
    print(f"{'='*80}")
    print(f"Subscribers Audited: {len(all_results)}")
    print(f"Total Plays: {sum(r['total_plays'] for r in all_results):,}")
    print(f"Total Wins: {sum(r['wins'] for r in all_results):,}")
    print(f"Total Payout: ${sum(r['total_payout'] for r in all_results):,.2f}")
    print(f"Average Win Rate: {sum(r['win_rate'] for r in all_results)/len(all_results):.2f}%")
    print(f"Average ROI: {sum(r['roi'] for r in all_results)/len(all_results):.2f}%")
    
    # Save summary
    summary = {
        'audit_date': datetime.now().isoformat(),
        'total_subscribers': len(all_results),
        'total_plays': sum(r['total_plays'] for r in all_results),
        'total_wins': sum(r['wins'] for r in all_results),
        'total_payout': sum(r['total_payout'] for r in all_results),
        'avg_win_rate': sum(r['win_rate'] for r in all_results)/len(all_results),
        'avg_roi': sum(r['roi'] for r in all_results)/len(all_results)
    }
    
    with open(os.path.join(PROJECT_ROOT, 'audit_results', 'audit_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to: {os.path.join(PROJECT_ROOT, 'audit_results')}")
    print("="*80)

if __name__ == '__main__':
    run_audit()
