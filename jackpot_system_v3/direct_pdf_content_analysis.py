#!/usr/bin/env python3
"""
direct_pdf_content_analysis.py
=============================

Direct analysis of PDF content to understand the lottery data structure
"""

import re
import os

def analyze_pdf_content():
    """Analyze raw PDF content to find lottery patterns"""
    
    pdf_files = [
        r"c:\Users\suppo\Downloads\GA_Lottery_WinningNumbers (50).pdf",
        r"c:\Users\suppo\Downloads\GA_Lottery_WinningNumbers (51).pdf"
    ]
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"⚠️  PDF not found: {pdf_file}")
            continue
            
        print(f"\n🔍 ANALYZING: {pdf_file}")
        print("=" * 60)
        
        with open(pdf_file, 'rb') as file:
            content = file.read().decode('latin-1', errors='ignore')
        
        # Look for text patterns that might indicate lottery data
        lines = content.split('\n')
        
        print("📄 Sample decoded content from PDF:")
        
        # Show lines that might contain lottery data
        potential_lottery_lines = []
        
        for i, line in enumerate(lines):
            # Look for lines with multiple digits or lottery-related keywords
            if re.search(r'\d+.*\d+', line) or any(keyword in line.lower() for keyword in ['cash', 'lottery', 'draw', 'ball', 'power', 'mega']):
                potential_lottery_lines.append((i, line))
        
        if potential_lottery_lines:
            print(f"Found {len(potential_lottery_lines)} potential lottery lines:")
            for i, (line_num, line) in enumerate(potential_lottery_lines[:10]):  # Show first 10
                print(f"{i+1:2d}. Line {line_num:4d}: {line[:80]}")
                if i == 9 and len(potential_lottery_lines) > 10:
                    print(f"    ... and {len(potential_lottery_lines) - 10} more lines")
        
        # Specifically look for the hex patterns we know contain digits
        print(f"\n🎯 HEX PATTERN DECODING:")
        
        # Extract known digit patterns
        digit_patterns = re.findall(r'<2[1-9a-f][0-9a-f]*>', content)
        
        for pattern in digit_patterns[:10]:  # Show first 10
            hex_content = pattern.strip('<>')
            
            # Apply our discovered mapping (0x21 = '0', 0x22 = '1', etc.)
            decoded = ""
            hex_pairs = [hex_content[i:i+2] for i in range(0, len(hex_content), 2)]
            
            for pair in hex_pairs:
                try:
                    byte_val = int(pair, 16)
                    if 0x21 <= byte_val <= 0x2a:  # Our digit range
                        decoded += str(byte_val - 0x21)
                    elif 0x30 <= byte_val <= 0x39:  # Standard ASCII digits  
                        decoded += chr(byte_val)
                    elif byte_val == 0x2f:  # Forward slash
                        decoded += "/"
                    elif byte_val == 0x2d:  # Dash
                        decoded += "-"
                    elif byte_val == 0x2b:  # Plus
                        decoded += "+"
                    elif byte_val == 0x20:  # Space
                        decoded += " "
                    else:
                        decoded += f"[{pair}]"
                except:
                    decoded += f"[{pair}]"
            
            print(f"  {pattern} -> '{decoded}'")
        
        # Look for patterns that suggest date/time or lottery structure
        print(f"\n📅 LOOKING FOR DATE PATTERNS:")
        date_patterns = re.findall(r'<[0-9a-f]+>', content)
        
        for pattern in date_patterns:
            decoded = pattern
            hex_content = pattern.strip('<>')
            
            # Try to decode as potential date
            if len(hex_content) >= 8:  # Enough for date
                decoded_chars = ""
                hex_pairs = [hex_content[i:i+2] for i in range(0, len(hex_content), 2)]
                
                has_date_like = False
                for pair in hex_pairs:
                    try:
                        byte_val = int(pair, 16)
                        if 0x21 <= byte_val <= 0x2a:
                            decoded_chars += str(byte_val - 0x21)
                        elif byte_val == 0x2f:  # Forward slash for dates
                            decoded_chars += "/"
                            has_date_like = True
                        elif byte_val == 0x2d:  # Dash for dates
                            decoded_chars += "-" 
                            has_date_like = True
                        else:
                            decoded_chars += f"[{pair}]"
                    except:
                        decoded_chars += f"[{pair}]"
                
                if has_date_like or re.search(r'\d+/\d+|\d+-\d+', decoded_chars):
                    print(f"  Potential date: {pattern} -> '{decoded_chars}'")
        
        # Try to find actual lottery number sequences
        print(f"\n🎲 SEARCHING FOR LOTTERY SEQUENCES:")
        
        # Look for sequences that could be 5 numbers for Cash4Life
        sequences = re.findall(r'<[0-9a-f]+>\s*<[0-9a-f]+>\s*<[0-9a-f]+>\s*<[0-9a-f]+>\s*<[0-9a-f]+>', content)
        
        if sequences:
            print(f"Found {len(sequences)} potential 5-number sequences:")
            for i, seq in enumerate(sequences[:5]):
                print(f"  {i+1}. {seq}")
                
                # Try to decode the sequence
                patterns = re.findall(r'<[0-9a-f]+>', seq)
                decoded_numbers = []
                
                for pattern in patterns:
                    hex_content = pattern.strip('<>')
                    if len(hex_content) == 2:  # Single byte
                        try:
                            byte_val = int(hex_content, 16)
                            if 0x21 <= byte_val <= 0x2a:
                                decoded_numbers.append(str(byte_val - 0x21))
                            elif 0x30 <= byte_val <= 0x39:
                                decoded_numbers.append(chr(byte_val))
                        except:
                            pass
                
                if decoded_numbers:
                    print(f"     Decoded: {', '.join(decoded_numbers)}")

if __name__ == "__main__":
    analyze_pdf_content()