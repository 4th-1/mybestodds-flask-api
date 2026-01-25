#!/usr/bin/env python3
"""
MegaMillions Opportunity Scanner
================================
Checks multiple test subscribers for strong MegaMillions opportunities tonight
"""

import json
from pathlib import Path

def check_megamillions_opportunities():
    """Check existing test subscriber outputs for MegaMillions opportunities."""
    
    print("🎯 SCANNING FOR STRONG MEGAMILLIONS OPPORTUNITIES")
    print("=" * 55)
    
    outputs_dir = Path("outputs")
    opportunities = []
    
    # Check all existing test outputs
    for output_dir in outputs_dir.iterdir():
        if output_dir.is_dir() and "BOOK3_TEST" in output_dir.name:
            
            # Extract subscriber ID
            subscriber_id = "UNKNOWN"
            if "TEST" in output_dir.name:
                parts = output_dir.name.split("_")
                for part in parts:
                    if part.startswith("TEST"):
                        subscriber_id = part
                        break
            
            # Check today's predictions
            today_file = output_dir / "2025-12-23.json"
            
            if today_file.exists():
                try:
                    with open(today_file, 'r') as f:
                        data = json.load(f)
                    
                    overall_score = data.get("score", 0)
                    
                    if "picks" in data and "MegaMillions" in data["picks"]:
                        mm_picks = data["picks"]["MegaMillions"]["lane_system"]
                        
                        opportunities.append({
                            "subscriber_id": subscriber_id,
                            "confidence": overall_score,
                            "predictions": mm_picks,
                            "score_components": data.get("score_components", {}),
                            "astro_score": data.get("score_components", {}).get("astro", 0),
                            "mmfsn_score": data.get("score_components", {}).get("mmfsn", 0)
                        })
                        
                except Exception as e:
                    print(f"   ❌ Error reading {subscriber_id}: {e}")
                    continue
    
    # Sort by confidence score
    opportunities.sort(key=lambda x: x["confidence"], reverse=True)
    
    print(f"📊 Found {len(opportunities)} MegaMillions opportunities")
    print("\n🎯 TOP MEGAMILLIONS OPPORTUNITIES (sorted by confidence):")
    print("-" * 55)
    
    strong_opportunities = []
    moderate_opportunities = []
    
    for i, opp in enumerate(opportunities, 1):
        confidence = opp["confidence"]
        
        if confidence >= 75.0:
            strong_opportunities.append(opp)
            strength = "🔥 STRONG"
        elif confidence >= 60.0:
            moderate_opportunities.append(opp)
            strength = "⚡ MODERATE"
        else:
            strength = "📊 WEAK"
        
        print(f"{i:2}. {opp['subscriber_id']} - {strength}")
        print(f"    Confidence: {confidence:.1f}/100")
        print(f"    Predictions: {opp['predictions']}")
        print(f"    Astro: {opp['astro_score']:.1f} | MMFSN: {opp['mmfsn_score']:.1f}")
        print()
    
    # Summary
    print("=" * 55)
    print("🏆 TONIGHT'S MEGAMILLIONS SUMMARY:")
    print(f"   🔥 Strong opportunities (75-100%): {len(strong_opportunities)}")
    print(f"   ⚡ Moderate opportunities (60-75%): {len(moderate_opportunities)}")
    print(f"   📊 Total analyzed: {len(opportunities)}")
    
    if strong_opportunities:
        print(f"\n✨ BEST OPPORTUNITY:")
        best = strong_opportunities[0]
        print(f"   Subscriber: {best['subscriber_id']}")
        print(f"   Confidence: {best['confidence']:.1f}%")
        print(f"   Top pick: {best['predictions'][0]}")
    else:
        print(f"\n⚠️  NO STRONG OPPORTUNITIES (75-100%) detected for tonight's MegaMillions")
        
        if moderate_opportunities:
            best_moderate = moderate_opportunities[0]
            print(f"   Best moderate option: {best_moderate['subscriber_id']} ({best_moderate['confidence']:.1f}%)")
            print(f"   Pick: {best_moderate['predictions'][0]}")
        else:
            print(f"   All opportunities are below 60% confidence threshold")
    
    return strong_opportunities, moderate_opportunities

if __name__ == "__main__":
    strong, moderate = check_megamillions_opportunities()