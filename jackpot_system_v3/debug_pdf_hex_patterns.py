#!/usr/bin/env python3
"""
debug_pdf_hex_patterns.py
=========================

Debug script to examine the exact hex patterns in the Georgia lottery PDFs
and create proper mapping for lottery number extraction.
"""

import re
import os
from pathlib import Path

def extract_hex_patterns(pdf_path: str):
    """Extract and analyze hex patterns from PDF"""
    print(f"\n🔍 ANALYZING: {pdf_path}")
    print("=" * 60)
    
    try:
        with open(pdf_path, 'rb') as file:
            content = file.read().decode('latin-1', errors='ignore')
        
        # Find all hex patterns with their context
        hex_patterns = re.findall(r'<[0-9a-fA-F]+>', content)
        
        print(f"Found {len(hex_patterns)} hex patterns")
        
        # Show unique patterns with length analysis
        unique_patterns = {}
        for pattern in hex_patterns:
            if pattern not in unique_patterns:
                unique_patterns[pattern] = 1
            else:
                unique_patterns[pattern] += 1
        
        # Sort by frequency and show top patterns
        sorted_patterns = sorted(unique_patterns.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\nTop 20 most frequent hex patterns:")
        for i, (pattern, count) in enumerate(sorted_patterns[:20]):
            print(f"{i+1:2d}. {pattern:<20} (appears {count:3d} times)")
        
        # Look for lottery-specific patterns
        print(f"\n🎯 POTENTIAL LOTTERY PATTERNS:")
        lottery_candidates = []
        
        for pattern in unique_patterns:
            # Look for patterns that might contain lottery data
            hex_content = pattern.strip('<>')
            if len(hex_content) >= 10:  # Longer patterns more likely to contain numbers
                lottery_candidates.append((pattern, len(hex_content), unique_patterns[pattern]))
        
        # Sort by length and frequency
        lottery_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        for i, (pattern, length, count) in enumerate(lottery_candidates[:10]):
            print(f"{i+1:2d}. {pattern} (length: {length}, count: {count})")
        
        # Try to decode some patterns manually
        print(f"\n🔬 MANUAL HEX DECODING ATTEMPTS:")
        
        test_patterns = [
            '<2122232425262728292a>',  # From the PDF content
            '<2b272c2c272c2d2a>',
            '<2e2f3031293223>',
            '<33223429>',
            '<212223242a>',
            '<35223636>',
        ]
        
        for pattern in test_patterns:
            if pattern in unique_patterns:
                hex_content = pattern.strip('<>')
                
                # Try different decoding approaches
                print(f"\nPattern: {pattern}")
                
                # Approach 1: Direct ASCII conversion
                try:
                    ascii_bytes = bytes.fromhex(hex_content)
                    ascii_text = ascii_bytes.decode('ascii', errors='ignore')
                    print(f"  ASCII: '{ascii_text}'")
                except:
                    print(f"  ASCII: Failed")
                
                # Approach 2: Manual digit mapping
                digit_mapping = {
                    '21': '0', '22': '1', '23': '2', '24': '3', '25': '4',
                    '26': '5', '27': '6', '28': '7', '29': '8', '2a': '9'
                }
                
                hex_pairs = [hex_content[i:i+2] for i in range(0, len(hex_content), 2)]
                mapped_text = ""
                for pair in hex_pairs:
                    if pair.lower() in digit_mapping:
                        mapped_text += digit_mapping[pair.lower()]
                    else:
                        mapped_text += f"[{pair}]"
                
                print(f"  Digit mapping: '{mapped_text}'")
        
        return unique_patterns
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return {}

def main():
    """Debug PDF hex patterns"""
    
    print("🔬 PDF HEX PATTERN ANALYSIS")
    print("=" * 50)
    
    pdf_files = [
        r"c:\Users\suppo\Downloads\GA_Lottery_WinningNumbers (50).pdf",
        r"c:\Users\suppo\Downloads\GA_Lottery_WinningNumbers (51).pdf"
    ]
    
    all_patterns = {}
    
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            patterns = extract_hex_patterns(pdf_file)
            
            # Merge patterns
            for pattern, count in patterns.items():
                if pattern in all_patterns:
                    all_patterns[pattern] += count
                else:
                    all_patterns[pattern] = count
        else:
            print(f"⚠️  PDF not found: {pdf_file}")
    
    print(f"\n📊 COMBINED ANALYSIS:")
    print(f"Total unique hex patterns: {len(all_patterns)}")
    
    # Show the exact patterns we saw in the PDF content
    target_patterns = [
        '<2122232425262728292a>',  # This was in the header
        '<2b272c2c272c2d2a>',
        '<2e2f3031293223>',
    ]
    
    print(f"\n🎯 TARGET PATTERN ANALYSIS:")
    for pattern in target_patterns:
        if pattern in all_patterns:
            print(f"{pattern} - Found {all_patterns[pattern]} times")
            
            # Try comprehensive decoding
            hex_content = pattern.strip('<>')
            hex_pairs = [hex_content[i:i+2] for i in range(0, len(hex_content), 2)]
            
            print(f"  Hex pairs: {hex_pairs}")
            
            # Try different offset mappings for digits
            for offset in range(0x21, 0x31):  # Try different base offsets
                decoded = ""
                for pair in hex_pairs:
                    try:
                        byte_val = int(pair, 16)
                        if offset <= byte_val <= offset + 9:
                            decoded += str(byte_val - offset)
                        else:
                            decoded += "?"
                    except:
                        decoded += "X"
                
                if all(c.isdigit() or c in "?" for c in decoded):
                    print(f"  Offset 0x{offset:02x}: '{decoded}'")
        else:
            print(f"{pattern} - NOT FOUND")

if __name__ == "__main__":
    main()