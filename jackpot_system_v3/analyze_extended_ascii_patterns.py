#!/usr/bin/env python3
"""
analyze_extended_ascii_patterns.py
==================================

Analyze the extended ASCII patterns that look like real lottery numbers
"""

import json

def analyze_patterns():
    """Analyze raw decoded lines for real lottery patterns"""
    
    with open('december_lottery_extracted_data.json', 'r') as f:
        data = json.load(f)
    
    print('🔍 ANALYZING RAW DECODED LINES FOR REAL LOTTERY PATTERNS:')
    print('=' * 60)
    
    # Show lines that look like they contain real lottery numbers
    real_patterns = []
    for i, line in enumerate(data['raw_decoded_lines']):
        # Look for patterns that contain numbers in realistic lottery ranges
        if any(c in line for c in ':;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ') and len(line) >= 3:
            real_patterns.append((i, line))
    
    print(f'Found {len(real_patterns)} lines with extended ASCII patterns:')
    
    potential_lottery_draws = []
    
    for i, (idx, line) in enumerate(real_patterns[:30]):  # Check first 30
        print(f'{i+1:2d}. Line {idx:3d}: "{line}"')
        
        # Decode this specific pattern
        numbers = []
        for char in line:
            if char.isdigit():
                numbers.append(int(char))
            else:
                ascii_val = ord(char)
                if ascii_val == ord(':'):
                    numbers.append(10)
                elif ascii_val == ord(';'):
                    numbers.append(11) 
                elif ascii_val == ord('<'):
                    numbers.append(12)
                elif ascii_val == ord('='):
                    numbers.append(13)
                elif ascii_val == ord('>'):
                    numbers.append(14)
                elif ascii_val == ord('?'):
                    numbers.append(15)
                elif ascii_val == ord('@'):
                    numbers.append(16)
                elif 65 <= ascii_val <= 90:  # A-Z (17-42)
                    numbers.append(ascii_val - 65 + 17)
                elif 97 <= ascii_val <= 122:  # a-z (43-68)
                    numbers.append(ascii_val - 97 + 43)
        
        if numbers:
            valid_cash4life = [n for n in numbers if 1 <= n <= 60]
            valid_powerball = [n for n in numbers if 1 <= n <= 69]
            valid_megamillions = [n for n in numbers if 1 <= n <= 70]
            
            print(f'    -> Decoded: {numbers}')
            
            if len(valid_cash4life) >= 5:
                main = valid_cash4life[:5]
                cash_ball = valid_cash4life[5] if len(valid_cash4life) > 5 and valid_cash4life[5] <= 4 else 1
                combination = f"{'-'.join(map(str, sorted(main)))}+{cash_ball}"
                potential_lottery_draws.append({
                    'type': 'Cash4Life',
                    'combination': combination,
                    'main': main,
                    'bonus': cash_ball,
                    'source': line,
                    'all_numbers': numbers
                })
                print(f'    -> Cash4Life: {combination}')
            
            if len(valid_powerball) >= 6:
                main = valid_powerball[:5]
                power = valid_powerball[5] if valid_powerball[5] <= 26 else valid_powerball[-1] if valid_powerball[-1] <= 26 else 1
                combination = f"{'-'.join(map(str, sorted(main)))}+{power}"
                potential_lottery_draws.append({
                    'type': 'Powerball',
                    'combination': combination,
                    'main': main,
                    'bonus': power,
                    'source': line,
                    'all_numbers': numbers
                })
                print(f'    -> Powerball: {combination}')
            
            if len(valid_megamillions) >= 6:
                main = valid_megamillions[:5]
                mega = valid_megamillions[5] if valid_megamillions[5] <= 25 else valid_megamillions[-1] if valid_megamillions[-1] <= 25 else 1
                combination = f"{'-'.join(map(str, sorted(main)))}+{mega}"
                potential_lottery_draws.append({
                    'type': 'MegaMillions',
                    'combination': combination,
                    'main': main,
                    'bonus': mega,
                    'source': line,
                    'all_numbers': numbers
                })
                print(f'    -> MegaMillions: {combination}')
        
        print()
    
    # Summary of found lottery draws
    print(f"\n🎯 POTENTIAL LOTTERY DRAWS IDENTIFIED:")
    print("=" * 50)
    
    cash4life_draws = [d for d in potential_lottery_draws if d['type'] == 'Cash4Life']
    powerball_draws = [d for d in potential_lottery_draws if d['type'] == 'Powerball']
    megamillions_draws = [d for d in potential_lottery_draws if d['type'] == 'MegaMillions']
    
    print(f"Cash4Life: {len(cash4life_draws)} draws found")
    for i, draw in enumerate(cash4life_draws):
        print(f"  {i+1}. {draw['combination']} (from: {draw['source']})")
    
    print(f"\nPowerball: {len(powerball_draws)} draws found")
    for i, draw in enumerate(powerball_draws):
        print(f"  {i+1}. {draw['combination']} (from: {draw['source']})")
    
    print(f"\nMegaMillions: {len(megamillions_draws)} draws found")
    for i, draw in enumerate(megamillions_draws):
        print(f"  {i+1}. {draw['combination']} (from: {draw['source']})")
    
    # Test adjacent enhancement on any Cash4Life draws found
    if cash4life_draws:
        print(f"\n🎯 TESTING ADJACENT ENHANCEMENT ON REAL CASH4LIFE DATA:")
        print("=" * 60)
        
        try:
            from adjacent_number_enhancement_v3_7 import enhance_cash4life_prediction
            
            for i, draw in enumerate(cash4life_draws[:3]):  # Test first 3
                actual_numbers = draw['main']
                print(f"\nTest {i+1}: Actual Cash4Life draw: {actual_numbers}")
                
                # Create a prediction that's slightly off
                test_prediction = [(n - 1) if n > 1 else (n + 1) for n in actual_numbers]
                enhanced_prediction = enhance_cash4life_prediction(test_prediction)
                
                original_matches = len(set(test_prediction) & set(actual_numbers))
                enhanced_matches = len(set(enhanced_prediction) & set(actual_numbers))
                
                print(f"  Original prediction: {test_prediction} -> {original_matches} matches")
                print(f"  Enhanced prediction: {enhanced_prediction} -> {enhanced_matches} matches")
                print(f"  Improvement: {'✅ YES' if enhanced_matches > original_matches else '❌ NO'}")
                
        except ImportError:
            print("⚠️  Adjacent enhancement module not available")
    
    return potential_lottery_draws

if __name__ == "__main__":
    results = analyze_patterns()
    print(f"\n🎉 Analysis complete! Found {len(results)} potential lottery draws")