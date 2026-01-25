#!/usr/bin/env python3
"""
Test Updated National Game IDs
==============================

Tests the corrected national game IDs (Powerball 23, MegaMillions 24)
and the winning numbers integration from lottery-results/game-result
"""

import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

try:
    from automated_lottery_results_v3_7 import LotteryResultsFetcher
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_national_games_correction():
    """Test the corrected national game IDs"""
    print("🧪 TESTING CORRECTED NATIONAL GAME IDs")
    print("=" * 50)
    
    fetcher = LotteryResultsFetcher()
    
    # Test games with updated IDs
    test_games = ["powerball", "megamillions"]
    
    for game in test_games:
        print(f"\n🎯 Testing {game.upper()}")
        print(f"   Game ID: {fetcher.game_mappings[game]['gameID']}")
        
        try:
            # Test draw dates fetching
            draws = fetcher.fetch_draw_dates_and_results(game, days_back=3)
            
            if draws:
                print(f"   ✅ Successfully fetched {len(draws)} draws")
                print(f"   📅 Latest draw: {draws[0]['date']} (ID: {draws[0]['draw_id']})")
            else:
                print(f"   ⚠️ No draws found (may need different gameID)")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_winning_numbers_endpoint():
    """Test the winning numbers endpoint using MegaMillions"""
    print("\n🎲 TESTING WINNING NUMBERS ENDPOINT")
    print("=" * 50)
    
    fetcher = LotteryResultsFetcher()
    
    # Test with MegaMillions (most reliable for national games)
    game = "megamillions"
    
    print(f"🎯 Testing complete data fetch for {game.upper()}")
    
    try:
        complete_data = fetcher.fetch_complete_lottery_data(game, days_back=3)
        
        if complete_data:
            # Find a result with winning numbers
            with_numbers = [r for r in complete_data if r.get("formatted_winning_number")]
            
            if with_numbers:
                sample = with_numbers[0]
                print(f"\n🏆 SUCCESS! Got complete data:")
                print(f"   📅 Date: {sample['date']}")
                print(f"   🎲 Winning numbers: {sample['formatted_winning_number']}")
                print(f"   💰 Jackpot: {sample.get('jackpot', 'Unknown')}")
                print(f"   👥 Total winners: {sample.get('total_winners', 'Unknown')}")
                print(f"   🎯 MMFSN ready: {sample.get('mmfsn_ready', False)}")
            else:
                print("⚠️ No winning numbers retrieved - all draws may be future dates")
        else:
            print("❌ No data retrieved")
            
    except Exception as e:
        print(f"❌ Error testing complete data: {e}")

def main():
    """Run all tests"""
    print("🚀 TESTING UPDATED LOTTERY API INTEGRATION")
    print("=" * 60)
    
    test_national_games_correction()
    test_winning_numbers_endpoint()
    
    print("\n" + "=" * 60)
    print("✅ Testing complete!")
    print("\n🎯 Next steps:")
    print("   1. If tests pass → Run full 2000 subscriber processing")
    print("   2. If MegaMillions/Powerball work → 100% game coverage achieved")
    print("   3. Complete MMFSN course correction automation ready")

if __name__ == "__main__":
    main()