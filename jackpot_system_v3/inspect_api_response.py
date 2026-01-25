#!/usr/bin/env python3
"""
Inspect Actual API Response
===========================

Let's see exactly what the API is returning.
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

def inspect_api_response():
    """Let's see exactly what we're getting back"""
    
    print("🔍 INSPECTING ACTUAL API RESPONSE")
    print("=" * 35)
    
    url = f"{base_url}/lottery-results/past-draws-dates"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📋 Top-level keys: {list(data.keys())}")
            
            # Show the actual structure
            print(f"\n📊 Full Response Structure:")
            print(json.dumps(data, indent=2)[:1500] + "..." if len(json.dumps(data, indent=2)) > 1500 else json.dumps(data, indent=2))
            
            # Check if this matches your format
            if "data" in data:
                print(f"\n🔍 Data section keys: {list(data['data'].keys())}")
                
                if "date" in data["data"]:
                    dates = data["data"]["date"]
                    print(f"📅 Found {len(dates)} date entries")
                    if dates:
                        print(f"   First entry: {dates[0]}")
                        print("   ✅ This matches your format!")
                        return True
            
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = inspect_api_response()
    
    if success:
        print("\n✅ API Response Format Confirmed!")
    else:
        print("\n❌ API Response Format Differs")