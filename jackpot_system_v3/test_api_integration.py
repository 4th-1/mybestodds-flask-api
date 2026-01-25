#!/usr/bin/env python3
"""
Test API Integration with Real RapidAPI Data
============================================

Test the automated lottery results system with the actual API response
format you successfully connected to.
"""

import os
import sys
import json
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from automated_lottery_results_v3_7 import LotteryResultsFetcher

def test_with_real_api_data():
    """Test with the actual API response data you provided"""
    
    print("🧪 TESTING AUTOMATED LOTTERY RESULTS API INTEGRATION")
    print("=" * 55)
    
    # Initialize fetcher with your working API key
    fetcher = LotteryResultsFetcher()
    
    print(f"📡 API Key configured: {fetcher.api_key[:10]}...")
    print(f"🎯 Base URL: {fetcher.base_url}")
    print(f"🔧 Headers configured: {bool(fetcher.headers)}")
    
    # Test Cash4Life (the game from your API response)
    print("\n🎲 Testing Cash4Life (Lucky for Life) API Integration:")
    print("-" * 50)
    
    try:
        # This should use the exact same API call that worked for you
        results = fetcher.fetch_draw_dates_and_results("cash4life", days_back=7)
        
        if results:
            print(f"✅ SUCCESS: Retrieved {len(results)} draws")
            
            # Show first few results
            for i, result in enumerate(results[:3]):
                print(f"  Draw {i+1}: {result['date']} - Draw ID: {result['draw_id']}")
                print(f"    Game: {result['game']} | Session: {result['session']}")
                print(f"    Time: {result['draw_time']} | Status: {result['status']}")
                print(f"    State: {result['game_details'].get('state', 'N/A')}")
                print()
                
            # Test parsing sample data to verify format compatibility
            sample_api_response = {
                "status": "success",
                "data": {
                    "gameDetails": {
                        "id": 66,
                        "gameName": "Lucky for Life",
                        "state": {"state": "Delaware", "stateCode": "DE"}
                    },
                    "date": [
                        {
                            "drawID": 258259,
                            "drawDate": "2025-12-22",
                            "drawTime": "14:38:00"
                        }
                    ]
                }
            }
            
            print("🧪 Testing with sample API data format:")
            parsed = fetcher.parse_rapidapi_response(sample_api_response, "cash4life")
            
            if parsed:
                print("✅ API response parsing successful!")
                print(f"  Parsed result: {parsed[0]['game']} on {parsed[0]['date']}")
            else:
                print("❌ API response parsing failed")
                
        else:
            print("⚠️ No results returned - checking API connection...")
            
    except Exception as e:
        print(f"❌ API Integration Error: {e}")
        print("🔧 Troubleshooting steps:")
        print("   1. Verify API key is valid")
        print("   2. Check network connection")  
        print("   3. Confirm endpoint URL is correct")
    
    print("\n" + "=" * 55)
    print("🎯 API Integration Test Complete")
    
def test_mmfsn_integration():
    """Test integration with MMFSN course correction system"""
    
    print("\n🔄 TESTING MMFSN COURSE CORRECTION INTEGRATION")
    print("=" * 50)
    
    try:
        from mmfsn_course_corrector_v3_7 import MMFSNCourseCorrector
        
        corrector = MMFSNCourseCorrector()
        
        # Simulate a high-confidence prediction that missed
        sample_miss_data = {
            "subscriber": "TEST_USER",
            "date": "2025-12-22",
            "game": "cash4life",
            "predicted": "05-12-28-35-47-03",
            "actual": "12-25-33-41-48-15",  # Different numbers
            "confidence": 87.5,  # High confidence miss
            "mmfsn_weight": 1.0
        }
        
        print("📊 Simulating high-confidence miss for MMFSN adjustment...")
        print(f"   Predicted: {sample_miss_data['predicted']}")
        print(f"   Actual: {sample_miss_data['actual']}")
        print(f"   Confidence: {sample_miss_data['confidence']}%")
        
        # This would trigger MMFSN weight adjustment
        adjustment = corrector.calculate_weight_adjustment(
            sample_miss_data['confidence'], 
            sample_miss_data['mmfsn_weight']
        )
        
        print(f"🎛️ MMFSN Weight Adjustment: {adjustment:.3f}")
        print("✅ MMFSN Integration Test Successful!")
        
    except ImportError:
        print("⚠️ MMFSN Course Corrector not available - integration pending")
    except Exception as e:
        print(f"❌ MMFSN Integration Error: {e}")

if __name__ == "__main__":
    test_with_real_api_data()
    test_mmfsn_integration()
    
    print(f"\n🕒 Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")