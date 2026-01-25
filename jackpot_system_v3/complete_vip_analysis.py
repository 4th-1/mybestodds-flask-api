#!/usr/bin/env python3
"""
COMPLETE VIP BOOK3 ANALYSIS - December 23, 2025
=============================================
Analyzing ALL VIP BOOK3 subscribers and ranking them by confidence and game opportunities
"""

import json
from pathlib import Path

def analyze_all_vip_subscribers():
    """Analyze all VIP BOOK3 subscribers for tonight's predictions."""
    
    print("🎯 COMPLETE VIP BOOK3 ANALYSIS - DECEMBER 23, 2025")
    print("=" * 60)
    
    outputs_dir = Path("outputs")
    
    # All subscribers with their directories
    subscribers = {
        "JDS": {"name": "Joseph David Smith", "dir": "BOOK3_JDS_BOOK3_2025-12-22_to_2025-12-31"},
        "AJS": {"name": "Adonna Janay Smith", "dir": "BOOK3_AJS_2025-12-22_to_2025-12-31"},
        "YRS": {"name": "Yolanda Renee Smith", "dir": "BOOK3_YRS_BOOK3_2025-12-22_to_2025-12-31"},
        "BO": {"name": "Bakiea Owens", "dir": "BOOK3_BO_2025-12-22_to_2025-12-31"},
        "CP": {"name": "Corey Patterson", "dir": "BOOK3_CP_2025-12-22_to_2025-12-31"},
        "CW": {"name": "Consuela Ward", "dir": "BOOK3_CW_2025-12-22_to_2025-12-31"},
        "JDR": {"name": "Jimmy Deshawn Roberts", "dir": "BOOK3_JDR_2025-12-22_to_2025-12-31"},
        "JHD": {"name": "John HF Douglas", "dir": "BOOK3_JHD_2025-12-22_to_2025-12-31"},
        "MT": {"name": "Martin Taylor", "dir": "BOOK3_MT_2025-12-22_to_2025-12-31"},
        "TN": {"name": "Tad Newton", "dir": "BOOK3_TN_2025-12-22_to_2025-12-31"},
        "VAL": {"name": "Valencia Allen-Love", "dir": "BOOK3_VAL_2025-12-22_to_2025-12-31"},
        "YT": {"name": "Yadonnis Tucker Lee", "dir": "BOOK3_YT_2025-12-22_to_2025-12-31"}
    }
    
    all_predictions = {}
    rankings = []
    
    print(f"\n📊 INDIVIDUAL SUBSCRIBER ANALYSIS:")
    print("-" * 60)
    
    for code, info in subscribers.items():
        subscriber_dir = outputs_dir / info["dir"]
        today_file = subscriber_dir / "2025-12-23.json"
        
        print(f"\n👤 {code} - {info['name'].upper()}")
        print("-" * 45)
        
        if today_file.exists():
            try:
                with open(today_file, 'r') as f:
                    data = json.load(f)
                
                overall_score = data.get("score", 0)
                score_components = data.get("score_components", {})
                
                # Store for ranking
                subscriber_data = {
                    "code": code,
                    "name": info["name"],
                    "confidence": overall_score,
                    "components": score_components,
                    "predictions": data.get("picks", {})
                }
                
                # Calculate adjusted game strengths
                cash3_strength = overall_score * 1.2 if "Cash3" in data.get("picks", {}) else 0
                cash4_strength = overall_score * 1.1 if "Cash4" in data.get("picks", {}) else 0
                mm_strength = overall_score if "MegaMillions" in data.get("picks", {}) else 0
                
                subscriber_data.update({
                    "cash3_adj": cash3_strength,
                    "cash4_adj": cash4_strength, 
                    "mm_strength": mm_strength
                })
                
                rankings.append(subscriber_data)
                
                print(f"📊 Overall Confidence: {overall_score:.1f}%")
                print(f"📈 Score Breakdown:")
                print(f"   • Astro: {score_components.get('astro', 0):.1f}")
                print(f"   • MMFSN: {score_components.get('mmfsn', 0):.1f}")
                print(f"   • Stats: {score_components.get('stats', 0):.1f}")
                print(f"   • Numerology: {score_components.get('numerology', 0):.1f}")
                print(f"   • Planetary Hours: {score_components.get('planetary_hours', 0):.1f}")
                
                print(f"\n🎯 TONIGHT'S PREDICTIONS:")
                
                if "picks" in data:
                    if "MegaMillions" in data["picks"]:
                        mm_picks = data["picks"]["MegaMillions"]["lane_system"]
                        print(f"   🔥 MegaMillions: {mm_picks[0]}")
                        if len(mm_picks) > 1:
                            print(f"      Secondary: {mm_picks[1]}")
                    
                    if "Cash3" in data["picks"]:
                        cash3_picks = data["picks"]["Cash3"]["lane_system"]
                        strength_emoji = "💰" if cash3_strength >= 65 else "💵" if cash3_strength >= 55 else "📊"
                        print(f"   {strength_emoji} Cash3: {cash3_picks[0]} (Adj: {cash3_strength:.1f}%)")
                        if len(cash3_picks) > 1:
                            print(f"      Secondary: {cash3_picks[1]}")
                    
                    if "Cash4" in data["picks"]:
                        cash4_picks = data["picks"]["Cash4"]["lane_system"]
                        strength_emoji = "💰" if cash4_strength >= 65 else "💵" if cash4_strength >= 55 else "📊"
                        print(f"   {strength_emoji} Cash4: {cash4_picks[0]} (Adj: {cash4_strength:.1f}%)")
                        if len(cash4_picks) > 1:
                            print(f"      Secondary: {cash4_picks[1]}")
                    
                    if "Cash4Life" in data["picks"]:
                        c4l_picks = data["picks"]["Cash4Life"]["lane_system"]
                        print(f"   🌟 Cash4Life: {c4l_picks[0]}")
                    
                    if "Powerball" in data["picks"]:
                        pb_picks = data["picks"]["Powerball"]["lane_system"]
                        print(f"   ⚡ Powerball: {pb_picks[0]}")
                        
            except Exception as e:
                print(f"❌ Error reading {code} predictions: {e}")
        else:
            print(f"⚠️ No predictions file found")
    
    # Overall Rankings
    print(f"\n{'='*60}")
    print("🏆 COMPLETE SUBSCRIBER RANKINGS")
    print(f"{'='*60}")
    
    # Sort by overall confidence
    rankings.sort(key=lambda x: x["confidence"], reverse=True)
    
    print(f"\n📈 OVERALL CONFIDENCE RANKING:")
    for i, sub in enumerate(rankings, 1):
        conf = sub["confidence"]
        
        if conf >= 60.0:
            level = "🔥 STRONG"
        elif conf >= 55.0:
            level = "⚡ MODERATE"
        else:
            level = "📊 WEAK"
        
        print(f"{i:2d}. {sub['code']} - {sub['name']} - {level}")
        print(f"    Confidence: {conf:.1f}% | Astro: {sub['components'].get('astro', 0):.1f} | MMFSN: {sub['components'].get('mmfsn', 0):.1f}")
    
    # Game-specific rankings
    print(f"\n🎯 CASH3 OPPORTUNITIES RANKING:")
    cash3_rankings = [s for s in rankings if s['cash3_adj'] > 0]
    cash3_rankings.sort(key=lambda x: x["cash3_adj"], reverse=True)
    
    for i, sub in enumerate(cash3_rankings[:8], 1):
        adj_strength = sub['cash3_adj']
        cash3_picks = sub['predictions'].get('Cash3', {}).get('lane_system', ['N/A'])
        
        if adj_strength >= 65.0:
            level = "🔥 STRONG"
        elif adj_strength >= 55.0:
            level = "⚡ MODERATE" 
        else:
            level = "📊 WEAK"
            
        print(f"{i}. {sub['code']} - {level} - {adj_strength:.1f}% - Pick: {cash3_picks[0]}")
    
    print(f"\n🎯 CASH4 OPPORTUNITIES RANKING:")
    cash4_rankings = [s for s in rankings if s['cash4_adj'] > 0]
    cash4_rankings.sort(key=lambda x: x["cash4_adj"], reverse=True)
    
    for i, sub in enumerate(cash4_rankings[:8], 1):
        adj_strength = sub['cash4_adj']
        cash4_picks = sub['predictions'].get('Cash4', {}).get('lane_system', ['N/A'])
        
        if adj_strength >= 65.0:
            level = "🔥 STRONG"
        elif adj_strength >= 55.0:
            level = "⚡ MODERATE"
        else:
            level = "📊 WEAK"
            
        print(f"{i}. {sub['code']} - {level} - {adj_strength:.1f}% - Pick: {cash4_picks[0]}")
    
    print(f"\n🔥 MEGAMILLIONS RANKING:")
    mm_rankings = [s for s in rankings if s['mm_strength'] > 0]
    mm_rankings.sort(key=lambda x: x["mm_strength"], reverse=True)
    
    for i, sub in enumerate(mm_rankings[:8], 1):
        mm_strength = sub['mm_strength']
        mm_picks = sub['predictions'].get('MegaMillions', {}).get('lane_system', ['N/A'])
        
        if mm_strength >= 60.0:
            level = "🔥 STRONG"
        elif mm_strength >= 55.0:
            level = "⚡ MODERATE"
        else:
            level = "📊 WEAK"
            
        print(f"{i}. {sub['code']} - {level} - {mm_strength:.1f}% - Pick: {mm_picks[0]}")
    
    # Final Recommendations
    print(f"\n{'='*60}")
    print("🎯 TONIGHT'S TOP RECOMMENDATIONS")
    print(f"{'='*60}")
    
    if cash3_rankings:
        best_cash3 = cash3_rankings[0]
        best_cash3_pick = best_cash3['predictions']['Cash3']['lane_system'][0]
        print(f"🥇 BEST CASH3: {best_cash3['name']} ({best_cash3['code']})")
        print(f"   Pick: {best_cash3_pick} | Strength: {best_cash3['cash3_adj']:.1f}%")
        
        if best_cash3['cash3_adj'] >= 65.0:
            print(f"   ✅ STRONG PLAY RECOMMENDED")
        elif best_cash3['cash3_adj'] >= 55.0:
            print(f"   ⚡ MODERATE PLAY - Consider this")
        else:
            print(f"   ⚠️ WEAK OPPORTUNITY")
    
    if cash4_rankings:
        best_cash4 = cash4_rankings[0]
        best_cash4_pick = best_cash4['predictions']['Cash4']['lane_system'][0]
        print(f"\n🥈 BEST CASH4: {best_cash4['name']} ({best_cash4['code']})")
        print(f"   Pick: {best_cash4_pick} | Strength: {best_cash4['cash4_adj']:.1f}%")
    
    if mm_rankings:
        best_mm = mm_rankings[0]
        best_mm_pick = best_mm['predictions']['MegaMillions']['lane_system'][0]
        print(f"\n🎲 BEST MEGAMILLIONS: {best_mm['name']} ({best_mm['code']})")
        print(f"   Pick: {best_mm_pick} | Confidence: {best_mm['mm_strength']:.1f}%")
        
        if best_mm['mm_strength'] >= 60.0:
            print(f"   ✅ GOOD OPPORTUNITY")
        else:
            print(f"   ⚠️ BELOW OPTIMAL THRESHOLD")
    
    return rankings

if __name__ == "__main__":
    rankings = analyze_all_vip_subscribers()