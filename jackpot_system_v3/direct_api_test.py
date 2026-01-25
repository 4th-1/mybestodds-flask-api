#!/usr/bin/env python3
"""
Direct API Test - Using Your Exact Success Format
=================================================

Test the exact API call that worked for you to get the format right.
"""

import requests
import json

# Your working API credentials
api_key = "a0a23c4713msh72afb05b0e7b414p18e883jsn6452579f960a"
base_url = "https://usa-lottery-result-all-state-api.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": "usa-lottery-result-all-state-api.p.rapidapi.com"
}

def test_direct_api_call():
    """Make the exact API call that generated your successful response"""
    
    print("🔬 DIRECT API TEST - Replicating Your Success")
    print("=" * 45)
    
    # Try the endpoint that worked for you
    endpoint = "lottery-results/past-draws-dates"
    url = f"{base_url}/{endpoint}"
    
    print(f"📡 Testing URL: {url}")
    
    # Try different parameter combinations
    test_params = [
        {},  # No params (what you might have used)
        {"gameId": "66"},  # Lucky for Life ID from your response
        {"game": "lucky-for-life"},
        {"game": "cash4life"}
    ]
    
    for i, params in enumerate(test_params, 1):
        print(f"\n🧪 Test #{i} - Params: {params or 'None'}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if it matches your successful format
                if "data" in data and "date" in data.get("data", {}):
                    draws = data["data"]["date"]
                    game_name = data["data"].get("gameDetails", {}).get("gameName", "Unknown")
                    
                    print(f"   ✅ SUCCESS: {game_name}")
                    print(f"   📊 Found {len(draws)} draws")
                    print(f"   📅 Date range: {draws[-1]['drawDate']} to {draws[0]['drawDate']}")
                    
                    # Save successful response for analysis
                    with open("successful_api_response.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"   💾 Response saved to successful_api_response.json")
                    
                    return True
                else:
                    print(f"   ⚠️ Different format: {list(data.keys())}")
            else:
                print(f"   ❌ Failed: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False

def test_other_endpoints():
    """Test other potential endpoints"""
    
    print(f"\n🔍 TESTING OTHER POTENTIAL ENDPOINTS")
    print("=" * 40)
    
    other_endpoints = [
        "lottery-results",
        "games",
        "draw-dates",
        "results/cash4life",
        "results/lucky-for-life"
    ]
    
    for endpoint in other_endpoints:
        print(f"\n📡 Testing: {base_url}/{endpoint}")
        
        try:
            response = requests.get(f"{base_url}/{endpoint}", headers=headers, timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    keys = list(data.keys())[:3]  # First 3 keys
                    print(f"   📋 Keys: {keys}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")

if __name__ == "__main__":
    success = test_direct_api_call()
    
    if not success:
        print("\n🚫 No exact match found - trying other endpoints...")
        test_other_endpoints()
        
    print("\n" + "=" * 45)
    print("🎯 Direct API Test Complete")