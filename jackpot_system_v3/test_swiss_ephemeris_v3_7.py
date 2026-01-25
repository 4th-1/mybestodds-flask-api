#!/usr/bin/env python3
"""
Swiss Ephemeris Integration Test for My Best Odds v3.7
======================================================

Test script to validate the Swiss Ephemeris integration is working properly.
"""

import sys
import os

# Add the project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime
import json

def test_swiss_ephemeris_integration():
    """Test all aspects of the Swiss Ephemeris integration."""
    print("🌌 TESTING SWISS EPHEMERIS INTEGRATION v3.7")
    print("=" * 60)
    
    try:
        from core.swiss_ephemeris_v3_7 import (
            validate_ephemeris_integration,
            get_astronomical_context,
            get_moon_phase,
            get_planetary_positions
        )
        
        # Test 1: Validation check
        print("\n📋 VALIDATION CHECK:")
        validation = validate_ephemeris_integration()
        print(json.dumps(validation, indent=2))
        
        # Test 2: Astronomical context for today
        print(f"\n🌟 ASTRONOMICAL CONTEXT FOR TODAY ({datetime.now().strftime('%Y-%m-%d')}):")
        today_context = get_astronomical_context("2025-12-21", "MIDDAY")
        print(json.dumps(today_context, indent=2, default=str))
        
        # Test 3: Moon phase calculation
        print(f"\n🌙 CURRENT MOON PHASE:")
        moon_data = get_moon_phase(datetime.now())
        print(json.dumps(moon_data, indent=2))
        
        # Test 4: Planetary positions
        print(f"\n🪐 CURRENT PLANETARY POSITIONS:")
        planetary_pos = get_planetary_positions(datetime.now())
        for planet, data in planetary_pos.items():
            print(f"  {planet:12} - {data['sign']:12} {data['degree']:6.2f}° (Long: {data['longitude']:6.2f}°)")
        
        # Test 5: Different dates and times
        print(f"\n📅 ASTRONOMICAL DATA FOR DIFFERENT SESSIONS:")
        test_cases = [
            ("2025-12-21", "MIDDAY"),
            ("2025-12-21", "EVENING"),
            ("2025-12-25", "MIDDAY"),  # Christmas
            ("2026-01-01", "EVENING"), # New Year
        ]
        
        for date_str, session in test_cases:
            context = get_astronomical_context(date_str, session)
            print(f"  {date_str} {session:7} - Moon: {context.get('moon_phase'):15} | "
                  f"Planet Hour: {context.get('planetary_hour'):7} | "
                  f"Source: {context.get('calculation_source')}")
        
        print("\n✅ SWISS EPHEMERIS INTEGRATION TEST COMPLETE!")
        return True
        
    except Exception as e:
        print(f"❌ SWISS EPHEMERIS INTEGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_before_after():
    """Compare the old fake calculations vs new Swiss Ephemeris calculations."""
    print("\n" + "=" * 60)
    print("🔄 BEFORE vs AFTER COMPARISON")
    print("=" * 60)
    
    # Sample data that would have been fake before
    fake_data = {
        "moon_phase": "FULL",  # Always fake "FULL"
        "planetary_hour": "MIDDAY",  # Just copied from session
        "day_of_week": "SAT",
        "calculation_source": "Fake_Placeholder"
    }
    
    try:
        from core.swiss_ephemeris_v3_7 import get_astronomical_context
        
        # Real Swiss Ephemeris data for same conditions
        real_data = get_astronomical_context("2025-12-21", "MIDDAY")
        
        print("\n📊 DATA COMPARISON:")
        print(f"{'Field':<20} {'BEFORE (Fake)':<20} {'AFTER (Real)':<20}")
        print("-" * 60)
        print(f"{'Moon Phase':<20} {fake_data['moon_phase']:<20} {real_data.get('moon_phase', 'N/A'):<20}")
        print(f"{'Planetary Hour':<20} {fake_data['planetary_hour']:<20} {real_data.get('planetary_hour', 'N/A'):<20}")
        print(f"{'Day of Week':<20} {fake_data['day_of_week']:<20} {real_data.get('day_of_week', 'N/A'):<20}")
        print(f"{'Calculation Source':<20} {fake_data['calculation_source']:<20} {real_data.get('calculation_source', 'N/A'):<20}")
        
        # Show additional real data that wasn't available before
        print(f"\n🆕 NEW ASTRONOMICAL DATA AVAILABLE:")
        new_fields = ['sun_sign', 'moon_sign', 'north_node_sign', 'moon_illumination']
        for field in new_fields:
            if field in real_data:
                print(f"  {field:<20}: {real_data[field]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        return False


if __name__ == "__main__":
    success = test_swiss_ephemeris_integration()
    if success:
        compare_before_after()
    
    print(f"\n{'🎉 SUCCESS! Swiss Ephemeris integration is working!' if success else '💥 FAILED! Check errors above.'}")