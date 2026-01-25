#!/usr/bin/env python3
import json
from pathlib import Path

outputs_dir = Path('outputs')
test_dir = outputs_dir / 'BOOK3_TEST_TEST0001_2025-12-22_to_2025-12-31'

with open(test_dir / '2025-12-23.json', 'r') as f:
    data = json.load(f)

print('📊 TEST0001 PREDICTIONS:')
print(f'Overall Score: {data["score"]:.1f}')
print('🎯 Games & Predictions:')
for game, picks in data['picks'].items():
    predictions = picks.get('lane_system', [])
    print(f'  • {game}: {predictions}')

print('\n📈 Score Components:')
for component, score in data['score_components'].items():
    print(f'  • {component}: {score:.1f}')

print(f'\n🎯 PREDICTION SUMMARY:')
print(f'  • Cash3: {data["picks"]["Cash3"]["lane_system"]}')
print(f'  • Cash4: {data["picks"]["Cash4"]["lane_system"]}') 
print(f'  • MegaMillions: {data["picks"]["MegaMillions"]["lane_system"]}')
print(f'  • Powerball: {data["picks"]["Powerball"]["lane_system"]}')
print(f'  • Cash4Life: {data["picks"]["Cash4Life"]["lane_system"]}')