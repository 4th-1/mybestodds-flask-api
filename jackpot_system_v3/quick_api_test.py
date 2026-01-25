#!/usr/bin/env python3
import requests

headers = {
    'X-RapidAPI-Key': 'a0a23c4713msh72afb05b0e7b414p18e883jsn6452579f960a',
    'X-RapidAPI-Host': 'usa-lottery-result-all-state-api.p.rapidapi.com'
}

response = requests.get(
    'https://usa-lottery-result-all-state-api.p.rapidapi.com/lottery-results/past-draws-dates',
    headers=headers,
    params={'gameID': '66'}  # Note: gameID uppercase!
)

print(f"Status: {response.status_code}")
data = response.json()

if 'data' in data and 'gameDetails' in data['data']:
    game_name = data['data']['gameDetails']['gameName']
    dates = data['data']['date']
    print(f"✅ SUCCESS: {game_name}")
    print(f"📊 Found {len(dates)} draws")
    print(f"📅 Latest: {dates[0]['drawDate']}")
else:
    print(f"❌ Error: {data.get('message', 'Unknown error')}")