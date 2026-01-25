#!/usr/bin/env python3
"""
Test Fixed Winning Numbers Parsing
===================================

Test that the format_winning_number method works with the API response format
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

try:
    from automated_lottery_results_v3_7 import LotteryResultsFetcher
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_winning_numbers_parsing():
    """Test the winning numbers parsing with real Powerball data"""
    print("🎯 TESTING WINNING NUMBERS PARSING FIX")
    print("=" * 50)
    
    fetcher = LotteryResultsFetcher()
    
    # Test just one recent Powerball draw
    try:
        complete_data = fetcher.fetch_complete_lottery_data("powerball", days_back=7)
        
        if complete_data:
            success_count = sum(1 for r in complete_data if "formatted_winning_number" in r)
            print(f"🏆 RESULTS:")
            print(f"   📊 Total draws: {len(complete_data)}")
            print(f"   ✅ With winning numbers: {success_count}")
            print(f"   📈 Success rate: {success_count/len(complete_data)*100:.1f}%")
            
            # Show results
            for i, draw in enumerate(complete_data, 1):
                if "formatted_winning_number" in draw:
                    print(f"   [{i}] ✅ {draw['date']}: {draw['formatted_winning_number']} (${draw.get('jackpot', 'Unknown')})")
                else:
                    print(f"   [{i}] ⚠️ {draw['date']}: Numbers not available")
            
        else:
            print("❌ No data retrieved")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🧪 TESTING FIXED WINNING NUMBERS PARSING")
    print("=" * 60)
    
    test_winning_numbers_parsing()
    
    print("\n" + "=" * 60)
    print("🎯 If working:")
    print("   ✅ 100% API integration complete")
    print("   🚀 Ready for 2000 subscriber processing")
    print("   🎲 MMFSN course correction system fully automated")

if __name__ == "__main__":
    main()