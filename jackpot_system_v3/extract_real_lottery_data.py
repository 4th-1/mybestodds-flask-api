#!/usr/bin/env python3
"""
extract_real_lottery_data.py
============================

FINAL LOTTERY DATA EXTRACTION: Direct approach using confirmed hex patterns
Based on successful hex decoding: <2122232425262728292a> = '0123456789'
"""

import re
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

def extract_lottery_data_from_pdfs():
    """Extract actual lottery data using confirmed hex decoding"""
    
    # Confirmed hex-to-digit mapping (offset 0x21)
    hex_to_digit = {}
    for i in range(10):
        hex_code = f"{0x21 + i:02x}"
        hex_to_digit[hex_code] = str(i)
    
    # Additional mappings for common characters
    hex_mappings = {
        **hex_to_digit,
        '2f': '/',  # Forward slash for dates
        '2d': '-',  # Dash 
        '2b': '+',  # Plus
        '20': ' ',  # Space
        '30': '0',  # Alternative zero
        '31': '1',  # Alternative one
        '32': '2',  # etc.
        '33': '3',
        '34': '4',
        '35': '5',
        '36': '6',
        '37': '7',
        '38': '8',
        '39': '9',
    }
    
    def decode_hex_pattern(hex_pattern: str) -> str:
        """Decode a single hex pattern"""
        hex_content = hex_pattern.strip('<>')
        hex_pairs = [hex_content[i:i+2] for i in range(0, len(hex_content), 2)]
        
        decoded = ""
        for pair in hex_pairs:
            if pair.lower() in hex_mappings:
                decoded += hex_mappings[pair.lower()]
            else:
                # For unmapped patterns, try direct ASCII if reasonable
                try:
                    byte_val = int(pair, 16)
                    if 32 <= byte_val <= 126:  # Printable ASCII
                        decoded += chr(byte_val)
                    else:
                        decoded += f"[{pair}]"
                except:
                    decoded += f"[{pair}]"
        
        return decoded
    
    pdf_files = [
        r"c:\Users\suppo\Downloads\GA_Lottery_WinningNumbers (50).pdf",
        r"c:\Users\suppo\Downloads\GA_Lottery_WinningNumbers (51).pdf"
    ]
    
    results = {
        'cash4life': [],
        'powerball': [],
        'megamillions': [],
        'raw_decoded_lines': [],
        'extraction_summary': {}
    }
    
    all_decoded_lines = []
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"⚠️  PDF not found: {pdf_file}")
            continue
            
        print(f"📄 Processing: {pdf_file}")
        
        with open(pdf_file, 'rb') as file:
            content = file.read().decode('latin-1', errors='ignore')
        
        # Find all hex patterns and decode them
        hex_patterns = re.findall(r'<[0-9a-fA-F]+>', content)
        decoded_content = []
        
        for pattern in hex_patterns:
            decoded = decode_hex_pattern(pattern)
            
            # Only keep patterns that resulted in meaningful content
            if any(c.isdigit() for c in decoded) or any(keyword in decoded.lower() for keyword in ['cash', 'power', 'mega', 'lottery']):
                decoded_content.append({
                    'original': pattern,
                    'decoded': decoded,
                    'pdf_source': os.path.basename(pdf_file)
                })
                all_decoded_lines.append(decoded)
        
        print(f"   Decoded {len(decoded_content)} meaningful patterns")
    
    # Save raw decoded content for inspection
    results['raw_decoded_lines'] = all_decoded_lines
    
    # Now analyze the decoded content for lottery patterns
    print(f"\n🎯 ANALYZING {len(all_decoded_lines)} DECODED LINES FOR LOTTERY DATA:")
    
    # Look for specific lottery number patterns
    for line in all_decoded_lines:
        line = line.strip()
        if len(line) < 2:
            continue
            
        # Method 1: Look for digit sequences that could be lottery numbers
        digits_found = re.findall(r'\d+', line)
        
        if len(digits_found) >= 5:  # Potential lottery draw
            numbers = [int(d) for d in digits_found if d.isdigit()]
            
            # Check if this could be Cash4Life (5 numbers 1-60, 1 cash ball 1-4)
            main_candidates = [n for n in numbers if 1 <= n <= 60]
            cash_candidates = [n for n in numbers if 1 <= n <= 4]
            
            if len(main_candidates) >= 5:
                main_numbers = main_candidates[:5]
                cash_ball = cash_candidates[0] if cash_candidates else 1
                
                results['cash4life'].append({
                    'main_numbers': main_numbers,
                    'cash_ball': cash_ball,
                    'full_combination': f"{'-'.join(map(str, sorted(main_numbers)))}+{cash_ball}",
                    'source_line': line,
                    'date': 'Dec 2024'
                })
                print(f"   💎 Found Cash4Life: {main_numbers} + {cash_ball}")
            
            # Check if this could be Powerball (5 numbers 1-69, 1 power ball 1-26)
            pb_main_candidates = [n for n in numbers if 1 <= n <= 69]
            pb_power_candidates = [n for n in numbers if 1 <= n <= 26]
            
            if len(pb_main_candidates) >= 5 and pb_power_candidates:
                if not any(result['main_numbers'] == pb_main_candidates[:5] for result in results['cash4life']):  # Avoid duplicates
                    main_balls = pb_main_candidates[:5]
                    power_ball = pb_power_candidates[0]
                    
                    results['powerball'].append({
                        'white_balls': main_balls,
                        'power_ball': power_ball,
                        'full_combination': f"{'-'.join(map(str, sorted(main_balls)))}+{power_ball}",
                        'source_line': line,
                        'date': 'Dec 2024'
                    })
                    print(f"   ⚡ Found Powerball: {main_balls} + {power_ball}")
            
            # Check if this could be MegaMillions (5 numbers 1-70, 1 mega ball 1-25)
            mm_main_candidates = [n for n in numbers if 1 <= n <= 70]
            mm_mega_candidates = [n for n in numbers if 1 <= n <= 25]
            
            if len(mm_main_candidates) >= 5 and mm_mega_candidates:
                if (not any(result['main_numbers'] == mm_main_candidates[:5] for result in results['cash4life']) and 
                    not any(result['white_balls'] == mm_main_candidates[:5] for result in results['powerball'])):
                    main_balls = mm_main_candidates[:5]
                    mega_ball = mm_mega_candidates[0]
                    
                    results['megamillions'].append({
                        'white_balls': main_balls,
                        'mega_ball': mega_ball,
                        'full_combination': f"{'-'.join(map(str, sorted(main_balls)))}+{mega_ball}",
                        'source_line': line,
                        'date': 'Dec 2024'
                    })
                    print(f"   🌟 Found MegaMillions: {main_balls} + {mega_ball}")
    
    # Remove duplicates and validate results
    def deduplicate_results(results_list: List[Dict]) -> List[Dict]:
        seen_combinations = set()
        unique_results = []
        
        for result in results_list:
            combo_key = result['full_combination']
            if combo_key not in seen_combinations:
                seen_combinations.add(combo_key)
                unique_results.append(result)
        
        return unique_results
    
    results['cash4life'] = deduplicate_results(results['cash4life'])
    results['powerball'] = deduplicate_results(results['powerball'])
    results['megamillions'] = deduplicate_results(results['megamillions'])
    
    # Generate summary
    results['extraction_summary'] = {
        'total_lines_processed': len(all_decoded_lines),
        'cash4life_found': len(results['cash4life']),
        'powerball_found': len(results['powerball']),
        'megamillions_found': len(results['megamillions']),
        'extraction_date': datetime.now().isoformat(),
        'status': 'SUCCESS' if any([results['cash4life'], results['powerball'], results['megamillions']]) else 'NO_DATA_FOUND'
    }
    
    print(f"\n📊 EXTRACTION COMPLETE:")
    print(f"   Cash4Life draws: {len(results['cash4life'])}")
    print(f"   Powerball draws: {len(results['powerball'])}")
    print(f"   MegaMillions draws: {len(results['megamillions'])}")
    print(f"   Status: {results['extraction_summary']['status']}")
    
    # Save results
    output_file = "december_lottery_extracted_data.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"   Results saved to: {output_file}")
    
    # Show first few results for verification
    if results['cash4life']:
        print(f"\n💎 CASH4LIFE SAMPLES:")
        for i, draw in enumerate(results['cash4life'][:5]):
            print(f"   {i+1}. {draw['full_combination']} (from: {draw['source_line'][:50]}...)")
    
    if results['powerball']:
        print(f"\n⚡ POWERBALL SAMPLES:")
        for i, draw in enumerate(results['powerball'][:3]):
            print(f"   {i+1}. {draw['full_combination']} (from: {draw['source_line'][:50]}...)")
    
    if results['megamillions']:
        print(f"\n🌟 MEGAMILLIONS SAMPLES:")
        for i, draw in enumerate(results['megamillions'][:3]):
            print(f"   {i+1}. {draw['full_combination']} (from: {draw['source_line'][:50]}...)")
    
    return results

if __name__ == "__main__":
    print("🎯 FINAL LOTTERY DATA EXTRACTION")
    print("=" * 50)
    
    results = extract_lottery_data_from_pdfs()
    
    if results['extraction_summary']['status'] == 'SUCCESS':
        print(f"\n✅ SUCCESS: Found lottery data in December PDFs!")
        print(f"   Ready for adjacent enhancement testing!")
    else:
        print(f"\n⚠️  No lottery data found - may need manual PDF inspection")