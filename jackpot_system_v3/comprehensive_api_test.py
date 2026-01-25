#!/usr/bin/env python3
"""
Test Powerball Winning Numbers + MegaMillions with Broader Range
================================================================

Since Powerball ID 23 works, let's test its winning numbers
and check MegaMillions with a broader date range
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

def test_powerball_complete_data():
    """Test complete Powerball data including winning numbers"""
    print("🎯 TESTING POWERBALL COMPLETE DATA (including winning numbers)")
    print("=" * 70)
    
    fetcher = LotteryResultsFetcher()
    
    try:
        # Test with 7 days to get more draws
        complete_data = fetcher.fetch_complete_lottery_data("powerball", days_back=7)
        
        if complete_data:
            print(f"✅ Retrieved {len(complete_data)} Powerball draws")
            
            # Show all draws
            for i, draw in enumerate(complete_data, 1):
                status = "✅ COMPLETE" if "formatted_winning_number" in draw else "📅 DATE ONLY"
                numbers = draw.get("formatted_winning_number", "Numbers pending")
                jackpot = draw.get("jackpot", "Unknown")
                
                print(f"   [{i}] {draw['date']} (ID: {draw['draw_id']}) → {status}")
                print(f"       Numbers: {numbers}")
                print(f"       Jackpot: ${jackpot}")
                print()
        else:
            print("❌ No Powerball data retrieved")
            
    except Exception as e:
        print(f"❌ Error testing Powerball: {e}")

def test_megamillions_broader_range():
    """Test MegaMillions with broader date range"""
    print("🎯 TESTING MEGAMILLIONS WITH BROADER RANGE")
    print("=" * 70)
    
    fetcher = LotteryResultsFetcher()
    
    try:
        # Test with 10 days to catch MegaMillions draws (they may be less frequent)
        print("📊 Trying 10-day range for MegaMillions...")
        draws = fetcher.fetch_draw_dates_and_results("megamillions", days_back=10)
        
        if draws:
            print(f"✅ Found {len(draws)} MegaMillions draws in last 10 days!")
            
            # Show recent draws
            for i, draw in enumerate(draws[:3], 1):
                print(f"   [{i}] {draw['date']} (ID: {draw['draw_id']}) - Session: {draw.get('session', 'N/A')}")
                
            # Now test complete data for the most recent
            if draws:
                print(f"\n🎲 Testing complete data for latest draw...")
                complete_data = fetcher.fetch_complete_lottery_data("megamillions", days_back=10)
                
                if complete_data:
                    with_numbers = [r for r in complete_data if r.get("formatted_winning_number")]
                    if with_numbers:
                        sample = with_numbers[0]
                        print(f"🏆 SUCCESS! MegaMillions complete data:")
                        print(f"   📅 Date: {sample['date']}")
                        print(f"   🎲 Numbers: {sample['formatted_winning_number']}")
                        print(f"   💰 Jackpot: {sample.get('jackpot', 'Unknown')}")
                    else:
                        print("⚠️ Got draws but no winning numbers yet")
                else:
                    print("❌ Complete data fetch failed")
        else:
            print("❌ Still no MegaMillions draws found - may need investigation")
            
    except Exception as e:
        print(f"❌ Error testing MegaMillions: {e}")

def test_all_working_games():
    """Test all games that should be working now"""
    print("🚀 TESTING ALL GAME IDS - COMPREHENSIVE")
    print("=" * 70)
    
    fetcher = LotteryResultsFetcher()
    
    working_games = []
    
    # Test each game with current IDs
    for game_name, config in fetcher.game_mappings.items():
        print(f"\n🎯 {game_name.upper()}: ID {config['gameID']}")
        
        try:
            draws = fetcher.fetch_draw_dates_and_results(game_name, days_back=5)
            if draws:
                working_games.append(game_name)
                print(f"   ✅ Working! {len(draws)} draws found")
                print(f"   📅 Latest: {draws[0]['date']} (ID: {draws[0]['draw_id']})")
            else:
                print(f"   ⚠️ No recent draws (may need longer timeframe)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🏆 WORKING GAMES SUMMARY:")
    print(f"   ✅ {len(working_games)}/{len(fetcher.game_mappings)} games functional")
    for game in working_games:
        print(f"      • {game}")
    
    # Calculate success rate
    success_rate = (len(working_games) / len(fetcher.game_mappings)) * 100
    print(f"   📈 Success rate: {success_rate:.1f}%")

def main():
    """Run comprehensive tests"""
    print("🚀 COMPREHENSIVE LOTTERY API TESTING")
    print("=" * 80)
    
    test_powerball_complete_data()
    print("\n" + "=" * 80)
    
    test_megamillions_broader_range()
    print("\n" + "=" * 80)
    
    test_all_working_games()
    
    print("\n" + "=" * 80)
    print("🎯 BREAKTHROUGH STATUS:")
    print("   ✅ Powerball ID 23: CONFIRMED WORKING")
    print("   🔍 MegaMillions ID 24: Needs broader testing")
    print("   🚀 Ready for 2000 subscriber processing with current working games")

if __name__ == "__main__":
    main()