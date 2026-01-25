"""
CONFIDENCE SCORE ALIGNMENT ANALYSIS v3.7
Comparing Enhanced Right Engine confidence scores vs actual jackpot results

AUDIT RESULTS SUMMARY:
- Cash4Life: 10.27% actual win rate
- Powerball: 1.39% actual win rate  
- MegaMillions: 0% actual win rate (no data)
- Overall: 5.86% actual win rate

ENHANCED SYSTEM CONFIDENCE RANGES:
- Cash4Life: 10-15% confidence range
- Powerball: 6-10% confidence range
- MegaMillions: 8-12% confidence range
"""

import pandas as pd
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Enhanced engine confidence analysis
try:
    from engines.rightside_v3_7.rightside_engine_v3_7_ENHANCED import EnhancedJackpotEngine
    ENHANCED_ENGINE_AVAILABLE = True
except ImportError:
    ENHANCED_ENGINE_AVAILABLE = False

def analyze_confidence_alignment():
    """Analyze confidence score alignment with actual jackpot results"""
    
    print("="*80)
    print("📊 CONFIDENCE SCORE ALIGNMENT ANALYSIS")
    print("="*80)
    print("🎯 Comparing Enhanced Right Engine predictions vs actual results")
    print()
    
    # Actual performance from audit
    actual_results = {
        'Cash4Life': {
            'predictions': 584,
            'wins': 60, 
            'win_rate': 10.27,
            'winnings': 199
        },
        'Powerball': {
            'predictions': 576,
            'wins': 8,
            'win_rate': 1.39,
            'winnings': 32
        },
        'MegaMillions': {
            'predictions': 0,  # No analyzed data
            'wins': 0,
            'win_rate': 0.0,
            'winnings': 0
        }
    }
    
    # Enhanced system confidence ranges
    enhanced_confidence_ranges = {
        'Cash4Life': {'min': 10.0, 'max': 15.0, 'target': 12.5},
        'Powerball': {'min': 6.0, 'max': 10.0, 'target': 8.0}, 
        'MegaMillions': {'min': 8.0, 'max': 12.0, 'target': 10.0}
    }
    
    print("🎰 CONFIDENCE ALIGNMENT ANALYSIS:")
    print("-" * 50)
    
    alignment_results = {}
    
    for game in ['Cash4Life', 'Powerball', 'MegaMillions']:
        actual = actual_results[game]
        enhanced = enhanced_confidence_ranges[game]
        
        actual_rate = actual['win_rate']
        confidence_min = enhanced['min']
        confidence_max = enhanced['max']
        confidence_target = enhanced['target']
        
        # Calculate alignment
        if confidence_min <= actual_rate <= confidence_max:
            alignment = "✅ EXCELLENT"
            alignment_score = 100
        elif actual_rate < confidence_min:
            if actual_rate == 0:
                alignment = "🔴 OVER-OPTIMISTIC"
                alignment_score = 0
            else:
                # Calculate how much we over-predicted
                over_prediction = confidence_min - actual_rate
                alignment_score = max(0, 100 - (over_prediction * 10))
                alignment = f"🟡 OVER-OPTIMISTIC ({over_prediction:.1f}% too high)"
        else:  # actual_rate > confidence_max
            # Under-predicted (rare but good problem to have)
            under_prediction = actual_rate - confidence_max
            alignment_score = min(100, 100 + (under_prediction * 5))
            alignment = f"🟢 CONSERVATIVE ({under_prediction:.1f}% under-predicted)"
        
        alignment_results[game] = {
            'actual_rate': actual_rate,
            'confidence_range': f"{confidence_min}-{confidence_max}%",
            'confidence_target': confidence_target,
            'alignment': alignment,
            'alignment_score': alignment_score,
            'predictions': actual['predictions'],
            'wins': actual['wins']
        }
        
        print(f"\n{game}:")
        print(f"  Predicted Confidence: {confidence_min}-{confidence_max}% (target: {confidence_target}%)")
        print(f"  Actual Win Rate: {actual_rate:.2f}%")
        print(f"  Alignment: {alignment}")
        print(f"  Predictions: {actual['predictions']:,}")
        print(f"  Wins: {actual['wins']:,}")
        print(f"  Winnings: ${actual['winnings']:,}")
    
    # Overall system confidence alignment
    total_predictions = sum(r['predictions'] for r in actual_results.values())
    total_wins = sum(r['wins'] for r in actual_results.values())
    overall_actual_rate = (total_wins / total_predictions * 100) if total_predictions > 0 else 0
    
    # Calculate weighted average confidence target
    weighted_confidence = 0
    total_weight = 0
    for game, result in actual_results.items():
        if result['predictions'] > 0:
            weight = result['predictions']
            confidence = enhanced_confidence_ranges[game]['target']
            weighted_confidence += confidence * weight
            total_weight += weight
    
    avg_confidence_target = weighted_confidence / total_weight if total_weight > 0 else 0
    
    print(f"\n🎯 OVERALL SYSTEM ALIGNMENT:")
    print(f"  Average Predicted Confidence: {avg_confidence_target:.1f}%")
    print(f"  Overall Actual Win Rate: {overall_actual_rate:.2f}%")
    
    if abs(avg_confidence_target - overall_actual_rate) <= 2.0:
        overall_alignment = "✅ EXCELLENT ALIGNMENT"
    elif avg_confidence_target > overall_actual_rate:
        diff = avg_confidence_target - overall_actual_rate
        overall_alignment = f"🟡 SLIGHTLY OVER-OPTIMISTIC ({diff:.1f}% too high)"
    else:
        diff = overall_actual_rate - avg_confidence_target
        overall_alignment = f"🟢 CONSERVATIVE ({diff:.1f}% under-predicted)"
    
    print(f"  Overall Alignment: {overall_alignment}")
    
    # Confidence calibration recommendations
    print(f"\n🔧 CALIBRATION RECOMMENDATIONS:")
    print("-" * 40)
    
    for game, result in alignment_results.items():
        if result['alignment_score'] < 80:  # Needs calibration
            actual = result['actual_rate']
            current_range = enhanced_confidence_ranges[game]
            
            if actual == 0:
                new_max = 3.0
                new_min = 1.0
                print(f"{game}: Reduce to {new_min}-{new_max}% (currently generating no wins)")
            else:
                # Calibrate to actual ± 2%
                new_min = max(1.0, actual - 2.0)
                new_max = actual + 2.0
                print(f"{game}: Recalibrate to {new_min:.1f}-{new_max:.1f}% (actual: {actual:.2f}%)")
        else:
            print(f"{game}: ✅ Confidence range well-calibrated")
    
    # Return results for potential system updates
    return {
        'alignment_results': alignment_results,
        'overall_actual_rate': overall_actual_rate,
        'overall_confidence_target': avg_confidence_target,
        'calibration_needed': any(r['alignment_score'] < 80 for r in alignment_results.values())
    }

