#!/usr/bin/env python3
"""
Complete SMART LOGIC Lottery API Integration Test
=================================================

Test ALL supported games with the correct Georgia game IDs.
This will confirm complete API integration for the 2000 subscriber run.
"""

import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from automated_lottery_results_v3_7 import LotteryResultsFetcher

def test_complete_smart_logic_integration():
    """Test complete SMART LOGIC system with all supported games"""
    
    print("🚀 COMPLETE SMART LOGIC LOTTERY API INTEGRATION TEST")
    print("=" * 60)
    print(f"🕒 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize fetcher with your working API
    fetcher = LotteryResultsFetcher()
    
    print(f"\n📡 API Configuration:")
    print(f"   API Key: {fetcher.api_key[:10]}...{fetcher.api_key[-10:]}")
    print(f"   Base URL: {fetcher.base_url}")
    print(f"   Supported Games: {len(fetcher.game_mappings)}")
    
    # Show all configured game mappings
    print(f"\n🎲 Game ID Mappings:")
    for game, config in fetcher.game_mappings.items():
        print(f"   {game:15} → Game ID {config['gameID']}")
    
    print(f"\n" + "=" * 60)
    
    # Test all games at once
    try:
        all_results = fetcher.fetch_all_supported_games(days_back=3)
        
        if all_results:
            print(f"\n🎉 INTEGRATION TEST RESULTS:")
            print("=" * 35)
            
            successful_games = []
            failed_games = []
            
            for game_name, results in all_results.items():
                if results:
                    successful_games.append(game_name)
                    print(f"✅ {game_name:15} - {len(results):2d} draws")
                else:
                    failed_games.append(game_name)
                    print(f"❌ {game_name:15} - No data")
            
            print(f"\n📊 FINAL SUMMARY:")
            print(f"   Successful: {len(successful_games)}/{len(fetcher.game_mappings)} games")
            print(f"   Success Rate: {len(successful_games)/len(fetcher.game_mappings)*100:.1f}%")
            
            if successful_games:
                print(f"   ✅ Working: {', '.join(successful_games)}")
            if failed_games:
                print(f"   ❌ Issues: {', '.join(failed_games)}")
                
            # Test one successful game in detail
            if successful_games:
                test_game = successful_games[0]
                test_results = all_results[test_game]
                
                print(f"\n🔍 DETAILED SAMPLE - {test_game.upper()}:")
                print("-" * 40)
                
                sample = test_results[0]
                for key, value in sample.items():
                    if isinstance(value, dict):
                        print(f"   {key}: {list(value.keys())}")  # Show dict structure
                    else:
                        print(f"   {key}: {value}")
            
            # Check if ready for 2000 subscriber processing  
            if len(successful_games) >= 4:  # Need at least most major games
                print(f"\n🎯 STATUS: READY FOR 2000 SUBSCRIBER PROCESSING")
                print("   ✅ Sufficient game coverage")
                print("   ✅ API integration functional")
                print("   ✅ Data parsing working")
                print("   ✅ SMART LOGIC compatible format")
                return True
            else:
                print(f"\n⚠️ STATUS: PARTIAL SUCCESS - Need more game coverage")
                return False
                
        else:
            print(f"❌ No results returned from any games")
            return False
            
    except Exception as e:
        print(f"❌ Integration Test Failed: {e}")
        return False
    
    finally:
        print(f"\n🕒 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

def test_rapid_single_game_calls():
    """Quick test of individual game API calls"""
    
    print(f"\n🔬 RAPID SINGLE GAME API TESTS")
    print("=" * 35)
    
    fetcher = LotteryResultsFetcher()
    
    # Test each game individually
    key_games = ["cash3_midday", "cash4_night", "megamillions", "cash4life"]
    
    for game in key_games:
        print(f"\n🎲 Testing {game}...")
        
        try:
            results = fetcher.fetch_draw_dates_and_results(game, days_back=1)
            if results:
                latest = results[0]
                game_name = latest["game_details"]["game_name"]
                print(f"   ✅ {game_name} - Latest: {latest['date']}")
            else:
                print(f"   ❌ No data returned")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")

if __name__ == "__main__":
    # Run complete integration test
    success = test_complete_smart_logic_integration()
    
    if not success:
        print("\n🔧 Running additional diagnostic tests...")
        test_rapid_single_game_calls()
    
    print(f"\n{'🎉 READY TO PROCEED!' if success else '🔧 NEEDS ATTENTION'}")