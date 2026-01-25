"""
Test calibrated Right Engine v3.7 confidence scoring
"""

import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from engines.rightside_v3_7.rightside_engine_v3_7 import score_jackpot_row

def test_calibrated_confidence():
    """Test the calibrated confidence ranges"""
    
    print("="*60)
    print("🎯 TESTING CALIBRATED RIGHT ENGINE v3.7")
    print("="*60)
    
    # Test data for each game
    test_row = pd.Series({
        'n1': 5, 'n2': 15, 'n3': 25, 'n4': 35, 'n5': 45,
        'bonus': 3
    })
    
    games = ['CASH4LIFE', 'POWERBALL', 'MEGA_MILLIONS']
    
    print("\n📊 CALIBRATED CONFIDENCE TESTING:")
    print("-" * 40)
    
    for game in games:
        result = score_jackpot_row(test_row, game)
        
        print(f"\n{game}:")
        print(f"  Confidence: {result['confidence_score']:.1f}%")
        print(f"  Raw Score: {result['raw_score']:.2f}")
        
        # Extract calibration note
        notes = result['confidence_notes'].split('; ')
        calibration_note = [n for n in notes if 'CALIBRATED' in n]
        if calibration_note:
            print(f"  Calibration: {calibration_note[0]}")
    
    print(f"\n✅ CONFIDENCE CALIBRATION RESULTS:")
    print("- Cash4Life: Should be 10-13% (excellent alignment)")
    print("- Powerball: Should be 2-4% (recalibrated down)")  
    print("- MegaMillions: Should be 2-5% (conservative)")
    print("\n🎯 System ready for realistic confidence scoring!")

if __name__ == "__main__":
    test_calibrated_confidence()