def generate_calibrated_confidence_system():
    """Generate updated confidence system based on actual results"""
    
    print(f"\n🎯 GENERATING CALIBRATED CONFIDENCE SYSTEM:")
    print("=" * 50)
    
    # Calibrated ranges based on actual performance
    calibrated_ranges = {
        'Cash4Life': {
            'base_confidence': 0.10,   # 10% (matches 10.27% actual)
            'max_confidence': 0.13,    # 13% (slightly above actual)
            'description': 'Well-calibrated - actual 10.27%'
        },
        'Powerball': {
            'base_confidence': 0.02,   # 2% (above 1.39% actual but realistic)
            'max_confidence': 0.04,    # 4% (more realistic upper bound) 
            'description': 'Recalibrated down from 6-10% to 2-4%'
        },
        'MegaMillions': {
            'base_confidence': 0.02,   # 2% (conservative, no actual data)
            'max_confidence': 0.05,    # 5% (conservative upper bound)
            'description': 'Conservative - no actual data available'
        }
    }
    
    print("📊 NEW CALIBRATED CONFIDENCE RANGES:")
    for game, config in calibrated_ranges.items():
        base_pct = config['base_confidence'] * 100
        max_pct = config['max_confidence'] * 100
        print(f"  {game}: {base_pct:.1f}-{max_pct:.1f}% ({config['description']})")
    
    # Generate code snippet for implementation
    code_snippet = """
# Updated Enhanced Jackpot Engine Configuration
CALIBRATED_GAME_CONFIGS = {
    'CASH4LIFE': {
        'confidence_base': 0.10,     # Base 10% (matches actual 10.27%)
        'confidence_max': 0.13       # Max 13%
    },
    'POWERBALL': {
        'confidence_base': 0.02,     # Base 2% (down from 6%, actual 1.39%)
        'confidence_max': 0.04       # Max 4% (down from 10%)
    },
    'MEGA_MILLIONS': {
        'confidence_base': 0.02,     # Base 2% (conservative)
        'confidence_max': 0.05       # Max 5% (conservative)
    }
}
"""
    
    print(f"\n💻 IMPLEMENTATION CODE SNIPPET:")
    print(code_snippet)
    
    return calibrated_ranges

if __name__ == "__main__":
    # Run confidence alignment analysis
    alignment_data = analyze_confidence_alignment()
    
    print("\n" + "="*80)
    
    # Generate calibrated system
    calibrated_system = generate_calibrated_confidence_system()
    
    print("\n" + "="*80)
    print("📋 SUMMARY:")
    print("- Cash4Life confidence: ✅ EXCELLENT (predicted 10-15%, actual 10.27%)")  
    print("- Powerball confidence: 🟡 OVER-OPTIMISTIC (predicted 6-10%, actual 1.39%)")
    print("- MegaMillions confidence: ⚠️ NO DATA (predicted 8-12%, no results)")
    print("- Recommendation: Recalibrate Powerball and MegaMillions to 2-5% range")
    print("="*80)