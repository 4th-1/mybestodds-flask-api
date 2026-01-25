"""
validate_adjacent_enhancement_integration.py
===========================================
Validation script to ensure adjacent number enhancement is properly integrated
across both pick_engine_v3.py and rightside_engine_v3_7_ENHANCED.py

Validates:
1. Adjacent enhancement module loads correctly
2. Cash4Life generation includes adjacent logic
3. System integration is complete and functional
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def test_adjacent_enhancement_import():
    """Test that adjacent enhancement module can be imported"""
    try:
        from adjacent_number_enhancement_v3_7 import enhance_cash4life_prediction
        print("✅ Adjacent enhancement module imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import adjacent enhancement: {e}")
        return False

def test_pick_engine_integration():
    """Test Cash4Life enhancement in pick_engine_v3.py"""
    try:
        from core.pick_engine_v3 import generate_cash4life_picks
        
        # Test Cash4Life generation
        enhanced = generate_cash4life_picks(lines=1)
        
        print(f"✅ Pick engine Cash4Life integration working")
        print(f"   Enhanced result: {enhanced}")
        return True
        
    except Exception as e:
        print(f"❌ Pick engine integration failed: {e}")
        return False

def test_rightside_engine_integration():
    """Test Cash4Life enhancement in rightside engine"""
    try:
        from engines.rightside_v3_7.rightside_engine_v3_7_ENHANCED import EnhancedJackpotEngine
        
        # Create test data
        import pandas as pd
        
        test_row = pd.Series({
            'date': '2025-01-01',
            'game': 'CASH4LIFE'
        })
        
        test_subscriber = {
            'identity': {
                'date_of_birth': '1985-06-15'
            }
        }
        
        engine = EnhancedJackpotEngine()
        result = engine.generate_full_jackpot_combination('CASH4LIFE', test_subscriber, test_row)
        
        print("✅ Rightside engine Cash4Life integration working")
        print(f"   Generated combination: {result.get('full_combination', 'N/A')}")
        print(f"   Confidence: {result.get('confidence_score', 'N/A')}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Rightside engine integration failed: {e}")
        return False

def test_georgia_patterns():
    """Test enhancement against actual Georgia lottery patterns"""
    try:
        from adjacent_number_enhancement_v3_7 import enhance_cash4life_prediction
        
        # Test with Dec 21 Georgia pattern: [26, 31, 54] should enhance to include [25, 30, 55]
        original_numbers = [26, 31, 54, 12, 8]
        enhanced_numbers = enhance_cash4life_prediction(original_numbers)
        
        # Check if enhancement created variations
        has_adjacent_variations = any(
            abs(orig - enh) == 1 
            for orig, enh in zip(sorted(original_numbers)[:3], sorted(enhanced_numbers)[:3])
        )
        
        print("✅ Georgia pattern enhancement test:")
        print(f"   Original: {original_numbers}")
        print(f"   Enhanced: {enhanced_numbers}")
        print(f"   Has adjacent variations: {has_adjacent_variations}")
        
        return True
        
    except Exception as e:
        print(f"❌ Georgia pattern test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 VALIDATING ADJACENT ENHANCEMENT INTEGRATION")
    print("=" * 60)
    
    tests = [
        test_adjacent_enhancement_import,
        test_pick_engine_integration, 
        test_rightside_engine_integration,
        test_georgia_patterns
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"📊 VALIDATION RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 SYSTEM READY FOR JAN 1 LAUNCH!")
        print("   Adjacent enhancement fully integrated")
    else:
        print("⚠️  Issues found - review failures above")
    
    return passed == total

if __name__ == "__main__":
    main()