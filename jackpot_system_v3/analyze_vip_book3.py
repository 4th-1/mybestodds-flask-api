#!/usr/bin/env python3
"""
BOOK3 VIP Subscribers Analysis - December 23, 2025
==================================================
Analyzes JDS, AJS, and YRS predictions for tonight's games, especially MegaMillions
"""

import json
from pathlib import Path

def analyze_vip_subscribers():
    """Analyze the three VIP BOOK3 subscribers for tonight's predictions."""
    
    print("🎯 VIP BOOK3 SUBSCRIBERS - DECEMBER 23, 2025 ANALYSIS")
    print("=" * 65)
    
    outputs_dir = Path("outputs")
    
    # Map subscriber codes to full names and directories
    subscribers = {
        "JDS": {
            "name": "Joseph David Smith", 
            "dir": "BOOK3_JDS_BOOK3_2025-12-22_to_2025-12-31"
        },
        "AJS": {
            "name": "Adonna Janay Smith", 
            "dir": "BOOK3_AJS_2025-12-22_to_2025-12-31"
        },
        "YRS": {
            "name": "Yolanda Renee Smith", 
            "dir": "BOOK3_YRS_BOOK3_2025-12-22_to_2025-12-31"
        }
    }
    
    all_predictions = {}
    megamillions_summary = []
    
    for code, info in subscribers.items():
        subscriber_dir = outputs_dir / info["dir"]
        today_file = subscriber_dir / "2025-12-23.json"
        
        print(f"\n🎲 {code} - {info['name'].upper()}")
        print("-" * 45)
        
        if today_file.exists():
            try:
                with open(today_file, 'r') as f:
                    data = json.load(f)
                
                # Store predictions
                all_predictions[code] = data
                
                overall_score = data.get("score", 0)
                score_components = data.get("score_components", {})
                
                print(f"📊 Overall Confidence: {overall_score:.1f}/100")
                print(f"📈 Score Breakdown:")
                print(f"   • Astro: {score_components.get('astro', 0):.1f}")
                print(f"   • MMFSN: {score_components.get('mmfsn', 0):.1f}")
                print(f"   • Stats: {score_components.get('stats', 0):.1f}")
                print(f"   • Numerology: {score_components.get('numerology', 0):.1f}")
                print(f"   • Planetary Hours: {score_components.get('planetary_hours', 0):.1f}")
                
                print(f"\n🎯 TONIGHT'S PREDICTIONS:")
                
                if "picks" in data:
                    # MegaMillions focus
                    if "MegaMillions" in data["picks"]:
                        mm_picks = data["picks"]["MegaMillions"]["lane_system"]
                        print(f"   🔥 MegaMillions: {mm_picks}")
                        
                        megamillions_summary.append({
                            "subscriber": code,
                            "name": info["name"],
                            "confidence": overall_score,
                            "predictions": mm_picks,
                            "astro": score_components.get('astro', 0),
                            "mmfsn": score_components.get('mmfsn', 0)
                        })
                    
                    # Other games
                    if "Cash3" in data["picks"]:
                        cash3_picks = data["picks"]["Cash3"]["lane_system"]
                        print(f"   💰 Cash3: {cash3_picks}")
                    
                    if "Cash4" in data["picks"]:
                        cash4_picks = data["picks"]["Cash4"]["lane_system"]
                        print(f"   💵 Cash4: {cash4_picks}")
                    
                    if "Cash4Life" in data["picks"]:
                        c4l_picks = data["picks"]["Cash4Life"]["lane_system"]
                        print(f"   🌟 Cash4Life: {c4l_picks}")
                    
                    if "Powerball" in data["picks"]:
                        pb_picks = data["picks"]["Powerball"]["lane_system"]
                        print(f"   ⚡ Powerball: {pb_picks}")
                
            except Exception as e:
                print(f"❌ Error reading {code} predictions: {e}")
        else:
            print(f"⚠️ No predictions file found for today")
    
    # MegaMillions focus analysis
    print(f"\n{'='*65}")
    print("🔥 MEGAMILLIONS JACKPOT FOCUS ANALYSIS")
    print(f"{'='*65}")
    
    if megamillions_summary:
        # Sort by confidence
        megamillions_summary.sort(key=lambda x: x["confidence"], reverse=True)
        
        print(f"🏆 RANKED BY CONFIDENCE:")
        for i, mm in enumerate(megamillions_summary, 1):
            confidence = mm["confidence"]
            
            if confidence >= 75.0:
                strength = "🔥 STRONG"
            elif confidence >= 60.0:
                strength = "⚡ MODERATE"  
            else:
                strength = "📊 WEAK"
                
            print(f"\n{i}. {mm['subscriber']} - {mm['name']} - {strength}")
            print(f"   Confidence: {confidence:.1f}%")
            print(f"   🎲 Pick 1: {mm['predictions'][0]}")
            if len(mm['predictions']) > 1:
                print(f"   🎲 Pick 2: {mm['predictions'][1]}")
            print(f"   📊 Astro: {mm['astro']:.1f} | MMFSN: {mm['mmfsn']:.1f}")
        
        # Find best opportunity
        best = megamillions_summary[0]
        print(f"\n🎯 TONIGHT'S BEST MEGAMILLIONS OPPORTUNITY:")
        print(f"   👤 Subscriber: {best['name']} ({best['subscriber']})")
        print(f"   🎲 Top Pick: {best['predictions'][0]}")
        print(f"   📈 Confidence: {best['confidence']:.1f}%")
        
        if best['confidence'] >= 75.0:
            print(f"   ✅ RECOMMENDATION: STRONG PLAY")
        elif best['confidence'] >= 60.0:
            print(f"   ⚡ RECOMMENDATION: MODERATE PLAY")
        else:
            print(f"   ⚠️  RECOMMENDATION: WEAK OPPORTUNITY - CONSIDER WAITING")
            
    else:
        print("❌ No MegaMillions predictions available")
    
    # Consensus analysis
    if len(megamillions_summary) >= 2:
        print(f"\n📊 CONSENSUS ANALYSIS:")
        
        # Check for number overlaps
        all_numbers = []
        for mm in megamillions_summary:
            for pick in mm['predictions']:
                # Extract main numbers (before the +)
                if '+' in pick:
                    main_part = pick.split('+')[0].strip()
                    numbers = [int(n) for n in main_part.split()]
                    all_numbers.extend(numbers)
        
        # Find most common numbers
        from collections import Counter
        common_numbers = Counter(all_numbers).most_common(5)
        
        if common_numbers:
            print(f"   🔥 Most Popular Numbers:")
            for num, count in common_numbers:
                print(f"      {num}: appears {count} times")
    
    return all_predictions, megamillions_summary

if __name__ == "__main__":
    predictions, mm_summary = analyze_vip_subscribers()